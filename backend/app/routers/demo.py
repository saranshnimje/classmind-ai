"""Explicitly labelled simulated demo data."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..models import Session
from ..schemas import SessionOut
from ..serializers import session_out
from ..services.demo import seed_demo_session
from ..services.events import log_event
from ..services.storage import remove_session_files

router = APIRouter(tags=["demo"])


@router.post("/demo/seed", response_model=SessionOut, status_code=201)
def seed_demo(db: DbSession = Depends(get_db)) -> SessionOut:
    session = seed_demo_session(db)
    return session_out(session)


@router.delete("/demo", status_code=200)
def clear_demo(db: DbSession = Depends(get_db)) -> dict:
    sessions = db.scalars(select(Session).where(Session.is_demo.is_(True))).all()
    count = 0
    for session in sessions:
        remove_session_files(session.id)
        db.delete(session)
        count += 1
    db.commit()
    log_event(db, "info", "demo_cleared", f"Removed {count} demo session(s).")
    return {"removed_sessions": count, "message": "All demo sessions were removed."}
