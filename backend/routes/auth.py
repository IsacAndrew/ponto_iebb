import logging
import os
import secrets
import smtplib
import ssl
import string
import time
from email.message import EmailMessage

from fastapi import APIRouter, Body, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select

from ..db import Person, Setting, audit, now, reading, today, transaction
from ..rules import effective_role, fail, roles_for, summarize
from ..schemas import LoginInput
from ..security import confirm, cookie, current, digest, password_hash, public, verify
from .attendance import location_required

router = APIRouter()
RECOVERY_RESPONSE = {
    "message": "Se o login estiver cadastrado e possuir e-mail, uma credencial temporária será enviada."
}


def send_recovery(email, credential):
    host = os.getenv("SMTP_HOST", "").strip()
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM", "").strip()
    if not host or not sender:
        raise RuntimeError("SMTP não configurado")
    port = int(os.getenv("SMTP_PORT", "587"))
    message = EmailMessage()
    message["From"] = sender
    message["To"] = email
    message["Subject"] = "Credencial temporária"
    message.set_content(f"{credential}\n\nVálida por 5 minutos.")
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        if os.getenv("SMTP_USE_TLS", "true").lower() == "true":
            smtp.starttls(context=ssl.create_default_context())
        if user:
            smtp.login(user, password)
        smtp.send_message(message)


@router.post("/api/recover")
def recover(data: dict = Body(...)):
    login_name = str(data.get("login", "")).strip().lower()
    if not login_name:
        fail("Preencha o login primeiro.")
    person_id = email = None
    rate_key = "recover-rate:" + digest(login_name)
    with transaction() as db:
        rate = db.get(Setting, rate_key)
        if rate and rate.data.get("until", 0) > time.time():
            return RECOVERY_RESPONSE
        if rate:
            rate.data = {"until": time.time() + 60}
        else:
            db.add(Setting(key=rate_key, data={"until": time.time() + 60}))
        person = db.scalar(
            select(Person).where(Person.login == login_name, Person.active == True)
        )
        if person:
            person_id = person.id
            email = str(person.details.get("email", "")).strip()
    if not person_id or not email:
        return RECOVERY_RESPONSE
    credential = "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(8)
    )
    try:
        send_recovery(email, credential)
    except Exception as exc:
        logging.getLogger("ponto").error(
            "Falha SMTP na recuperação: %s", type(exc).__name__
        )
        with transaction() as db:
            rate = db.get(Setting, rate_key)
            if rate:
                db.delete(rate)
        fail(
            "Não foi possível concluir a recuperação agora. Tente novamente mais tarde.",
            503,
        )
    with transaction() as db:
        row = db.get(Setting, f"recovery:{person_id}")
        value = {
            "hash": digest(credential),
            "expires": time.time() + 300,
            "used": False,
        }
        if row:
            row.data = value
        else:
            db.add(Setting(key=f"recovery:{person_id}", data=value))
    return RECOVERY_RESPONSE


@router.post("/api/login")
def login(request: Request, response: Response, data: LoginInput):
    data = data.model_dump(mode="json", exclude_none=True)
    result = None
    with transaction() as db:
        name = str(data.get("login", "")).strip().lower()
        rate = db.get(Setting, "attempt:" + digest(name))
        if not rate:
            rate = Setting(key="attempt:" + digest(name), data={})
            db.add(rate)
        attempts = dict(rate.data)
        if attempts.get("until", 0) > time.time():
            return JSONResponse(
                {"detail": "Muitas tentativas. Aguarde um minuto."}, status_code=429
            )
        person = db.scalar(
            select(Person).where(Person.login == name, Person.active == True)
        )
        supplied = str(data.get("password", ""))
        recovery = db.get(Setting, f"recovery:{person.id}") if person else None
        recovery_ok = bool(
            recovery
            and recovery.data.get("expires", 0) >= time.time()
            and not recovery.data.get("used")
            and secrets.compare_digest(recovery.data.get("hash", ""), digest(supplied))
        )
        password_ok = bool(person and verify(supplied, person.password))
        if not person or not (password_ok or recovery_ok):
            n = attempts.get("count", 0) + 1
            rate.data = {
                "count": n if n < 5 else 0,
                "until": time.time() + 60 if n >= 5 else 0,
            }
            result = JSONResponse(
                {"detail": "Login ou senha incorretos."}, status_code=401
            )
        else:
            rate.data = {}
            if recovery_ok:
                recovery.data = {**recovery.data, "used": True}
                person.temporary = True
            state = person.session or {}
            previous = request.cookies.get("ponto_session", "")
            same = (
                previous
                and digest(previous) == state.get("token")
                and state.get("expires", 0) > time.time()
            )
            token = previous if same else f"{person.id}:" + secrets.token_urlsafe(32)
            assigned = roles_for(person)
            person.session = {
                "token": digest(token),
                "expires": time.time() + 43200,
                **({"active_role": assigned[0]} if len(assigned) == 1 else {}),
            }
            cookie(response, token)
            punch = (
                None
                if len(assigned) > 1 or effective_role(person) == "Diretoria"
                else {
                    **summarize(db, person, today()),
                    "now": now().isoformat(),
                    "location_required": location_required(db, person),
                    "geo_ready": bool(
                        db.get(Setting, "geo")
                        and db.get(Setting, "geo").data.get("verified")
                    ),
                }
            )
            result = {"user": public(person, True), "punch": punch}
    return result


@router.get("/api/me")
def me(request: Request):
    with reading() as db:
        person = current(db, request, True, True)
        selected = not public(person, True)["access_required"]
        punch = (
            None
            if not selected or effective_role(person) == "Diretoria"
            else {
                **summarize(db, person, today()),
                "now": now().isoformat(),
                "location_required": location_required(db, person),
                "geo_ready": bool(
                    db.get(Setting, "geo")
                    and db.get(Setting, "geo").data.get("verified")
                ),
            }
        )
        return {
            "user": public(person, True),
            "now": now().isoformat(),
            "location_required": location_required(db, person),
            "punch": punch,
        }


@router.post("/api/access")
def choose_access(request: Request, data: dict = Body(...)):
    with transaction() as db:
        person = current(db, request, True, True)
        role = data.get("role")
        if role not in roles_for(person):
            fail("Perfil de acesso inválido.", 403)
        person.session = {**person.session, "active_role": role}
        punch = (
            None
            if role == "Diretoria"
            else {
                **summarize(db, person, today()),
                "now": now().isoformat(),
                "location_required": location_required(db, person),
                "geo_ready": bool(
                    db.get(Setting, "geo")
                    and db.get(Setting, "geo").data.get("verified")
                ),
            }
        )
        return {"user": public(person, True), "punch": punch}


@router.post("/api/logout")
def logout(request: Request, response: Response):
    with transaction() as db:
        person = current(db, request, True, True)
        person.session = {}
    response.delete_cookie("ponto_session")
    return {"ok": True}


@router.post("/api/password")
def password(request: Request, data: dict = Body(...)):
    with transaction() as db:
        person = current(db, request, True, True)
        if not person.temporary:
            confirm(person, data.get("current", ""))
        value = str(data.get("password", ""))
        if (
            len(value) < 8
            or len(value) > 128
            or value == "102030"
            or (person.temporary and verify(value, person.password))
        ):
            fail("Use uma senha definitiva com 8 a 128 caracteres.")
        person.password = password_hash(value)
        person.temporary = False
        person.session = {**person.session}
        audit(db, person, "Senha alterada", person.id)
        return public(person, True)


@router.post("/api/profile/login")
def reveal(request: Request, data: dict = Body(...)):
    with transaction() as db:
        person = current(db, request)
        confirm(person, data.get("password", ""))
        return {"login": person.login}


@router.put("/api/profile/theme")
def theme(request: Request, data: dict = Body(...)):
    with transaction() as db:
        person = current(db, request, True, True)
        value = data.get("theme")
        if value not in ("light", "dark"):
            fail("Escolha o tema claro ou escuro.")
        person.details = {**(person.details or {}), "theme": value}
        return public(person, True)
