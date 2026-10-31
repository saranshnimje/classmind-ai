"""Optional live camera capture (video-only).

Live support depends on a working local camera and OpenCV backend. It records
to a local file and then runs the same offline pipeline. Audio is not captured
live (microphone capture is not implemented); this is documented as a limitation.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import datetime, timezone

import cv2

from ..database import SessionLocal
from ..models import Session
from .events import log_event
from .pipeline import pipeline
from .storage import session_dir

logger = logging.getLogger(__name__)


class LiveError(Exception):
    pass


class LiveManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._captures: dict[str, dict] = {}

    def start(
        self,
        session_id: str,
        camera_index: int = 0,
        max_seconds: float = 300.0,
        auto_process: bool = True,
    ) -> dict:
        with self._lock:
            if session_id in self._captures and self._captures[session_id]["thread"].is_alive():
                raise LiveError("A live capture is already running for this session")

        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            cap.release()
            raise LiveError(
                f"Camera index {camera_index} could not be opened. "
                "Check that a webcam is connected and not used by another application."
            )
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
        fps = 20.0
        filename = f"live-{uuid.uuid4().hex[:10]}.mp4"
        target = session_dir(session_id) / filename
        writer = cv2.VideoWriter(
            str(target), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
        )
        if not writer.isOpened():
            cap.release()
            target.unlink(missing_ok=True)
            raise LiveError("Could not create a local video writer (codec unavailable).")

        state = {
            "stop": threading.Event(),
            "frames": 0,
            "started_at": datetime.now(timezone.utc),
            "max_seconds": max_seconds,
            "error": None,
            "filename": filename,
            "width": width,
            "height": height,
            "fps": fps,
            "auto_process": auto_process,
        }

        def worker() -> None:
            frames = 0
            error: str | None = None
            started = time.monotonic()
            try:
                while not state["stop"].is_set() and time.monotonic() - started < max_seconds:
                    ok, frame = cap.read()
                    if not ok:
                        error = "The camera stopped returning frames."
                        break
                    writer.write(frame)
                    frames += 1
                    state["frames"] = frames
            except Exception as exc:  # pragma: no cover - hardware dependent
                error = f"Live capture failed: {exc}"
            finally:
                writer.release()
                cap.release()
                duration = round(frames / fps, 3)
                db = SessionLocal()
                try:
                    session = db.get(Session, session_id)
                    if session is not None:
                        if frames == 0:
                            session.status = "failed"
                            session.error_message = error or "No frames were captured."
                        else:
                            session.video_filename = filename
                            session.video_size_bytes = target.stat().st_size if target.exists() else None
                            session.duration_sec = duration
                            session.fps = fps
                            session.width = width
                            session.height = height
                            session.has_audio = False
                            session.status = "uploaded"
                            session.error_message = None
                        db.commit()
                        log_event(
                            db,
                            "info" if frames else "error",
                            "live_capture_finished",
                            f"Live capture finished: {frames} frames, {duration}s"
                            + (f" ({error})" if error else ""),
                            session_id,
                        )
                    state["error"] = error
                    if frames and auto_process:
                        try:
                            pipeline.submit(session_id)
                        except Exception as exc:  # pragma: no cover
                            logger.warning("Could not auto-process live capture: %s", exc)
                finally:
                    db.close()

        thread = threading.Thread(target=worker, name=f"live-{session_id[:6]}", daemon=True)
        state["thread"] = thread
        with self._lock:
            self._captures[session_id] = state
        thread.start()
        return self.status(session_id)

    def stop(self, session_id: str) -> dict:
        with self._lock:
            state = self._captures.get(session_id)
        if state is None:
            raise LiveError("No live capture is running for this session")
        state["stop"].set()
        return self.status(session_id)

    def status(self, session_id: str) -> dict:
        with self._lock:
            state = self._captures.get(session_id)
        if state is None:
            return {
                "session_id": session_id,
                "active": False,
                "frames": 0,
                "seconds": 0.0,
                "error": None,
                "message": "No live capture has been started for this session.",
            }
        thread = state["thread"]
        elapsed = (datetime.now(timezone.utc) - state["started_at"]).total_seconds()
        return {
            "session_id": session_id,
            "active": thread.is_alive(),
            "frames": state["frames"],
            "seconds": round(min(elapsed, state["max_seconds"]), 1),
            "max_seconds": state["max_seconds"],
            "error": state["error"],
            "video_filename": state["filename"],
            "message": (
                "Recording from the local camera."
                if thread.is_alive()
                else "Capture finished; analysis may be queued."
            ),
        }

    def stop_all(self) -> None:
        with self._lock:
            states = list(self._captures.values())
        for state in states:
            state["stop"].set()


live_manager = LiveManager()
