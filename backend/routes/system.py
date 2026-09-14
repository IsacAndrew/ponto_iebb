import base64
import io
import math
import os
import secrets
from pathlib import Path

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse
from fastapi.responses import Response as RawResponse
from sqlalchemy import delete, select, text

from ..db import Day, Person, Setting, audit, reading, today, transaction
from ..rules import ADMIN, fail, valid_date
from ..security import FULL_ACCESS, confirm, current, digest, require
from .attendance import location_accuracy, location_required

router = APIRouter()


@router.get("/api/calendar")
def calendar(request: Request):
    with reading() as db:
        require(current(db, request), ADMIN)
        return [
            {"date": r.key[8:], **r.data}
            for r in db.scalars(
                select(Setting)
                .where(Setting.key.like("holiday:%"))
                .order_by(Setting.key)
            )
        ]


@router.post("/api/calendar")
def save_holiday(request: Request, data: dict = Body(...)):
    with transaction() as db:
        actor = current(db, request)
        require(actor, ADMIN)
        d = valid_date(data.get("date"))
        name = str(data.get("name", "")).strip()
        row = db.get(Setting, "holiday:" + d)
        before = row.data if row else {}
        if not name:
            if row:
                db.delete(row)
        elif row:
            row.data = {"name": name[:120]}
        else:
            db.add(Setting(key="holiday:" + d, data={"name": name[:120]}))
        audit(db, actor, "Alterar calendário", d, before, {"name": name})
        return {"ok": True}


@router.get("/api/support/settings")
def settings(request: Request):
    with reading() as db:
        require(current(db, request), FULL_ACCESS)
        row = db.get(Setting, "geo")
        return (
            {**row.data, "accuracy": location_accuracy(row.data)}
            if row
            else {
                "lat": -23.67637077,
                "lon": -46.76243126,
                "accuracy": 500,
                "verified": False,
            }
        )


@router.put("/api/support/settings")
def save_settings(request: Request, data: dict = Body(...)):
    with transaction() as db:
        actor = current(db, request)
        require(actor, FULL_ACCESS)
        try:
            lat, lon, accuracy = (
                float(data["lat"]),
                float(data["lon"]),
                float(data["accuracy"]),
            )
        except (KeyError, ValueError, TypeError):
            fail("Confira as coordenadas e a precisão.")
        if (
            not all(math.isfinite(v) for v in [lat, lon, accuracy])
            or not -90 <= lat <= 90
            or not -180 <= lon <= 180
            or not 1 <= accuracy <= 500
        ):
            fail("Confira as coordenadas e a precisão máxima (1 a 500 m).")
        row = db.get(Setting, "geo")
        if not row:
            row = Setting(key="geo", data={})
            db.add(row)
        before = row.data
        row.data = {
            "lat": lat,
            "lon": lon,
            "accuracy": accuracy,
            "accuracy_version": 2,
            "verified": data.get("verified", before.get("verified", False)) is True,
        }
        audit(
            db,
            actor,
            "Configurar localização",
            "geo",
            before,
            row.data,
            "Confirmação do Suporte",
        )
        return row.data


@router.get("/api/system/storage")
def storage(request: Request):
    with reading() as db:
        require(current(db, request), FULL_ACCESS)
        if db.bind.dialect.name == "postgresql":
            used = int(
                db.execute(
                    text("SELECT pg_database_size(current_database())")
                ).scalar_one()
            )
        else:
            path = Path(db.bind.url.database)
            used = path.stat().st_size if path.exists() else 0
        limit = max(1, int(os.getenv("DB_STORAGE_LIMIT_MB", "500"))) * 1024 * 1024
        test_data = bool(
            db.scalar(
                select(Setting.key).where(Setting.key.like("storage-test:%")).limit(1)
            )
        )
        return {
            "connection_label": (
                "Conexão ativa: PostgreSQL (Supabase)"
                if db.bind.dialect.name == "postgresql"
                and (db.bind.url.host or "").endswith((".supabase.co", ".supabase.com"))
                else "Conexão ativa: PostgreSQL"
                if db.bind.dialect.name == "postgresql"
                else "Banco local: SQLite"
            ),
            "used_bytes": used,
            "limit_bytes": limit,
            "percent": round(min(100, used * 100 / limit), 2),
            "test_data": test_data,
        }


@router.post("/api/system/storage-test")
def create_storage_test(request: Request):
    with transaction() as db:
        actor = current(db, request)
        require(actor, ["Suporte"])
        limit = max(1, int(os.getenv("DB_STORAGE_LIMIT_MB", "500"))) * 1024 * 1024
        target = math.ceil(limit * 0.012)
        if target > 32 * 1024 * 1024:
            fail(
                "Este teste é limitado a 32 MB. O limite configurado do banco é alto demais para simular 1%."
            )
        remaining = target
        # Replace only the synthetic batch; repeated clicks do not accumulate data.
        db.execute(delete(Setting).where(Setting.key.like("storage-test:%")))
        index = 0
        while remaining:
            size = min(65536, remaining)
            payload = secrets.token_urlsafe(math.ceil(size * 3 / 4))[:size]
            db.add(
                Setting(
                    key=f"storage-test:{index}",
                    data={"synthetic": True, "payload": payload},
                )
            )
            remaining -= size
            index += 1
        audit(
            db,
            actor,
            "Gerar dados de teste de armazenamento",
            "sistema",
            after={"bytes": target},
            reason="Teste de limpeza solicitado pelo Suporte",
        )
    return {"created_bytes": target}


@router.post("/api/system/reset")
def reset_system(request: Request, data: dict = Body(...)):
    with transaction() as db:
        actor = current(db, request)
        require(actor, ["Suporte"])
        confirm(actor, data.get("password", ""))
        if data.get("confirmation") != "APAGAR":
            fail("Digite APAGAR para confirmar.")
        from ..reset import clear_system_data

        actor = clear_system_data(db, actor)
        audit(
            db,
            actor,
            "Apagar dados do sistema",
            "sistema",
            after={"preserved_account": actor.id},
            reason="Limpeza confirmada pelo Suporte",
        )
    response = JSONResponse({"ok": True})
    response.delete_cookie("ponto_session")
    return response


@router.get("/api/system/qr")
def get_global_qr(request: Request):
    with reading() as db:
        require(current(db, request), FULL_ACCESS)
        row = db.get(Setting, "qr-global")
        return {"active": bool(row), "url": ("/q/" + row.data["token"]) if row else ""}


@router.post("/api/system/qr")
def create_global_qr(request: Request):
    with transaction() as db:
        actor = current(db, request)
        require(actor, FULL_ACCESS)
        row = db.get(Setting, "qr-global")
        token = secrets.token_urlsafe(48)
        value = {"token": token, "hash": digest(token)}
        if row:
            row.data = value
        else:
            db.add(Setting(key="qr-global", data=value))
        audit(
            db,
            actor,
            "Gerar QR institucional",
            "sistema",
            before={"active": bool(row)},
            after={"active": True},
        )
        return {"active": True, "url": "/q/" + token}


@router.get("/api/system/qr/image")
def global_qr_image(request: Request):
    with reading() as db:
        require(current(db, request), FULL_ACCESS)
        row = db.get(Setting, "qr-global")
        if not row:
            fail("Gere o QR Code primeiro.", 404)
        import qrcode

        url = str(request.base_url).rstrip("/") + "/q/" + row.data["token"]
        image = qrcode.make(url)
        output = io.BytesIO()
        image.save(output, format="PNG")
        return RawResponse(
            output.getvalue(),
            media_type="image/png",
            headers={"Cache-Control": "no-store"},
        )


@router.get("/api/support/my-location")
def my_location(request: Request):
    with reading() as db:
        actor = current(db, request)
        require(actor, ["Suporte"])
        return {"required": location_required(db, actor)}


@router.put("/api/support/my-location")
def save_my_location(request: Request, data: dict = Body(...)):
    with transaction() as db:
        actor = current(db, request)
        require(actor, ["Suporte"])
        required = data.get("required") is not False
        key = f"geo-required:{actor.id}"
        row = db.get(Setting, key)
        before = location_required(db, actor)
        if row:
            row.data = {"required": required}
        else:
            db.add(Setting(key=key, data={"required": required}))
        audit(
            db,
            actor,
            "Alterar exigência de localização própria",
            actor.id,
            {"required": before},
            {"required": required},
        )
        return {"required": required}


@router.get("/api/favicon")
def favicon():
    with reading() as db:
        row = db.get(Setting, "favicon")
        if not row:
            return RawResponse(status_code=204)
        return RawResponse(
            base64.b64decode(row.data["content"]),
            media_type=row.data["type"],
            headers={"Cache-Control": "public, max-age=300"},
        )


@router.put("/api/favicon")
def save_favicon(request: Request, data: dict = Body(...)):
    with transaction() as db:
        actor = current(db, request)
        require(actor, FULL_ACCESS)
        content = str(data.get("content", ""))
        kind = str(data.get("type", ""))
        if kind not in ("image/png", "image/jpeg"):
            fail("Use uma imagem PNG, JPG ou JPEG.")
        try:
            raw = base64.b64decode(content, validate=True)
        except Exception:
            fail("Imagem inválida.")
        if not raw or len(raw) > 512000:
            fail("Use uma imagem de até 500 KB.")
        if (
            kind == "image/png"
            and not raw.startswith(b"\x89PNG")
            or kind == "image/jpeg"
            and not raw.startswith(b"\xff\xd8")
        ):
            fail("O conteúdo não corresponde ao formato da imagem.")
        row = db.get(Setting, "favicon")
        if row:
            row.data = {"type": kind, "content": content}
        else:
            db.add(Setting(key="favicon", data={"type": kind, "content": content}))
        audit(db, actor, "Alterar favicon", "sistema")
        return {"ok": True}


@router.delete("/api/favicon")
def remove_favicon(request: Request):
    with transaction() as db:
        actor = current(db, request)
        require(actor, FULL_ACCESS)
        row = db.get(Setting, "favicon")
        if row:
            db.delete(row)
            audit(db, actor, "Remover favicon", "sistema")
        return {"ok": True}


@router.get("/api/today-events")
def today_events(request: Request):
    with reading() as db:
        require(current(db, request), ADMIN)
        events = []
        for row in db.scalars(select(Day).where(Day.date == today())):
            person = db.get(Person, row.person_id)
            events += [
                {"time": x["time"], "name": person.name, "person_id": person.id}
                for x in row.punches
            ]
        return sorted(events, key=lambda x: x["time"])
