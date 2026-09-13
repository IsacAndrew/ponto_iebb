import hashlib
import hmac
import os
import secrets
import time

from fastapi import Request

from .db import Person
from .rules import effective_role, fail, roles_for


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(value):
    salt = secrets.token_hex(16)
    return (
        salt
        + ":"
        + hashlib.pbkdf2_hmac("sha256", value.encode(), salt.encode(), 310000).hex()
    )


def verify(value, stored):
    if not isinstance(value, str) or not isinstance(stored, str):
        return False
    try:
        salt, hashed = stored.split(":", 1)
    except ValueError:
        return False
    return hmac.compare_digest(
        hashlib.pbkdf2_hmac("sha256", value.encode(), salt.encode(), 310000).hex(),
        hashed,
    )


def cookie(response, token):
    response.set_cookie(
        "ponto_session",
        token,
        httponly=True,
        samesite="strict",
        secure=bool(os.getenv("RENDER")),
        max_age=43200,
        path="/",
    )


FULL_ACCESS = ("Suporte", "Diretoria")


def current(db, request: Request, allow_temporary=False, allow_unselected=False):
    token = request.cookies.get("ponto_session", "")
    if not token or ":" not in token:
        fail("Entre novamente.", 401)
    try:
        person = db.get(Person, int(token.split(":")[0]))
    except ValueError:
        fail("Entre novamente.", 401)
    if not person or not person.active:
        fail("Entre novamente.", 401)
    state = person.session or {}
    if (
        not hmac.compare_digest(state.get("token", ""), digest(token))
        or state.get("expires", 0) < time.time()
    ):
        fail("Entre novamente.", 401)
    if (
        len(roles_for(person)) > 1
        and state.get("active_role") not in roles_for(person)
        and not allow_unselected
    ):
        fail("Escolha o perfil de acesso.", 409)
    return person


def require(person, roles):
    if effective_role(person) not in roles:
        fail("Você não tem acesso a esta ação.", 403)


def confirm(person, password):
    if not verify(password, person.password):
        fail("Senha incorreta.", 403)


def public(person, active=False):
    assigned = roles_for(person)
    role = effective_role(person) if active else person.role
    return dict(
        id=person.id,
        name=person.name,
        login=person.login,
        role=role,
        roles=assigned,
        access_required=active
        and len(assigned) > 1
        and (person.session or {}).get("active_role") not in assigned,
        active=person.active,
        hired=person.hired,
        terminated=person.terminated,
        details=person.details,
        temporary=person.temporary,
    )
