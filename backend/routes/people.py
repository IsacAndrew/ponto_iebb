from datetime import date, timedelta

from fastapi import APIRouter, Body, Request
from sqlalchemy import select

from ..db import Day, Person, Schedule, audit, reading, today, transaction
from ..rules import (
    ADMIN,
    CLASSES,
    ROLES,
    effective_role,
    fail,
    get_day,
    minutes,
    roles_for,
    valid_date,
    validate_days,
)
from ..schemas import ScheduleInput
from ..security import FULL_ACCESS, current, password_hash, public, require

router = APIRouter()


def person_data(p):
    return {**public(p), "login": p.login}


@router.get("/api/people")
def people(request: Request):
    with reading() as db:
        require(current(db, request), ADMIN)
        scheduled = {
            pid
            for pid, days in db.execute(select(Schedule.person_id, Schedule.days))
            if any(days.values())
        }
        return [
            {**person_data(p), "has_schedule": p.id in scheduled}
            for p in db.scalars(select(Person).order_by(Person.name))
        ]


def clean_person(data):
    name = str(data.get("name", "")).strip()
    login = str(data.get("login", "")).strip().lower()
    role = data.get("role")
    if (
        not name
        or len(name) > 160
        or not login
        or len(login) > 100
        or role not in ROLES
    ):
        fail("Preencha nome, login e perfil válidos.")
    if not isinstance(data.get("details", {}), dict) or not isinstance(
        data.get("roles", [role]), list
    ):
        fail("Confira os dados e perfis da pessoa.")
    details = {
        k: str(data.get("details", {}).get(k, ""))[:250]
        for k in ("email", "phone", "birth")
    }
    details["phone"] = "".join(c for c in details["phone"] if c.isdigit())
    requested = data.get("roles", [role])
    assigned = list(dict.fromkeys(r for r in requested if r in ROLES))
    if role not in assigned:
        assigned.insert(0, role)
    if len(assigned) > 2:
        fail("Selecione no máximo dois perfis de acesso.")
    details["roles"] = assigned
    return name, login, role, details


def editable(actor, target, role=None, assigned=None):
    target_roles = list(
        dict.fromkeys((roles_for(target) if target else []) + (assigned or [role]))
    )
    if effective_role(actor) == "Administração" and any(
        value in FULL_ACCESS for value in target_roles
    ):
        fail("Somente Diretoria ou Suporte gerenciam esse perfil.", 403)


@router.post("/api/people")
def add_person(request: Request, data: dict = Body(...)):
    with transaction() as db:
        actor = current(db, request)
        require(actor, ADMIN)
        name, login, role, details = clean_person(data)
        editable(actor, None, role, details["roles"])
        if db.scalar(select(Person.id).where(Person.login == login)):
            fail("Este login já está em uso.")
        hired = valid_date(data.get("hired", today()))
        credential = "102030"
        p = Person(
            name=name,
            login=login,
            role=role,
            details=details,
            hired=hired,
            password=password_hash(credential),
            session={},
        )
        db.add(p)
        db.flush()
        audit(db, actor, "Cadastrar pessoa", p.id, after=person_data(p))
        return {**person_data(p), "initial_password": credential}


@router.put("/api/people/{pid}")
def update_person(pid: int, request: Request, data: dict = Body(...)):
    with transaction() as db:
        actor = current(db, request)
        require(actor, ADMIN)
        p = db.get(Person, pid)
        if not p:
            fail("Pessoa não encontrada.", 404)
        name, login, role, details = clean_person(data)
        editable(actor, p, role, details["roles"])
        if actor.id == pid and details["roles"] != roles_for(p):
            fail("Você não pode alterar o próprio perfil de acesso.")
        if db.scalar(select(Person.id).where(Person.login == login, Person.id != pid)):
            fail("Este login já está em uso.")
        before = person_data(p)
        for key in ("lessons", "subjects_by_class"):
            if key in p.details:
                details[key] = p.details[key]
        p.name, p.login, p.role, p.details, p.hired = (
            name,
            login,
            role,
            details,
            valid_date(data.get("hired", p.hired)),
        )
        if before["roles"] != details["roles"]:
            p.session = {}
        audit(
            db,
            actor,
            "Alterar cadastro",
            pid,
            before,
            person_data(p),
            data.get("reason", "Atualização cadastral"),
        )
        return person_data(p)


@router.post("/api/people/{pid}/reset")
def reset(pid: int, request: Request):
    with transaction() as db:
        actor = current(db, request)
        require(actor, FULL_ACCESS)
        p = db.get(Person, pid)
        if not p:
            fail("Pessoa não encontrada.", 404)
        editable(actor, p)
        credential = "102030"
        p.password = password_hash(credential)
        p.temporary = True
        p.session = {}
        audit(db, actor, "Redefinir senha temporária", pid)
        return {"ok": True, "initial_password": credential}


@router.post("/api/people/{pid}/deactivate")
def deactivate(pid: int, request: Request, data: dict = Body(...)):
    with transaction() as db:
        actor = current(db, request)
        require(actor, ADMIN)
        p = db.get(Person, pid)
        if not p:
            fail("Pessoa não encontrada.", 404)
        editable(actor, p)
        if p.id == actor.id:
            fail("Você não pode desativar sua própria conta.")
        d = valid_date(data.get("date", today()))
        if d > today() or d < p.hired:
            fail("Informe uma data entre a admissão e hoje.")
        if db.scalar(select(Day.key).where(Day.person_id == pid, Day.date > d)):
            fail(
                "Existem registros após essa data. Use a data do último dia trabalhado."
            )
        p.active = False
        p.terminated = d
        p.session = {}
        audit(
            db,
            actor,
            "Inativar pessoa",
            pid,
            after={"date": d},
            reason=data.get("reason", "Desligamento"),
        )
        return {"ok": True}


@router.get("/api/people/{pid}/schedules")
def schedules(pid: int, request: Request):
    with reading() as db:
        p = current(db, request)
        if p.id != pid:
            require(p, ADMIN)
        return [
            {
                "id": s.id,
                "effective": s.effective,
                "specific": s.specific,
                "days": s.days,
            }
            for s in db.scalars(
                select(Schedule)
                .where(Schedule.person_id == pid)
                .order_by(Schedule.effective.desc(), Schedule.id.desc())
            )
        ]


@router.post("/api/people/{pid}/schedules")
def add_schedule(pid: int, request: Request, data: ScheduleInput):
    data = data.model_dump(mode="json", exclude_none=True)
    with transaction() as db:
        actor = current(db, request)
        require(actor, ADMIN)
        p = db.get(Person, pid)
        if not p:
            fail("Pessoa não encontrada.", 404)
        d = valid_date(data.get("effective"))
        days = validate_days(data.get("days", {}))
        specific = bool(data.get("specific"))
        if d < today():
            fail("Uma nova jornada não pode alterar o passado.")
        row = get_day(db, p, d)
        if d == today() and row and row.punches:
            d = (date.fromisoformat(d) + timedelta(days=1)).isoformat()
        db.add(Schedule(person_id=pid, effective=d, days=days, specific=specific))
        if row and not row.punches and row.date == d:
            row.periods = days.get(str(date.fromisoformat(d).weekday()), [])
        audit(
            db,
            actor,
            "Alterar jornada",
            f"{pid}:{d}",
            after={"days": days, "specific": specific},
            reason=data.get("reason", "Nova vigência"),
        )
        return {"effective": d, "deferred": d != data.get("effective")}


def clean_subjects(values):
    if not isinstance(values, dict):
        fail("Confira as matérias e turmas.")
    result = {}
    for classroom, values in values.items():
        if not isinstance(values, list):
            fail("Confira as matérias da turma.")
        if classroom not in CLASSES:
            fail("Confira a turma.")
        clean = []
        for value in values:
            subject = str(value).strip()[:80]
            if subject and subject not in clean:
                clean.append(subject)
        if clean:
            result[classroom] = clean
    return result


@router.put("/api/people/{pid}/lessons")
def lessons(pid: int, request: Request, data: dict = Body(...)):
    with transaction() as db:
        actor = current(db, request)
        require(actor, ADMIN)
        p = db.get(Person, pid)
        if not p or "Professor" not in roles_for(p):
            fail("Selecione um professor.")
        rows = data.get("lessons", [])
        subjects = (
            clean_subjects(data["subjects"])
            if "subjects" in data
            else p.details.get("subjects_by_class", {})
        )
        if not isinstance(rows, list):
            fail("Confira as aulas da grade.")
        counts = {}
        normalized = []
        weekdays = [
            "Segunda-feira",
            "Terça-feira",
            "Quarta-feira",
            "Quinta-feira",
            "Sexta-feira",
            "Sábado",
            "Domingo",
        ]
        for row in rows:
            if not isinstance(row, dict):
                fail("Confira os dados da aula.")
            day = str(row.get("day"))
            if day not in list(map(str, range(7))):
                fail("Selecione o dia da semana da aula.")
            counts[day] = counts.get(day, 0) + 1
            label = f"{weekdays[int(day)]}, {counts[day]}ª aula"
            try:
                valid_time = minutes(row.get("start")) < minutes(row.get("end"))
            except Exception:
                valid_time = False
            if not valid_time:
                fail(f"{label}: confira início e fim. O fim deve ser depois do início.")
            if row.get("class") not in CLASSES:
                fail(f"{label}: selecione uma Turma válida.")
            subject = str(row.get("subject", "")).strip()[:80]
            if subject not in subjects.get(row.get("class"), []):
                fail(
                    f"{label}: selecione uma Matéria cadastrada para {row.get('class')}."
                )
            normalized.append({**row, "day": day, "subject": subject})
        before = p.details
        p.details = {**p.details, "lessons": normalized, "subjects_by_class": subjects}
        audit(db, actor, "Alterar grade pedagógica", pid, before, p.details)
        return {"ok": True}


@router.put("/api/people/{pid}/subjects")
def subjects(pid: int, request: Request, data: dict = Body(...)):
    with transaction() as db:
        actor = current(db, request)
        require(actor, ADMIN)
        person = db.get(Person, pid)
        if not person or "Professor" not in roles_for(person):
            fail("Selecione um professor.")
        result = clean_subjects(data.get("subjects", {}))
        before = person.details
        person.details = {**person.details, "subjects_by_class": result}
        audit(db, actor, "Alterar matérias do professor", pid, before, person.details)
        return {"subjects": result}
