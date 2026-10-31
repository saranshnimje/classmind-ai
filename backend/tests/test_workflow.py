"""End-to-end recorded-media workflow with a deterministic mocked detector.

Real codec/media decoding is exercised (OpenCV + bundled ffmpeg). Only the
person detector is mocked here; real-detector verification is documented
separately because it requires model weights and a real recording.
"""

from __future__ import annotations

from pathlib import Path

from backend.app.database import SessionLocal
from backend.app.models import Session
from backend.app.services.pipeline import pipeline


def upload(client, session_id: str, video: Path | None = None, audio: Path | None = None):
    files = {}
    handles = []
    try:
        if video is not None:
            handle = video.open("rb")
            handles.append(handle)
            files["video"] = (video.name, handle, "video/mp4")
        if audio is not None:
            handle = audio.open("rb")
            handles.append(handle)
            files["audio"] = (audio.name, handle, "audio/wav")
        return client.post(f"/api/sessions/{session_id}/upload", files=files)
    finally:
        for handle in handles:
            handle.close()


def test_full_recorded_workflow(client, created_session, media_files, fake_detector):
    session_id = created_session["id"]
    video, audio = media_files

    upload_response = upload(client, session_id, video, audio)
    assert upload_response.status_code == 202, upload_response.text

    # Synchronous run keeps the test deterministic; production uses a background worker.
    pipeline.run_now(session_id)

    status = client.get(f"/api/sessions/{session_id}/status").json()
    assert status["status"] == "completed", status
    assert status["progress"] == 100.0
    assert status["job"]["status"] == "completed"
    assert status["job"]["stage"] == "completed"

    session = client.get(f"/api/sessions/{session_id}").json()
    assert session["detector_used"] == "fake-test"
    assert session["has_audio"] is True
    assert session["duration_sec"] > 0
    assert session["average_engagement"] is not None

    attendance = client.get(f"/api/sessions/{session_id}/attendance").json()
    assert attendance["total_detected"] == 2
    assert attendance["present"] == 2
    assert attendance["late"] == 0
    assert attendance["unconfirmed"] == 0
    assert attendance["attendance_rate"] == 100.0
    assert len(attendance["tracks"]) == 2
    first = attendance["records"][0]
    assert first["presence_sec"] >= 2
    assert first["first_seen_sec"] <= first["last_seen_sec"]

    analytics = client.get(f"/api/sessions/{session_id}/analytics").json()
    assert len(analytics["windows"]) >= 1
    assert analytics["audio"]["available"] is True
    assert analytics["audio"]["speech_active_sec"] > 0
    assert analytics["quality"]["score"] in {"good", "partial", "poor"}
    assert analytics["quality"]["detector"] == "fake-test"
    assert analytics["quality"]["sampled_frames"] >= 1
    assert analytics["methodology"]["engagement_proxy"]["formula"]
    assert "not" in analytics["methodology"]["engagement_proxy"]["definition"].lower()

    recs = client.get(f"/api/sessions/{session_id}/recommendations").json()
    assert recs["generated_by"] == "rules"
    assert recs["llm_available"] is False
    assert recs["recommendations"]
    for rec in recs["recommendations"]:
        assert rec["evidence"]
        assert rec["observed"]
        assert rec["interpretation"]
        assert rec["source"] == "rule"

    report = client.get(f"/api/sessions/{session_id}/report").json()
    assert report["session"]["id"] == session_id
    assert report["attendance"]["total_detected"] == 2
    assert report["quality"]["detector"] == "fake-test"
    assert report["limitations"]

    html = client.get(f"/api/sessions/{session_id}/report.html")
    assert html.status_code == 200
    assert "text/html" in html.headers["content-type"]
    assert "Test lesson" in html.text
    assert "Limitations" in html.text
    assert "Privacy &amp; ethics" in html.text

    csv_report = client.get(f"/api/sessions/{session_id}/report.csv")
    assert csv_report.status_code == 200
    assert "ATTENDANCE" in csv_report.text
    assert "RECOMMENDATIONS" in csv_report.text

    attendance_csv = client.get(f"/api/sessions/{session_id}/attendance.csv")
    assert attendance_csv.status_code == 200
    assert "participant" in attendance_csv.text.lower()
    assert "present" in attendance_csv.text.lower()

    # Persistence across a fresh database session (simulates an app restart).
    db = SessionLocal()
    try:
        stored = db.get(Session, session_id)
        assert stored is not None
        assert stored.status == "completed"
        assert len(stored.attendance) == 2
        assert len(stored.windows) >= 1
        assert stored.recommendations
    finally:
        db.close()

    # Reprocessing must replace results rather than duplicate them.
    pipeline.run_now(session_id)
    attendance_again = client.get(f"/api/sessions/{session_id}/attendance").json()
    assert attendance_again["total_detected"] == 2


def test_manual_mapping_workflow(client, created_session, media_files, fake_detector):
    session_id = created_session["id"]
    video, audio = media_files
    assert upload(client, session_id, video, audio).status_code == 202
    pipeline.run_now(session_id)

    roster = client.post(
        "/api/roster",
        json={"name": "Asha Rao", "external_id": "S-101", "class_label": "MATH-101"},
    )
    assert roster.status_code == 201
    roster_id = roster.json()["id"]

    tracks = client.get(f"/api/sessions/{session_id}/attendance").json()["tracks"]
    track_id = tracks[0]["id"]

    without_confirmation = client.post(
        f"/api/sessions/{session_id}/attendance/{track_id}/map",
        json={"roster_id": roster_id},
    )
    assert without_confirmation.status_code == 400
    assert without_confirmation.json()["error"]["code"] == "confirmation_required"

    mapped = client.post(
        f"/api/sessions/{session_id}/attendance/{track_id}/map",
        json={"roster_id": roster_id, "confirm_manual": True},
    )
    assert mapped.status_code == 200, mapped.text
    assert mapped.json()["display_name"] == "Asha Rao"
    assert mapped.json()["roster_id"] == roster_id

    summary = client.get(f"/api/sessions/{session_id}/attendance").json()
    assert summary["mapped"] == 1
    csv_text = client.get(f"/api/sessions/{session_id}/attendance.csv").text
    assert "Asha Rao" in csv_text

    unmapped = client.post(
        f"/api/sessions/{session_id}/attendance/{track_id}/map",
        json={"roster_id": None, "confirm_manual": True},
    )
    assert unmapped.status_code == 200
    assert unmapped.json()["display_name"].startswith("Participant")

    deleted = client.delete(f"/api/roster/{roster_id}")
    assert deleted.status_code == 204


def test_audio_only_session_completes(client, created_session, media_files):
    session_id = created_session["id"]
    _video, audio = media_files
    assert upload(client, session_id, audio=audio).status_code == 202
    pipeline.run_now(session_id)

    status = client.get(f"/api/sessions/{session_id}/status").json()
    assert status["status"] == "completed", status
    attendance = client.get(f"/api/sessions/{session_id}/attendance").json()
    assert attendance["total_detected"] == 0
    assert any("No participant tracks" in w for w in attendance["warnings"])
    analytics = client.get(f"/api/sessions/{session_id}/analytics").json()
    assert analytics["audio"]["available"] is True
    # No video means no visual signal; the proxy must not pretend otherwise.
    assert analytics["windows"][0]["movement_index"] is None
    assert analytics["windows"][0]["audio_active_ratio"] is not None


def test_missing_media_file_marks_session_failed(client, created_session, media_files):
    session_id = created_session["id"]
    video, _audio = media_files
    assert upload(client, session_id, video).status_code == 202

    from backend.app.config import get_config
    from backend.app.services.storage import media_path

    db = SessionLocal()
    try:
        stored = db.get(Session, session_id)
        media_path(session_id, stored.video_filename).unlink()
    finally:
        db.close()

    pipeline.run_now(session_id)
    status = client.get(f"/api/sessions/{session_id}/status").json()
    assert status["status"] == "failed"
    assert "missing" in (status["error"] or "").lower()
    assert status["job"]["status"] == "failed"

    # A failed session can be deleted cleanly.
    assert client.delete(f"/api/sessions/{session_id}").status_code == 204
    assert not (get_config().resolved_data_dir / "sessions" / session_id).exists()


def test_report_before_processing_returns_409(client, created_session):
    from backend.app.config import get_config

    session_id = created_session["id"]
    response = client.get(f"/api/sessions/{session_id}/report")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "not_ready"
    assert get_config().resolved_data_dir.exists()
