"""Regressões da versão 3, verificadas com dados descartáveis."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from test_system import add_person, at, client, clock, set_schedule  # noqa: F401

from backend.db import Audit, Day, Person, init, transaction
from backend.main import app
from backend.security import verify


def test_theme_is_saved_per_account_and_validated(client):
    pid = add_person(login="theme-other")
    assert (
        client.put(
            "/api/profile/theme", json={"theme": "dark", "person_id": pid}
        ).status_code
        == 200
    )
    assert client.get("/api/me").json()["user"]["theme"] == "dark"
    with transaction() as db:
        assert (db.get(Person, pid).details or {}).get("theme") is None
    assert (
        client.put("/api/profile/theme", json={"theme": "invalid"}).status_code == 400
    )
    with TestClient(app) as other:
        other.headers["X-Ponto"] = "1"
        assert (
            other.put("/api/profile/theme", json={"theme": "light"}).status_code == 401
        )
        other.post(
            "/api/login", json={"login": "theme-other", "password": "definitiva1"}
        )
        assert other.get("/api/me").json()["user"]["theme"] == "light"
        other.post("/api/logout", json={})
        other.post("/api/login", json={"login": "suporte", "password": "definitiva1"})
        assert other.get("/api/me").json()["user"]["theme"] == "dark"
        assert (
            other.put("/api/profile/theme", json={"theme": "light"}).status_code == 200
        )
        assert other.get("/api/me").json()["user"]["theme"] == "light"


def test_resolved_occurrence_does_not_reappear(client):
    with transaction() as db:
        db.add(
            Day(
                key="1:2026-09-02",
                person_id=1,
                date="2026-09-02",
                periods=[["07:00", "15:00"]],
                punches=[{"time": "07:00"}],
                absent=False,
                overtime="",
            )
        )
    first = client.get("/api/support/occurrences").json()
    rid = first[0]["id"]
    assert (
        client.post(
            f"/api/support/occurrences/{rid}", json={"reason": "Analisado"}
        ).status_code
        == 200
    )
    again = client.get("/api/support/occurrences").json()
    assert len(again) == 1 and again[0]["status"] == "Concluída"
    # A different incomplete state requires a fresh review.
    with transaction() as db:
        day = db.get(Day, "1:2026-09-02")
        day.punches = [{"time": "08:00"}]
    again = client.get("/api/support/occurrences").json()
    assert len(again) == 2 and sum(r["status"] == "Pendente" for r in again) == 1


@pytest.mark.parametrize(
    "days", [{"0": None}, {"0": [None]}, {"0": [["07:00"]]}, {"0": "invalid"}]
)
def test_malformed_schedule_is_rejected_without_server_error(client, days):
    result = client.post(
        "/api/people/1/schedules", json={"effective": "2026-09-03", "days": days}
    )
    assert result.status_code == 422


def test_default_password_allows_access_and_optional_change(client):
    credentials = []
    for login in ["new-one", "new-two"]:
        result = client.post(
            "/api/people", json={"name": login, "login": login, "role": "Professor"}
        )
        assert result.status_code == 200
        person = result.json()
        credential = person["initial_password"]
        credentials.append(credential)
        assert credential == "102030"
        assert "initial_password" not in client.get("/api/people").text
        with transaction() as db:
            assert verify(credential, db.get(Person, person["id"]).password)
            assert credential not in json.dumps(
                [a.after for a in db.scalars(select(Audit))]
            )
        with TestClient(app) as user:
            user.headers["X-Ponto"] = "1"
            assert (
                user.post(
                    "/api/login", json={"login": login, "password": credential}
                ).status_code
                == 200
            )
            assert (
                user.get("/api/records?start=2026-09-03&end=2026-09-03").status_code
                == 200
            )
            assert (
                user.post("/api/password", json={"password": credential}).status_code
                == 400
            )
            assert (
                user.post(
                    "/api/password", json={"password": "my-new-password"}
                ).status_code
                == 200
            )
            assert user.get("/api/punch/today").status_code == 200
    assert credentials == ["102030", "102030"]


def test_reset_returns_a_new_credential_and_invalidates_session(client):
    pid = add_person(login="reset-v3")
    with TestClient(app) as user:
        user.headers["X-Ponto"] = "1"
        user.post("/api/login", json={"login": "reset-v3", "password": "definitiva1"})
        result = client.post(f"/api/people/{pid}/reset", json={})
        assert result.status_code == 200
        assert user.get("/api/me").status_code == 401
        assert (
            user.post(
                "/api/login",
                json={
                    "login": "reset-v3",
                    "password": result.json()["initial_password"],
                },
            ).status_code
            == 200
        )
        assert user.get("/api/me").json()["user"]["temporary"] is True


def test_baseline_migration_is_repeatable_and_preserves_data(client):
    pid = add_person(login="migration-survivor")
    # Version 2 has the application tables but no Alembic revision yet.
    with transaction() as db:
        db.execute(text("DELETE FROM alembic_version"))
    init()
    init()
    with transaction() as db:
        assert db.get(Person, pid).login == "migration-survivor"


def test_correction_preserves_original_access_role(client):
    pid = add_person()
    with transaction() as db:
        p = db.get(Person, pid)
        p.details = {"roles": ["Professor", "Administração"]}
        db.add(
            Day(
                key=f"{pid}:2026-09-02",
                person_id=pid,
                date="2026-09-02",
                periods=[["07:00", "15:00"]],
                punches=[{"time": "07:00", "access_role": "Administração"}],
                absent=False,
                overtime="",
            )
        )
    assert (
        client.post(
            "/api/corrections",
            json={
                "person_id": pid,
                "date": "2026-09-02",
                "times": ["07:05", "15:00"],
                "reason": "Ajuste solicitado",
            },
        ).status_code
        == 200
    )
    rows = client.get(
        f"/api/records?start=2026-09-02&end=2026-09-02&person_id={pid}"
    ).json()
    assert rows[0]["role"] == "Administração"


def test_qr_two_punch_day_has_exit_confirmation(client, monkeypatch):
    set_schedule(1, [["07:00", "15:00"]])
    token = client.post("/api/system/qr", json={}).json()["url"].split("/q/")[1]
    payload = {
        "key": "qr-enter-v3",
        "lat": -23.67637077,
        "lon": -46.76243126,
        "accuracy": 10,
    }
    assert client.post(f"/api/qr/{token}/punch", json=payload).status_code == 200
    at(monkeypatch, "2026-09-03T15:00:00")
    result = client.post(
        f"/api/qr/{token}/punch", json={**payload, "key": "qr-exit-v3"}
    )
    assert result.status_code == 200 and result.json()["label"] == "Saída"
    assert "saída" in result.json()["confirmation"]
