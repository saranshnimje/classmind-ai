"""Attendance, manual roster mapping and CSV export."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..errors import ApiError
from ..models import AttendanceRecord, ParticipantTrack, RosterEntry, Session
from ..schemas import (
    AttendanceOut,
    AttendanceSummary,
    RosterCreate,
    RosterOut,
    TrackMappingIn,
)
from ..serializers import attendance_summary
from ..services.events import log_event
from ..services.report import attendance_csv
from ..routers.sessions import get_session_or_404

router = APIRouter(tags=["attendance"])


@router.get("/sessions/{session_id}/attendance", response_model=AttendanceSummary)
def get_attendance(session_id: str, db: DbSession = Depends(get_db)) -> AttendanceSummary:
    session = get_session_or_404(db, session_id)
    return attendance_summary(session)


def _filename(title: str, suffix: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower()[:60] or "session"
    return f"classmind-{slug}-{suffix}"


@router.get("/sessions/{session_id}/attendance.csv")
def download_attendance_csv(session_id: str, db: DbSession = Depends(get_db)) -> Response:
    session = get_session_or_404(db, session_id)
    if not session.attendance:
        raise ApiError(409, "no_attendance", "No attendance records exist for this session yet")
    content = attendance_csv(session)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{_filename(session.title, "attendance.csv")}"'
        },
    )


@router.post(
    "/sessions/{session_id}/attendance/{track_id}/map", response_model=AttendanceOut
)
def map_track(
    session_id: str,
    track_id: str,
    payload: TrackMappingIn,
    db: DbSession = Depends(get_db),
) -> AttendanceOut:
    get_session_or_404(db, session_id)
    track = db.get(ParticipantTrack, track_id)
    if track is None or track.session_id != session_id:
        raise ApiError(404, "track_not_found", "Participant track not found for this session")
    record = db.scalars(
        select(AttendanceRecord).where(AttendanceRecord.track_id == track.id)
    ).first()
    if record is None:
        raise ApiError(404, "attendance_not_found", "Attendance record not found for this track")

    if payload.roster_id is None:
        track.roster_id = None
        track.identity_status = "anonymous"
        track.display_label = f"Participant {track.track_index}"
        record.roster_id = None
        record.display_name = track.display_label
        record.note = (record.note or "") + " Manual mapping removed."
        db.commit()
        log_event(db, "info", "attendance_unmapped", "Manual mapping removed", session_id)
        return AttendanceOut.model_validate(record)

    if not payload.confirm_manual:
        raise ApiError(
            400,
            "confirmation_required",
            "Manual mapping requires confirm_manual=true. Tracks are anonymous by default.",
        )
    roster = db.get(RosterEntry, payload.roster_id)
    if roster is None:
        raise ApiError(404, "roster_not_found", "Roster entry not found")

    track.roster_id = roster.id
    track.identity_status = "mapped"
    track.display_label = roster.name
    record.roster_id = roster.id
    record.display_name = roster.name
    record.note = (
        "Manually mapped by the teacher to an authorised roster entry. "
        "This mapping is approximate and not biometric identification."
    )
    db.commit()
    log_event(
        db,
        "info",
        "attendance_mapped",
        f"Track {track.track_index} manually mapped to a roster entry.",
        session_id,
    )
    return AttendanceOut.model_validate(record)


# --------------------------------------------------------------------------
# Roster (teacher-managed, no biometric data)
# --------------------------------------------------------------------------
@router.get("/roster", response_model=list[RosterOut])
def list_roster(
    db: DbSession = Depends(get_db), class_label: str | None = Query(default=None)
) -> list[RosterOut]:
    stmt = select(RosterEntry).order_by(RosterEntry.name)
    if class_label:
        stmt = stmt.where(RosterEntry.class_label == class_label)
    return [RosterOut.model_validate(entry) for entry in db.scalars(stmt).all()]


@router.post("/roster", response_model=RosterOut, status_code=201)
def create_roster_entry(payload: RosterCreate, db: DbSession = Depends(get_db)) -> RosterOut:
    existing = db.scalars(
        select(RosterEntry).where(
            RosterEntry.name == payload.name.strip(),
            RosterEntry.class_label == payload.class_label,
        )
    ).first()
    if existing:
        raise ApiError(409, "roster_exists", "A roster entry with this name already exists")
    entry = RosterEntry(
        name=payload.name.strip(),
        external_id=payload.external_id,
        class_label=payload.class_label,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return RosterOut.model_validate(entry)


@router.delete("/roster/{roster_id}", status_code=204)
def delete_roster_entry(roster_id: str, db: DbSession = Depends(get_db)) -> Response:
    entry = db.get(RosterEntry, roster_id)
    if entry is None:
        raise ApiError(404, "roster_not_found", "Roster entry not found")
    # Remove references first so the deleted name does not linger on records.
    tracks = db.scalars(select(ParticipantTrack).where(ParticipantTrack.roster_id == roster_id)).all()
    for track in tracks:
        track.roster_id = None
        track.identity_status = "anonymous"
        track.display_label = f"Participant {track.track_index}"
        record = db.scalars(
            select(AttendanceRecord).where(AttendanceRecord.track_id == track.id)
        ).first()
        if record:
            record.roster_id = None
            record.display_name = track.display_label
    db.delete(entry)
    db.commit()
    return Response(status_code=204)
