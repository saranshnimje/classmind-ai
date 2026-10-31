"""Dashboard aggregate endpoint (all values from real database records)."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from ..config import get_config
from ..database import get_db
from ..models import AttendanceRecord, ProcessingJob, Session, SystemEvent
from ..schemas import DashboardOut, EventOut
from ..serializers import dashboard_session
from ..services.attendance import summarize
from ..services.pipeline import pipeline
from ..services.settings_service import models_status, get_preferences

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: DbSession = Depends(get_db)) -> DashboardOut:
    sessions = db.scalars(select(Session).order_by(Session.created_at.desc())).all()
    total_sessions = len(sessions)
    completed = [s for s in sessions if s.status == "completed"]
    total_records = db.scalar(select(func.count(AttendanceRecord.id))) or 0

    rates = []
    for session in completed:
        summary = summarize(
            [
                {"state": r.state, "roster_id": r.roster_id, "uncertain": r.uncertain}
                for r in session.attendance
            ]
        )
        if summary["attendance_rate"] is not None:
            rates.append(summary["attendance_rate"])
    average_rate = round(sum(rates) / len(rates), 2) if rates else None

    engagement_values = [
        (s.quality_json or {}).get("average_engagement")
        for s in completed
        if (s.quality_json or {}).get("average_engagement") is not None
    ]
    average_engagement = (
        round(sum(engagement_values) / len(engagement_values), 4) if engagement_values else None
    )

    today = date.today()
    counts = Counter(s.session_date for s in sessions)
    sessions_last_14_days = [
        {
            "date": (today - timedelta(days=offset)).isoformat(),
            "sessions": counts.get(today - timedelta(days=offset), 0),
        }
        for offset in range(13, -1, -1)
    ]

    engagement_trend = [
        {
            "session_id": s.id,
            "title": s.title,
            "date": s.session_date.isoformat(),
            "engagement": (s.quality_json or {}).get("average_engagement"),
            "attendance_rate": summarize(
                [
                    {"state": r.state, "roster_id": r.roster_id, "uncertain": r.uncertain}
                    for r in s.attendance
                ]
            )["attendance_rate"],
            "is_demo": s.is_demo,
        }
        for s in sorted(completed, key=lambda s: s.session_date)
        if (s.quality_json or {}).get("average_engagement") is not None
    ][-12:]

    recent_events = db.scalars(
        select(SystemEvent).order_by(SystemEvent.created_at.desc()).limit(10)
    ).all()
    active_jobs = db.scalar(
        select(func.count(ProcessingJob.id)).where(
            ProcessingJob.status.in_(["queued", "processing"])
        )
    ) or 0

    cfg = get_config()
    prefs = get_preferences(db)
    return DashboardOut(
        total_sessions=total_sessions,
        completed_sessions=len(completed),
        total_attendance_records=total_records,
        average_attendance_rate=average_rate,
        average_engagement=average_engagement,
        sessions_last_14_days=sessions_last_14_days,
        engagement_trend=engagement_trend,
        recent_sessions=[dashboard_session(s) for s in sessions[:8]],
        recent_events=[EventOut.model_validate(e) for e in recent_events],
        processing={
            "active": pipeline.is_busy(),
            "queue": pipeline.status(),
            "active_jobs": active_jobs,
        },
        models=models_status(prefs),
        definitions={
            "attendance_rate": (
                "Mean of per-session (Present + Late) / detected participants, across completed "
                "sessions with attendance records. Anonymous tracks count as detected participants."
            ),
            "engagement": (
                "Mean of session-level 0-1 engagement proxies. A descriptive blend of movement, "
                "presence activity and speech activity — not a validated learning measure."
            ),
            "demo_data": "Sessions marked DEMO are simulated and excluded from no calculations, but are labelled everywhere.",
            "data_dir": str(cfg.resolved_data_dir),
        },
    )
