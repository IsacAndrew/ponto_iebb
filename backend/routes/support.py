import json

from fastapi import APIRouter, Body, Request
from sqlalchemy import select

from ..db import Day, Item, Person, audit, now, reading, today, transaction
from ..rules import effective_role, fail, get_day
from ..security import current, digest, require
from .attendance import occurrence
from .requests import item_json

router = APIRouter()


@router.get("/api/support/occurrences")
def occurrences(request: Request):
    with transaction() as db:
        require(current(db, request), ["Suporte"])
        for row in db.scalars(select(Day).where(Day.date < today())):
            if (
                len(row.punches) < len(row.periods) * 2
                and row.punches
                or len(row.punches) % 2
            ):
                occurrence(
                    db, db.get(Person, row.person_id), row.date, "Ponto incompleto"
                )
        db.flush()
        return [
            item_json(db, r)
            for r in db.scalars(
                select(Item).where(Item.kind == "occurrence").order_by(Item.id.desc())
            )
        ]


@router.post("/api/support/occurrences/{rid}")
def resolve(rid: int, request: Request, data: dict = Body(...)):
    with transaction() as db:
        actor = current(db, request)
        require(actor, ["Suporte"])
        r = db.get(Item, rid)
        if not r or r.kind != "occurrence" or r.status != "Pendente":
            fail("Ocorrência não está pendente.")
        reason = str(data.get("reason", "")).strip()
        if not reason:
            fail("Informe o resultado da análise.")
        if r.data.get("title") == "Hora extra pendente":
            row = get_day(db, db.get(Person, r.person_id), r.date)
            row.overtime = "Validada" if data.get("approve") else "Não validada"
        day = get_day(db, db.get(Person, r.person_id), r.date)
        fingerprint = digest(
            json.dumps(day.punches if day else [], sort_keys=True, ensure_ascii=False)
        )
        r.status = "Concluída"
        r.data = {
            **r.data,
            "resolution": reason,
            "by": actor.name,
            "fingerprint": fingerprint,
        }
        audit(
            db,
            actor,
            "Analisar ocorrência",
            f"{r.person_id}:{r.date}",
            after=r.data,
            reason=reason,
        )
        return {"ok": True}


@router.get("/api/tickets")
def tickets(request: Request, management: bool = False):
    with reading() as db:
        actor = current(db, request)
        if management:
            require(actor, ["Suporte"])
        return [
            item_json(db, r)
            for r in db.scalars(
                select(Item).where(Item.kind == "ticket").order_by(Item.id.desc())
            )
            if (management and effective_role(actor) == "Suporte")
            or r.person_id == actor.id
        ]


@router.get("/api/tickets/unread")
def unread_tickets(request: Request):
    with reading() as db:
        require(current(db, request), ["Suporte"])
        count = 0
        names = []
        for row in db.scalars(
            select(Item).where(Item.kind == "ticket").order_by(Item.id.desc())
        ):
            unread = [
                message
                for message in row.data.get("messages", [])
                if not message.get("support") and not message.get("support_read", False)
            ]
            if unread:
                count += len(unread)
                name = db.get(Person, row.person_id).name
                if name not in names:
                    names.append(name)
        return {"count": count, "names": names}


@router.post("/api/tickets/read")
def read_tickets(request: Request):
    with transaction() as db:
        require(current(db, request), ["Suporte"])
        count = 0
        for row in db.scalars(select(Item).where(Item.kind == "ticket")):
            messages = []
            changed = False
            for message in row.data.get("messages", []):
                if not message.get("support") and not message.get(
                    "support_read", False
                ):
                    message = {**message, "support_read": True}
                    changed = True
                    count += 1
                messages.append(message)
            if changed:
                row.data = {**row.data, "messages": messages}
        return {"read": count}


@router.post("/api/tickets")
def new_ticket(request: Request, data: dict = Body(...)):
    with transaction() as db:
        actor = current(db, request)
        if effective_role(actor) == "Suporte":
            fail("Selecione um chamado para responder.", 403)
        message = str(data.get("message", "")).strip()
        if not message or len(message) > 4000:
            fail("Escreva uma mensagem com até 4000 caracteres.")
        row = db.scalar(
            select(Item).where(Item.kind == "ticket", Item.person_id == actor.id)
        )
        if not row:
            row = Item(kind="ticket", person_id=actor.id, data={"messages": []})
            db.add(row)
        row.data = {
            "messages": row.data["messages"]
            + [
                {
                    "name": actor.name,
                    "support": False,
                    "support_read": False,
                    "text": message,
                    "at": now().isoformat(),
                }
            ]
        }
        return {"ok": True}


@router.post("/api/tickets/{rid}/message")
def message(rid: int, request: Request, data: dict = Body(...)):
    with transaction() as db:
        actor = current(db, request)
        row = db.get(Item, rid)
        if (
            not row
            or row.kind != "ticket"
            or effective_role(actor) != "Suporte"
            and row.person_id != actor.id
        ):
            fail("Chamado não encontrado.", 404)
        value = str(data.get("message", "")).strip()
        if not value or len(value) > 4000:
            fail("Escreva uma mensagem com até 4000 caracteres.")
        support = effective_role(actor) == "Suporte" and row.person_id != actor.id
        row.data = {
            "messages": row.data["messages"]
            + [
                {
                    "name": actor.name,
                    "support": support,
                    "support_read": support,
                    "text": value,
                    "at": now().isoformat(),
                }
            ]
        }
        return {"ok": True}


@router.delete("/api/tickets/{rid}")
def close_ticket(rid: int, request: Request):
    with transaction() as db:
        require(current(db, request), ["Suporte"])
        row = db.get(Item, rid)
        if not row or row.kind != "ticket":
            fail("Chamado não encontrado.", 404)
        db.delete(row)
        return {"ok": True}
