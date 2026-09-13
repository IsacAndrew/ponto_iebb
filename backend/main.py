import logging
import os
import secrets
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from .db import ROOT, Person, Setting, init, reading, today, transaction
from .rules import fail
from .security import password_hash


@asynccontextmanager
async def lifespan(app):
    init()
    with transaction() as db:
        if not db.scalar(select(Person.id).limit(1)):
            login = os.getenv("BOOTSTRAP_LOGIN", "suporte")
            if not os.getenv("BOOTSTRAP_PASSWORD"):
                raise RuntimeError("Defina BOOTSTRAP_PASSWORD no primeiro deploy.")
            db.add(
                Person(
                    name="Isac",
                    login=login,
                    password=password_hash(os.environ["BOOTSTRAP_PASSWORD"]),
                    role="Suporte",
                    hired=today(),
                    details={},
                    session={},
                )
            )
        if not db.get(Setting, "geo"):
            db.add(
                Setting(
                    key="geo",
                    data={
                        "lat": -23.67637077,
                        "lon": -46.76243126,
                        "verified": False,
                        "accuracy": 500,
                        "accuracy_version": 2,
                    },
                )
            )
    yield


app = FastAPI(title="Ponto IEBB", version="3.0.0", lifespan=lifespan)


@app.middleware("http")
async def protection(request, call_next):
    if (
        request.method not in ("GET", "HEAD", "OPTIONS")
        and request.headers.get("x-ponto") != "1"
    ):
        return JSONResponse({"detail": "Requisição não autorizada."}, status_code=403)
    request_id = secrets.token_hex(6)
    try:
        response = await call_next(request)
    except Exception as exc:
        original = getattr(exc, "orig", exc)
        frames = " > ".join(
            f"{Path(f.filename).name}:{f.lineno}:{f.name}"
            for f in traceback.extract_tb(exc.__traceback__)
        )
        logging.getLogger("ponto").error(
            "request=%s method=%s path=%s error=%s sqlstate=%s frames=%s",
            request_id,
            request.method,
            request.url.path,
            type(original).__name__,
            getattr(original, "sqlstate", None),
            frames,
        )
        status = 503 if isinstance(exc, SQLAlchemyError) else 500
        response = JSONResponse(
            {
                "detail": "Não foi possível salvar agora. Tente novamente."
                if request.method != "GET"
                else "Não foi possível carregar agora. Tente novamente.",
                "reference": request_id,
            },
            status_code=status,
        )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    try:
        with reading() as db:
            db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            {"status": "unavailable", "version": "3.0.0"}, status_code=503
        )
    return {"status": "ok", "version": "3.0.0"}


from .routes import attendance, auth, people, reports, requests, support, system

for module in (auth, attendance, people, requests, support, system, reports):
    app.include_router(module.router)

dist = ROOT / "frontend" / "dist"

if dist.exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.api_route("/{path:path}", methods=["GET", "HEAD"])
    def frontend(path: str):
        if path.startswith("api/"):
            fail("Recurso não encontrado.", 404)
        return FileResponse(dist / "index.html")
