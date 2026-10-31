"""Persistent application preferences and model availability reporting."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ..config import get_config
from ..models import AppSetting, Session
from ..schemas import SettingsOut, SettingsUpdate
from .audio import vad_status
from .recommend import ollama_status
from .storage import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS, data_root, remove_session_files
from .vision import detector_status

PREF_KEY = "preferences"


def default_preferences() -> dict:
    cfg = get_config()
    return {
        "min_presence_sec": cfg.min_presence_sec,
        "sample_interval_sec": cfg.sample_interval_sec,
        "window_sec": cfg.window_sec,
        "late_after_sec": cfg.late_after_sec,
        "detector_backend": cfg.detector_backend,
        "ollama_enabled": cfg.ollama_enabled,
        "ollama_url": cfg.ollama_url,
        "ollama_model": cfg.ollama_model,
        "retention_days": 0,
        "delete_media_after_processing": False,
    }


def get_preferences(db: DbSession) -> dict:
    prefs = default_preferences()
    row = db.get(AppSetting, PREF_KEY)
    if row and isinstance(row.value_json, dict):
        for key, value in row.value_json.items():
            if key in prefs and value is not None:
                prefs[key] = value
    return prefs


def save_preferences(db: DbSession, payload: SettingsUpdate) -> dict:
    prefs = get_preferences(db)
    updates = payload.model_dump(exclude_none=True)
    prefs.update(updates)
    row = db.get(AppSetting, PREF_KEY)
    if row is None:
        row = AppSetting(key=PREF_KEY, value_json=prefs)
        db.add(row)
    else:
        row.value_json = prefs
    db.commit()
    apply_preferences_to_config(prefs)
    return prefs


def apply_preferences_to_config(prefs: dict) -> None:
    """Keep the in-process config aligned with persisted preferences."""
    cfg = get_config()
    for key in (
        "min_presence_sec",
        "sample_interval_sec",
        "window_sec",
        "late_after_sec",
        "detector_backend",
        "ollama_enabled",
        "ollama_url",
        "ollama_model",
    ):
        if key in prefs and prefs[key] is not None:
            setattr(cfg, key, prefs[key])


def load_preferences_into_config(db: DbSession) -> dict:
    prefs = get_preferences(db)
    apply_preferences_to_config(prefs)
    return prefs


def models_status(prefs: dict) -> dict:
    cfg = get_config()
    return {
        "detector": detector_status(prefs.get("detector_backend")),
        "audio_vad": vad_status(cfg.vad_backend),
        "llm": ollama_status(prefs.get("ollama_url"), prefs.get("ollama_model")),
    }


def settings_out(db: DbSession) -> SettingsOut:
    cfg = get_config()
    prefs = get_preferences(db)
    return SettingsOut(
        **prefs,
        data_dir=str(data_root()),
        database_path=cfg.resolved_database_path,
        models=models_status(prefs),
        limits={
            "max_upload_mb": cfg.max_upload_mb,
            "max_media_duration_sec": cfg.max_media_duration_sec,
            "video_extensions": sorted(VIDEO_EXTENSIONS),
            "audio_extensions": sorted(AUDIO_EXTENSIONS),
            "max_analysis_frames": cfg.max_analysis_frames,
            "analysis_max_width": cfg.analysis_max_width,
        },
    )


def apply_retention(db: DbSession) -> int:
    """Delete sessions older than the configured retention window."""
    prefs = get_preferences(db)
    days = int(prefs.get("retention_days") or 0)
    if days <= 0:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    sessions = db.scalars(select(Session).where(Session.created_at < cutoff)).all()
    removed = 0
    for session in sessions:
        remove_session_files(session.id)
        db.delete(session)
        removed += 1
    if removed:
        db.commit()
    return removed
