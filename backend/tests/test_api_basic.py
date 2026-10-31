"""Health, session CRUD, upload validation and dashboard endpoints."""

from __future__ import annotations


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["database"] == "ok"
    assert body["data_dir_writable"] is True
    assert "detector" in body and "audio_vad" in body and "llm" in body
    assert body["ffmpeg"]["available"] is True


def test_models_endpoint(client):
    response = client.get("/api/models")
    assert response.status_code == 200
    body = response.json()
    assert body["detector"]["requested"] == "none"
    assert body["detector"]["active"] == "none"
    assert "offline" in body["notes"]


def test_create_and_get_session(client):
    response = client.post(
        "/api/sessions",
        json={"title": "Algebra", "subject": "Maths", "session_date": "2026-04-02"},
    )
    assert response.status_code == 201
    session = response.json()
    assert session["status"] == "created"
    assert session["title"] == "Algebra"
    assert session["sample_interval_sec"] > 0

    detail = client.get(f"/api/sessions/{session['id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == session["id"]
    assert detail.json()["latest_job"] is None

    listing = client.get("/api/sessions")
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_session_validation_errors(client):
    response = client.post("/api/sessions", json={"title": "   ", "subject": "Maths"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"

    response = client.post("/api/sessions", json={"title": "x", "subject": "Maths", "window_sec": 5})
    assert response.status_code == 422


def test_missing_session_returns_structured_404(client):
    response = client.get("/api/sessions/deadbeef")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "session_not_found"


def test_upload_requires_a_file(client, created_session):
    response = client.post(f"/api/sessions/{created_session['id']}/upload")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "missing_file"


def test_upload_rejects_unsupported_extension(client, created_session):
    response = client.post(
        f"/api/sessions/{created_session['id']}/upload",
        files={"video": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "upload_rejected"


def test_upload_rejects_corrupt_media(client, created_session):
    response = client.post(
        f"/api/sessions/{created_session['id']}/upload",
        files={"video": ("broken.mp4", b"this is not a real video", "video/mp4")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_media"


def test_process_without_media_is_rejected(client, created_session):
    response = client.post(f"/api/sessions/{created_session['id']}/process")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "no_media"


def test_upload_valid_video_stores_internal_name(client, created_session, media_files):
    video, _audio = media_files
    with video.open("rb") as handle:
        response = client.post(
            f"/api/sessions/{created_session['id']}/upload",
            files={"video": ("lesson.mp4", handle, "video/mp4")},
        )
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["status"] == "uploaded"
    assert body["duration_sec"] > 0
    assert body["video_filename"].startswith("video-")
    assert body["video_filename"] != "lesson.mp4"

    status = client.get(f"/api/sessions/{created_session['id']}/status").json()
    assert status["media_ready"] is True
    assert status["status"] == "uploaded"


def test_delete_session_removes_record_and_files(client, created_session, media_files):
    video, _audio = media_files
    with video.open("rb") as handle:
        client.post(
            f"/api/sessions/{created_session['id']}/upload",
            files={"video": ("lesson.mp4", handle, "video/mp4")},
        )
    response = client.delete(f"/api/sessions/{created_session['id']}")
    assert response.status_code == 204
    assert client.get(f"/api/sessions/{created_session['id']}").status_code == 404

    from backend.app.config import get_config

    assert not (get_config().resolved_data_dir / "sessions" / created_session["id"]).exists()


def test_unknown_api_route_is_json_404(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_media_is_not_served_over_http(client, created_session, media_files):
    video, _audio = media_files
    with video.open("rb") as handle:
        client.post(
            f"/api/sessions/{created_session['id']}/upload",
            files={"video": ("lesson.mp4", handle, "video/mp4")},
        )
    for path in ("/api/sessions/%s/media/video" % created_session["id"], "/media/lesson.mp4"):
        response = client.get(path)
        if path.startswith("/api"):
            assert response.status_code == 404
        # No raw media is ever returned: the SPA fallback serves HTML, not the video.
        assert not response.headers.get("content-type", "").startswith("video/")
        assert b"ftyp" not in response.content


def test_demo_seed_and_dashboard(client):
    seeded = client.post("/api/demo/seed")
    assert seeded.status_code == 201, seeded.text
    demo = seeded.json()
    assert demo["is_demo"] is True
    assert demo["status"] == "completed"

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["total_sessions"] == 1
    assert body["completed_sessions"] == 1
    assert body["total_attendance_records"] == 6
    assert body["average_attendance_rate"] is not None
    assert body["recent_sessions"][0]["is_demo"] is True
    assert body["recent_events"]
    assert body["engagement_trend"]

    cleared = client.delete("/api/demo")
    assert cleared.status_code == 200
    assert cleared.json()["removed_sessions"] == 1
    assert client.get("/api/dashboard").json()["total_sessions"] == 0


def test_dashboard_empty_state(client):
    body = client.get("/api/dashboard").json()
    assert body["total_sessions"] == 0
    assert body["total_attendance_records"] == 0
    assert body["average_attendance_rate"] is None
    assert body["average_engagement"] is None
    assert body["recent_sessions"] == []
