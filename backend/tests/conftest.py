"""Shared pytest fixtures.

Environment is configured *before* the application package is imported so the
test database and data directory are fully isolated from real user data.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import numpy as np

TMP_ROOT = Path(tempfile.mkdtemp(prefix="classmind-tests-"))
DATA_DIR = TMP_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

os.environ["CLASSMIND_DATA_DIR"] = str(DATA_DIR)
os.environ["CLASSMIND_DATABASE_URL"] = f"sqlite:///{(DATA_DIR / 'test.db').as_posix()}"
os.environ["CLASSMIND_DETECTOR_BACKEND"] = "none"
os.environ["CLASSMIND_OLLAMA_ENABLED"] = "false"
os.environ["CLASSMIND_ALLOW_MODEL_DOWNLOAD"] = "false"
os.environ["CLASSMIND_VAD_BACKEND"] = "energy"
os.environ["CLASSMIND_LOG_LEVEL"] = "WARNING"

import cv2  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.app.config import AppConfig, get_config  # noqa: E402
from backend.app.database import Base, SessionLocal, engine  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.services.media import write_wav_mono16  # noqa: E402
from backend.app.services.vision import BaseDetector, Detection  # noqa: E402


def _reset_config() -> None:
    cfg = get_config()
    fresh = AppConfig()
    for key in (
        "min_presence_sec",
        "sample_interval_sec",
        "window_sec",
        "late_after_sec",
        "detector_backend",
        "ollama_enabled",
        "ollama_url",
        "ollama_model",
        "max_upload_mb",
        "max_analysis_frames",
        "analysis_max_width",
    ):
        setattr(cfg, key, getattr(fresh, key))


def _clean_database() -> None:
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    sessions_dir = DATA_DIR / "sessions"
    if sessions_dir.exists():
        shutil.rmtree(sessions_dir, ignore_errors=True)
    _reset_config()


@pytest.fixture(scope="session")
def client():
    Base.metadata.create_all(engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_state(client):
    _clean_database()
    yield
    _clean_database()


# --------------------------------------------------------------------------
# Synthetic media helpers (no external assets required)
# --------------------------------------------------------------------------
def make_test_video(path: Path, seconds: int = 8, fps: int = 10, size=(320, 240)) -> Path:
    width, height = size
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), float(fps), (width, height)
    )
    if not writer.isOpened():
        pytest.skip("mp4v codec unavailable in this OpenCV build")
    total = seconds * fps
    for i in range(total):
        frame = np.full((height, width, 3), 60, dtype=np.uint8)
        x = 20 + int((i * 4) % max(1, width - 100))
        cv2.rectangle(frame, (x, 70), (x + 50, 200), (210, 210, 210), -1)
        cv2.circle(frame, (x + 25, 60), 16, (230, 220, 200), -1)
        writer.write(frame)
    writer.release()
    assert path.exists() and path.stat().st_size > 0
    return path


def make_test_audio(path: Path, seconds: int = 8, rate: int = 16000) -> Path:
    total = seconds * rate
    t = np.arange(total) / rate
    envelope = (np.sin(2 * np.pi * 0.5 * t) > 0).astype(np.float32)
    samples = 0.12 * np.sin(2 * np.pi * 440 * t).astype(np.float32) * envelope
    write_wav_mono16(path, samples, rate)
    return path


class FakePersonDetector(BaseDetector):
    name = "fake-test"
    available = True
    detail = "Deterministic two-person detector used only in tests."

    def detect(self, frame):
        height, width = frame.shape[:2]
        return [
            Detection((width * 0.15, height * 0.20, width * 0.32, height * 0.92), 0.91),
            Detection((width * 0.55, height * 0.24, width * 0.72, height * 0.95), 0.86),
        ]


@pytest.fixture
def fake_detector(monkeypatch):
    detector = FakePersonDetector()
    monkeypatch.setattr(
        "backend.app.services.pipeline.vision.build_detector",
        lambda backend=None: detector,
    )
    return detector


@pytest.fixture
def media_files(tmp_path):
    video = make_test_video(tmp_path / "lesson.mp4", seconds=8)
    audio = make_test_audio(tmp_path / "lesson.wav", seconds=8)
    return video, audio


@pytest.fixture
def created_session(client):
    response = client.post(
        "/api/sessions",
        json={
            "title": "Test lesson",
            "subject": "Mathematics",
            "session_date": "2026-03-01",
            "class_label": "MATH-101",
            "min_presence_sec": 2,
            "late_after_sec": 100,
            "window_sec": 30,
            "sample_interval_sec": 1,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
