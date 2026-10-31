"""System event log helper (never stores raw media or secrets)."""

from __future__ import annotations

from sqlalchemy.orm import Session as DbSession

from ..models import SystemEvent


def log_event(
    db: DbSession,
    level: str,
    event: str,
    message: str,
    session_id: str | None = None,
) -> None:
    db.add(
        SystemEvent(
            level=level,
            event=event,
            message=message[:2000],
            session_id=session_id,
        )
    )
    db.commit()
