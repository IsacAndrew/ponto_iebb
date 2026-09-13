from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from ..db import Audit, reading
from ..rules import ADMIN, valid_date
from ..security import current, require

router = APIRouter()


@router.post("/api/month/{month}/export")
def export(month: str, request: Request):
    valid_date(month + "-01")
    from ..excel import export_month

    with reading() as db:
        require(current(db, request), ADMIN)
        binary = export_month(db, month)
    return Response(
        binary,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="Ponto_{month}.xlsx"'},
    )


@router.get("/api/reports/teachers")
def teachers_report(request: Request):
    from ..excel import export_teachers

    with reading() as db:
        require(current(db, request), ADMIN)
        binary = export_teachers(db)
    return Response(
        binary,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Professores.xlsx"'},
    )


@router.get("/api/audit")
def audit_list(request: Request, month: str):
    valid_date(month + "-01")
    with reading() as db:
        require(current(db, request), ADMIN)
        return [
            {
                "id": a.id,
                "at": a.at,
                "actor": a.actor,
                "action": a.action,
                "target": a.target,
                "before": a.before,
                "after": a.after,
                "reason": a.reason,
            }
            for a in db.scalars(select(Audit).order_by(Audit.id.desc()))
            if month in a.target or a.at.startswith(month)
        ]
