import json
import math
import secrets
from datetime import date, timedelta

from fastapi import APIRouter, Body, Request
from sqlalchemy import select

from ..db import Item, Person, Setting, audit, now, reading, today, transaction
from ..rules import (
    ADMIN,
    distance,
    effective_role,
    fail,
    get_day,
    holiday,
    minutes,
    roles_for,
    schedule_for,
    summarize,
    suspect_missing,
    valid_date,
)
from ..schemas import CorrectionInput, PunchInput
from ..security import current, digest, require

router = APIRouter()


def location_required(db, person):
    row = (
        db.get(Setting, f"geo-required:{person.id}")
        if effective_role(person) == "Suporte"
        else None
    )
    return row is None or row.data.get("required") is not False


def occurrence(db, person, day, title, details=None):
    row = get_day(db, person, day)
    fingerprint = digest(
        json.dumps(row.punches if row else [], sort_keys=True, ensure_ascii=False)
    )
    for existing in db.scalars(
        select(Item).where(
            Item.kind == "occurrence", Item.person_id == person.id, Item.date == day
        )
    ):
        if existing.data.get("title") != title:
            continue
        if (
            existing.status == "Pendente"
            or existing.data.get("fingerprint") == fingerprint
        ):
            return
    db.add(
        Item(
            kind="occurrence",
            person_id=person.id,
            date=day,
            data={"title": title, "fingerprint": fingerprint, **(details or {})},
        )
    )


@router.get("/api/punch/today")
def punch_today(request: Request):
    with reading() as db:
        p = current(db, request)
        return {
            **summarize(db, p, today()),
            "now": now().isoformat(),
            "location_required": location_required(db, p),
            "geo_ready": bool(
                db.get(Setting, "geo") and db.get(Setting, "geo").data.get("verified")
            ),
        }


def location_accuracy(geo):
    return geo.get("accuracy", 500) if geo.get("accuracy_version") == 2 else 500


def process_punch(db, p, data, source="site"):
    if effective_role(p) == "Diretoria":
        fail("Este perfil não tem jornada obrigatória.")
    d = today()
    if d < p.hired or (p.terminated and d > p.terminated):
        fail("Data fora do vínculo da pessoa.")
    row = get_day(db, p, d, True)
    if not row.punches:
        row.periods = schedule_for(db, p, d)
    punches = list(row.punches)
    key = str(data.get("key", ""))
    if not key or len(key) > 100:
        fail("Atualize a página e tente novamente.")
    if any(x.get("key") == key for x in punches):
        return {"message": "Ponto registrado com sucesso", "day": summarize(db, p, d)}
    stamp = now()
    minute = stamp.hour * 60 + stamp.minute
    if punches and stamp.timestamp() - punches[-1]["epoch"] < 30:
        fail("Ponto já registrado. Aguarde antes de outra marcação.", 409)
    expected = [x for pair in row.periods for x in pair]
    index = len(punches)
    extra = index >= len(expected) or bool(holiday(db, d))
    if extra and not data.get("overtime"):
        return {"question": "overtime", "message": "Você está fazendo hora extra?"}
    if not extra and index % 2 == 0 and minute < minutes(expected[index]) - 5:
        fail("Ponto liberado cinco minutos antes da entrada prevista.")
    unusual = not extra and suspect_missing(expected, index, minute)
    if unusual and data.get("forgot") not in ("yes", "no"):
        return {"question": "forgot", "message": "Você esqueceu a marcação anterior?"}
    required = location_required(db, p)
    geo_row = db.get(Setting, "geo")
    geo = geo_row.data if geo_row else {}
    location = {}
    if required:
        if geo.get("verified") is not True:
            fail(
                "A escola ainda precisa confirmar o local de registro. Procure a Diretoria ou o Suporte.",
                409,
            )
        try:
            lat, lon, accuracy = [float(data[k]) for k in ("lat", "lon", "accuracy")]
        except (KeyError, ValueError, TypeError):
            fail("Permita a localização para registrar o ponto.", 422)
        if (
            not all(math.isfinite(x) for x in (lat, lon, accuracy))
            or abs(lat) > 90
            or abs(lon) > 180
            or accuracy < 0
        ):
            fail("Localização inválida.", 422)
        if accuracy > location_accuracy(geo):
            fail(
                f"Este aparelho informou precisão de {round(accuracy)} m; o limite é {location_accuracy(geo)} m. Não foi possível confirmar sua presença na escola. Ative a localização precisa do sistema ou use um aparelho com melhor localização.",
                422,
            )
        meters = distance(lat, lon, geo["lat"], geo["lon"])
        if meters > 100:
            fail(
                f"Você está a {round(meters)} m da escola. Aproxime-se para registrar.",
                422,
            )
        location = {
            "lat": lat,
            "lon": lon,
            "accuracy": accuracy,
            "distance": round(meters, 1),
        }
    punches.append(
        {
            "time": stamp.strftime("%H:%M"),
            "at": stamp.isoformat(),
            "epoch": stamp.timestamp(),
            "key": key,
            "test": False,
            "access_role": effective_role(p),
            **location,
        }
    )
    row.punches = punches
    if unusual:
        occurrence(
            db,
            p,
            d,
            "Batida possivelmente esquecida"
            if data.get("forgot") == "yes"
            else "Marcação fora do esperado",
            {"answer": data.get("forgot")},
        )
    if extra:
        occurrence(db, p, d, "Batida adicional")
    if row.absent:
        occurrence(db, p, d, "Falta registrada com comparecimento")
    summary = summarize(db, p, d)
    if extra or summary["extra"] > 0:
        row.overtime = "Pendente de validação"
        occurrence(db, p, d, "Hora extra pendente")
    audit(
        db,
        p,
        "Registrar ponto",
        row.key,
        after={
            "time": punches[-1]["time"],
            "location_required": required,
            "source": source,
        },
    )
    message = "Ponto registrado com sucesso"
    if row.absent:
        message += ". Havia falta registrada. Procure o Suporte."
    elif not extra and index % 2 == 0 and minute - minutes(expected[index]) > 65:
        message += ". Atraso elevado: procure o Suporte."
    return {"message": message, "day": summarize(db, p, d)}


@router.post("/api/punch")
def punch(request: Request, data: PunchInput):
    data = data.model_dump(mode="json", exclude_none=True)
    with transaction() as db:
        return process_punch(db, current(db, request), data)


def qr_person(db, request, token):
    if not token or len(token) > 200:
        fail("QR Code inválido.", 404)
    row = db.get(Setting, "qr-global")
    if not row or not secrets.compare_digest(digest(token), row.data.get("hash", "")):
        fail("QR Code inválido ou substituído.", 404)
    return current(db, request)


def button_labels(periods):
    total = len([v for pair in periods for v in pair])
    defaults = ["Entrada", "Saída para intervalo", "Retorno do intervalo", "Saída"]
    if total == 2:
        defaults = ["Entrada", "Saída"]
    return [
        (defaults[i] if i < len(defaults) else ("Entrada" if i % 2 == 0 else "Saída"))
        for i in range(total)
    ]


@router.get("/api/qr/{token}")
def qr_state(token: str, request: Request):
    with reading() as db:
        p = qr_person(db, request, token)
        summary = summarize(db, p, today())
        labels = button_labels(summary["periods"])
        index = len(summary["punches"])
        return {
            "name": p.name.split()[0],
            "now": now().isoformat(),
            "day": summary,
            "labels": labels,
            "can_register": bool(labels),
            "location_required": location_required(db, p),
            "next": labels[index]
            if index < len(labels)
            else ("Registrar hora extra" if labels else "Sem jornada hoje"),
        }


@router.post("/api/qr/{token}/punch")
def qr_punch(token: str, request: Request, data: PunchInput):
    data = data.model_dump(mode="json", exclude_none=True)
    with transaction() as db:
        p = qr_person(db, request, token)
        result = process_punch(db, p, data, "qr")
        if "day" in result:
            index = len(result["day"]["punches"]) - 1
            labels = button_labels(result["day"]["periods"])
            label = labels[index] if index < len(labels) else "Hora extra"
            message = f"{p.name.split()[0]}, {label.lower()} registrada com sucesso"
            result.update(
                label=label,
                confirmation=message,
                registered_at=now().strftime("%H:%M:%S"),
            )
        return result


@router.get("/api/records")
def records(request: Request, start: str, end: str, person_id: int | None = None):
    start = valid_date(start)
    end = valid_date(end)
    if end < start or (date.fromisoformat(end) - date.fromisoformat(start)).days > 93:
        fail("Selecione até 93 dias.")
    with reading() as db:
        actor = current(db, request)
        if effective_role(actor) not in ADMIN:
            person_id = actor.id
        people = (
            list(db.scalars(select(Person).where(Person.id == person_id)))
            if person_id
            else list(db.scalars(select(Person).order_by(Person.name)))
        )
        result = []
        day = date.fromisoformat(start)
        while day.isoformat() <= end:
            d = day.isoformat()
            for p in people:
                if p.hired <= d and (not p.terminated or d <= p.terminated):
                    result.append(summarize(db, p, d))
            day += timedelta(days=1)
        return result


@router.get("/api/attendance")
def attendance(request: Request, day: str):
    valid_date(day)
    with reading() as db:
        require(current(db, request), ADMIN)
        rows = [
            summarize(db, p, day)
            for p in db.scalars(select(Person).order_by(Person.name))
            if roles_for(p) != ["Diretoria"]
            and p.hired <= day
            and (not p.terminated or day <= p.terminated)
        ]
        return sorted(
            rows,
            key=lambda r: (not bool(r["expected"] and not r["holiday"]), r["name"]),
        )


@router.post("/api/absence")
def absence(request: Request, data: dict = Body(...)):
    with transaction() as db:
        actor = current(db, request)
        require(actor, ADMIN)
        d = valid_date(data.get("date"))
        p = db.get(Person, data.get("person_id"))
        if not p:
            fail("Pessoa não encontrada.", 404)
        row = get_day(db, p, d, True)
        before = {"absent": row.absent}
        if data.get("absent") and (
            holiday(db, d) or not row.periods or roles_for(p) == ["Diretoria"]
        ):
            fail("Não há expediente previsto nesta data.")
        row.absent = bool(data.get("absent"))
        audit(
            db,
            actor,
            "Registrar falta" if row.absent else "Desmarcar falta",
            row.key,
            before,
            {"absent": row.absent},
        )
        if row.absent and row.punches:
            occurrence(db, p, d, "Falta registrada com comparecimento")
        return {"ok": True}


def apply_correction(db, actor, p, d, times, reason):
    if not reason.strip():
        fail("Informe o motivo.")
    if d > today():
        fail("Não é possível corrigir uma data futura.")
    if d < p.hired or p.terminated and d > p.terminated:
        fail("Data fora do vínculo da pessoa.")
    values = [minutes(t) for t in times]
    if values != sorted(set(values)):
        fail("As marcações devem estar em ordem e sem horários repetidos.")
    row = get_day(db, p, d, True)
    before = {"punches": row.punches}
    original_role = next(
        (x.get("access_role") for x in row.punches if x.get("access_role")), None
    )
    row.punches = [
        {
            **({"access_role": original_role} if original_role else {}),
            "time": t,
            "at": d + "T" + t + ":00-03:00",
            "epoch": __import__("datetime")
            .datetime.fromisoformat(d + "T" + t + ":00-03:00")
            .timestamp(),
            "key": secrets.token_hex(12),
            "corrected": True,
            "test": False,
        }
        for t in times
    ]
    audit(
        db, actor, "Corrigir ponto", row.key, before, {"punches": row.punches}, reason
    )
    if summarize(db, p, d)["extra"] > 0:
        row.overtime = "Pendente de validação"
        occurrence(db, p, d, "Hora extra pendente")
    else:
        row.overtime = ""


@router.post("/api/corrections")
def corrections(request: Request, data: CorrectionInput):
    data = data.model_dump(mode="json", exclude_none=True)
    with transaction() as db:
        actor = current(db, request)
        require(actor, ADMIN)
        p = db.get(Person, data.get("person_id"))
        if not p:
            fail("Pessoa não encontrada.", 404)
        apply_correction(
            db,
            actor,
            p,
            valid_date(data.get("date")),
            data.get("times", []),
            str(data.get("reason", "")),
        )
        return {"ok": True}
