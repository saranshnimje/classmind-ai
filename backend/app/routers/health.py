"""Health and model availability endpoints."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from ..config import get_config
from ..database import get_db
from ..schemas import HealthOut
from ..services.audio import vad_status
from ..services.media import ffmpeg_version
from ..services.pipeline import pipeline
from ..services.recommend import ollama_status
from ..services.storage import data_root
from ..services.vision import detector_status

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthOut)
def health(db: DbSession = Depends(get_db)) -> HealthOut:
    cfg = get_config()
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover
        db_status = f"error: {type(exc).__name__}"

    writable = False
    try:
        with tempfile.NamedTemporaryFile(dir=data_root(), delete=True):
            writable = True
    except Exception:  # pragma: no cover
        writable = False

    ffmpeg = ffmpeg_version()
    return HealthOut(
        status="ok" if db_status == "ok" and writable else "degraded",
        app=cfg.app_name,
        version=cfg.app_version,
        database=db_status,
        data_dir_writable=writable,
        processing_active=pipeline.is_busy(),
        detector=detector_status(),
        audio_vad=vad_status(cfg.vad_backend),
        llm=ollama_status(timeout=0.8),
        ffmpeg={"available": bool(ffmpeg), "version": ffmpeg},
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/models")
def models() -> dict:
    cfg = get_config()
    return {
        "detector": detector_status(),
        "audio_vad": vad_status(cfg.vad_backend),
        "llm": ollama_status(timeout=1.0),
        "notes": {
            "offline": (
                "All core processing runs locally. Model weights must be downloaded once "
                "(internet required) before offline use."
            ),
            "privacy": "No recordings or student data are sent to external services.",
        },
    }
