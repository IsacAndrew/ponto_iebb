"""Servidor exclusivo dos testes de navegador; nunca usa o banco da aplicação."""

import os
import sys
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
temporary = TemporaryDirectory(prefix="ponto-e2e-")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(temporary.name) / "e2e.db")
os.environ["BOOTSTRAP_PASSWORD"] = "only-for-e2e-tests"
os.environ.pop("RENDER", None)

import uvicorn

from backend import db, main, rules
from backend.routes import attendance, auth, people, reports, requests, support, system
from backend.security import password_hash

NOW = datetime.fromisoformat("2026-09-03T07:10:00-03:00")
for module in (
    main,
    db,
    rules,
    auth,
    attendance,
    people,
    requests,
    support,
    system,
    reports,
):
    module.now = lambda: NOW
    module.today = lambda: NOW.date().isoformat()
db.init()
with db.transaction() as session:
    session.add(
        db.Person(
            name="Isac Andrew",
            login="suporte",
            role="Suporte",
            password=password_hash("e2e-password"),
            temporary=False,
            active=True,
            hired="2026-01-01",
            details={},
            session={},
        )
    )
    session.add(
        db.Setting(
            key="geo",
            data={
                "lat": -23.67637077,
                "lon": -46.76243126,
                "verified": True,
                "accuracy": 100,
                "accuracy_version": 2,
            },
        )
    )
try:
    uvicorn.run(main.app, host="127.0.0.1", port=5051)
finally:
    db.engine.dispose()
    temporary.cleanup()
