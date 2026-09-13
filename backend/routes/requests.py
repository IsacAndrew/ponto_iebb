from fastapi import APIRouter, Body, Request
from sqlalchemy import select

from ..db import Item, Person, audit, now, reading, today, transaction
from ..rules import effective_role, fail, minutes, summarize, valid_date
from ..security import FULL_ACCESS, current, public, require
from .attendance import apply_correction

router = APIRouter()


@router.get("/api/requests")
def requests(request: Request):
    with reading() as db:
        actor = current(db, request)
        return [
            item_json(db, r)
            for r in db.scalars(
                select(Item).where(Item.kind == "request").order_by(Item.id.desc())
            )
            if effective_role(actor) in FULL_ACCESS or r.person_id == actor.id
        ]


def item_json(db, r):
    p = db.get(Person, r.person_id)
    return dict(
        id=r.id,
        kind=r.kind,
        person_id=r.person_id,
        name=p.name if p else "",
        date=r.date,
        status=r.status,
        data=r.data,
    )


@router.put("/api/profile")
def update_profile(request: Request, data: dict = Body(...)):
    with transaction() as db:
        actor = current(db, request)
        require(actor, FULL_ACCESS)
        before = public(actor)
        name = str(data.get("name", actor.name)).strip()
        if not name or len(name) > 160:
            fail("Informe um nome válido.")
        details = {**actor.details}
        for key in ("email", "phone", "birth"):
            if key in data:
                value = str(data[key]).strip()[:250]
                details[key] = (
                    "".join(c for c in value if c.isdigit())
                    if key == "phone"
                    else value
                )
        actor.name = name
        actor.details = details
        audit(
            db,
            actor,
            "Editar próprio cadastro",
            actor.id,
            before,
            public(actor),
            "Atualização pelo titular",
        )
        return public(actor, True)


@router.post("/api/requests")
def new_request(request: Request, data: dict = Body(...)):
    with transaction() as db:
        p = current(db, request)
        kind = data.get("type")
        if kind not in ("point", "profile") or not str(data.get("reason", "")).strip():
            fail("Informe a alteração e o motivo.")
        if kind == "point":
            d = valid_date(data.get("date"))
            for t in data.get("times", []):
                minutes(t)
            before = {"punches": summarize(db, p, d)["punches"]}
        else:
            d = today()
            if (
                data.get("field") not in ("name", "email", "phone", "birth")
                or not str(data.get("value", "")).strip()
            ):
                fail("Informe o campo e o novo valor.")
            before = {
                "value": p.name
                if data["field"] == "name"
                else p.details.get(data["field"], "")
            }
        r = Item(
            kind="request", person_id=p.id, date=d, data={**data, "before": before}
        )
        db.add(r)
        db.flush()
        audit(
            db,
            p,
            "Solicitar alteração",
            f"{p.id}:{d}",
            after={"request": r.id},
            reason=data["reason"],
        )
        return {"ok": True}


@router.post("/api/requests/{rid}/decide")
def decide(rid: int, request: Request, data: dict = Body(...)):
    with transaction() as db:
        actor = current(db, request)
        require(actor, FULL_ACCESS)
        r = db.get(Item, rid)
        if not r or r.kind != "request" or r.status != "Pendente":
            fail("Solicitação não está pendente.")
        p = db.get(Person, r.person_id)
        approved = data.get("approve") is True
        reason = str(data.get("reason", "")).strip()
        if not reason:
            fail("Informe o motivo da decisão.")
        if approved:
            if r.data["type"] == "point":
                actual = summarize(db, p, r.date)["punches"]
                if [x["time"] for x in actual] != [
                    x["time"] for x in r.data["before"]["punches"]
                ]:
                    fail("O ponto mudou desde a solicitação. Revise os horários.")
                apply_correction(db, actor, p, r.date, r.data.get("times", []), reason)
            else:
                field = r.data["field"]
                value = r.data["value"]
                actual = p.name if field == "name" else p.details.get(field, "")
                if actual != r.data["before"]["value"]:
                    fail("O cadastro mudou desde a solicitação. Revise os dados.")
                if field == "name":
                    p.name = value[:160]
                else:
                    p.details = {**p.details, field: value[:250]}
                audit(
                    db,
                    actor,
                    "Aprovar alteração cadastral",
                    p.id,
                    {"value": actual},
                    {"value": value},
                    reason,
                )
        r.status = "Aprovada" if approved else "Reprovada"
        r.data = {
            **r.data,
            "decision_by": actor.name,
            "decision_at": now().isoformat(),
            "decision_reason": reason,
        }
        audit(
            db,
            actor,
            "Decidir solicitação",
            f"{r.person_id}:{r.date}",
            after={"status": r.status, "request": rid},
            reason=reason,
        )
        return {"ok": True}
