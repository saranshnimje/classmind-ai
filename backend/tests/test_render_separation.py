"""Verify Render backend-only behavior and health endpoint integrity."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"


def test_root_with_backend_only():
    with patch.dict("os.environ", {"CLASSMIND_BACKEND_ONLY": "true"}, clear=False):
        # Restarting app in test requires reimport; simplest is to rely on env
        # being read at route time. The serve_frontend checks env directly.
        # Since route reads env live, no restart needed.
        resp = client.get("/")
        # When CLASSMIND_BACKEND_ONLY=true, root should return JSON status,
        # not HTML SPA (200 with JSON content-type).
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        body = resp.json()
        assert body.get("service") == "ClassMind AI backend"
        assert "docs" in body
        assert "health" in body
