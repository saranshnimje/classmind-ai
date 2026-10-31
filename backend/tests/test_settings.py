"""Settings validation, persistence and retention behaviour."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.app.database import SessionLocal
from backend.app.models import AppSetting, Session


def test_settings_defaults(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["min_presence_sec"] > 0
    assert body["sample_interval_sec"] > 0
    assert body["window_sec"] >= 30
    assert body["detector_backend"] in {"auto", "yolo", "hog", "none"}
    assert body["data_dir"]
    assert "detector" in body["models"]
    assert body["limits"]["max_upload_mb"] > 0


def test_settings_update_and_persistence(client):
    response = client.put(
        "/api/settings",
        json={
            "min_presence_sec": 45,
            "sample_interval_sec": 1.5,
            "window_sec": 120,
            "late_after_sec": 200,
            "retention_days": 30,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["min_presence_sec"] == 45
    assert body["window_sec"] == 120

    db = SessionLocal()
    try:
        row = db.get(AppSetting, "preferences")
        assert row is not None
        assert row.value_json["min_presence_sec"] == 45
    finally:
        db.close()

    # New sessions inherit the persisted defaults.
    created = client.post(
        "/api/sessions", json={"title": "Inherited", "subject": "Physics", "session_date": "2026-05-01"}
    )
    assert created.status_code == 201
    assert created.json()["min_presence_sec"] == 45
    assert created.json()["window_sec"] == 120


def test_settings_validation_rejects_bad_values(client):
    for payload in (
        {"min_presence_sec": 0},
        {"sample_interval_sec": 0.1},
        {"window_sec": 10},
        {"retention_days": -1},
        {"ollama_url": "file:///etc/passwd"},
        {"detector_backend": "magic"},
    ):
        response = client.put("/api/settings", json=payload)
        assert response.status_code == 422, payload


def test_retention_deletes_old_sessions(client, created_session):
    db = SessionLocal()
    try:
        stored = db.get(Session, created_session["id"])
        stored.created_at = datetime.now(timezone.utc) - timedelta(days=10)
        db.commit()
    finally:
        db.close()

    response = client.put("/api/settings", json={"retention_days": 1})
    assert response.status_code == 200
    assert client.get("/api/sessions").json() == []


def test_retention_keeps_recent_sessions(client, created_session):
    response = client.put("/api/settings", json={"retention_days": 30})
    assert response.status_code == 200
    listing = client.get("/api/sessions").json()
    assert len(listing) == 1
    assert listing[0]["id"] == created_session["id"]
