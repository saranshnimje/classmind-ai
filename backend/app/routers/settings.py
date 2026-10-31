"""Settings, model status and retention endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..schemas import SettingsOut, SettingsUpdate
from ..services.events import log_event
from ..services.settings_service import (
    apply_retention,
    get_preferences,
    models_status,
    save_preferences,
    settings_out,
)

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=SettingsOut)
def read_settings(db: DbSession = Depends(get_db)) -> SettingsOut:
    return settings_out(db)


@router.put("/settings", response_model=SettingsOut)
def update_settings(payload: SettingsUpdate, db: DbSession = Depends(get_db)) -> SettingsOut:
    prefs = save_preferences(db, payload)
    removed = apply_retention(db)
    log_event(
        db,
        "info",
        "settings_updated",
        "Analysis preferences updated."
        + (f" Retention removed {removed} old session(s)." if removed else ""),
    )
    return settings_out(db)


@router.get("/settings/models")
def read_models(db: DbSession = Depends(get_db)) -> dict:
    return models_status(get_preferences(db))


@router.post("/settings/retention/apply")
def run_retention(db: DbSession = Depends(get_db)) -> dict:
    removed = apply_retention(db)
    return {"removed_sessions": removed}
