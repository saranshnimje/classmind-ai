"""ORM -> API schema serialisation helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from .models import Session
from .schemas import (
    AnalyticsOut,
    AttendanceOut,
    AttendanceSummary,
    AudioIntervalOut,
    AudioSummary,
    DashboardSession,
    ReportOut,
    SessionOut,
    TrackOut,
    WindowOut,
)
from .services.attendance import summarize

LIMITATIONS = [
    "Person detection cannot establish a student's real-world identity; tracks stay anonymous until a teacher maps them.",
    "Head orientation is estimated from frontal-face position only and is frequently 'unknown'.",
    "The engagement proxy is a descriptive blend of observable signals, not a validated measure of attention or learning.",
    "Missing audio or video is reported as unknown, never as low engagement.",
    "Attendance reflects who was visible and trackable in the recording, not who was physically present.",
    "Occlusion, low light, camera movement and small face sizes reduce reliability.",
    "No face recognition, speaker identification, emotion detection or demographic inference is performed.",
]

_QUALITY_KEYS = (
    "score",
    "detector",
    "sampled_frames",
    "decode_failures",
    "effective_sample_interval_sec",
    "brightness_mean",
    "camera_motion",
    "face_visible_ratio",
    "audio_available",
    "audio_method",
    "warnings",
)


def _quality_payload(session: Session) -> dict:
    """Return the data-quality block for API consumers.

    The pipeline stores quality fields at the top level of ``quality_json`` and
    adds engagement/recommendation metadata beside them. Older rows may instead
    contain a nested ``quality`` object, so support both shapes.
    """
    stored = session.quality_json or {}
    nested = stored.get("quality")
    if isinstance(nested, dict) and nested:
        return nested
    return {key: stored[key] for key in _QUALITY_KEYS if key in stored}



def session_out(session: Session) -> SessionOut:
    data = SessionOut.model_validate(session)
    data.attendance_count = len(session.attendance)
    data.track_count = len(session.tracks)
    data.average_engagement = (session.quality_json or {}).get("average_engagement")
    return data


def dashboard_session(session: Session) -> DashboardSession:
    summary = summarize(
        [
            {"state": r.state, "roster_id": r.roster_id, "uncertain": r.uncertain}
            for r in session.attendance
        ]
    )
    return DashboardSession(
        id=session.id,
        title=session.title,
        subject=session.subject,
        class_label=session.class_label,
        session_date=session.session_date,
        status=session.status,
        duration_sec=session.duration_sec,
        is_demo=session.is_demo,
        created_at=session.created_at,
        attendance_rate=summary["attendance_rate"],
        average_engagement=(session.quality_json or {}).get("average_engagement"),
        error_message=session.error_message,
    )


def attendance_summary(session: Session) -> AttendanceSummary:
    records = sorted(session.attendance, key=lambda r: (r.first_seen_sec, r.display_name))
    tracks = sorted(session.tracks, key=lambda t: t.track_index)
    base = summarize(
        [{"state": r.state, "roster_id": r.roster_id, "uncertain": r.uncertain} for r in records]
    )
    quality = session.quality_json or {}
    warnings: list[str] = []
    if not tracks:
        warnings.append(
            "No participant tracks were produced. This may be a detector/camera limitation; "
            "it does not prove that nobody attended."
        )
    if base["unconfirmed"]:
        warnings.append(
            "Unconfirmed records had insufficient sustained presence or low detection confidence."
        )
    if base["anonymous"]:
        warnings.append(
            "Anonymous tracks are not linked to students. Map them manually only if authorised."
        )
    warnings.extend(quality.get("warnings", [])[:5])
    return AttendanceSummary(
        session_id=session.id,
        session_duration_sec=session.duration_sec,
        min_presence_sec=session.min_presence_sec,
        late_after_sec=session.late_after_sec,
        total_detected=base["total_detected"],
        present=base["present"],
        late=base["late"],
        unconfirmed=base["unconfirmed"],
        mapped=base["mapped"],
        anonymous=base["anonymous"],
        uncertain=base["uncertain"],
        attendance_rate=base["attendance_rate"],
        records=[AttendanceOut.model_validate(r) for r in records],
        tracks=[TrackOut.model_validate(t) for t in tracks],
        warnings=list(dict.fromkeys(warnings)),
    )


def audio_summary(session: Session) -> AudioSummary:
    quality = session.quality_json or {}
    intervals = sorted(session.audio_intervals, key=lambda i: i.start_sec)
    speech = [i for i in intervals if i.kind == "speech"]
    speech_sec = sum(max(0.0, i.end_sec - i.start_sec) for i in speech)
    duration = session.duration_sec or 0.0
    available = bool(quality.get("audio_available", session.has_audio))
    warnings = list(quality.get("audio_warnings", []))
    if not available:
        warnings.append("No usable audio track; audio activity is unknown, not zero.")
    return AudioSummary(
        available=available,
        method=session.audio_method,
        speech_active_sec=round(speech_sec, 2),
        speech_ratio=round(speech_sec / duration, 4) if available and duration > 0 else None,
        interval_count=len(speech),
        intervals=[AudioIntervalOut.model_validate(i) for i in intervals],
        warnings=list(dict.fromkeys(warnings)),
    )


def analytics_out(session: Session) -> AnalyticsOut:
    windows = sorted(session.windows, key=lambda w: w.window_index)
    quality = session.quality_json or {}
    scored = [w for w in windows if w.engagement_score is not None]
    peak = max(scored, key=lambda w: w.engagement_score).window_index if scored else None
    low = min(scored, key=lambda w: w.engagement_score).window_index if scored else None
    summary = summarize(
        [{"state": r.state, "roster_id": r.roster_id, "uncertain": r.uncertain} for r in session.attendance]
    )
    return AnalyticsOut(
        session_id=session.id,
        title=session.title,
        duration_sec=session.duration_sec,
        window_sec=session.window_sec,
        average_engagement=quality.get("average_engagement"),
        engagement_confidence=quality.get("engagement_confidence"),
        peak_window=peak,
        lowest_window=low,
        windows=[WindowOut.model_validate(w) for w in windows],
        audio=audio_summary(session),
        movement_summary=quality.get("movement_summary", {}),
        attendance_summary=summary,
        quality=_quality_payload(session),
        methodology=session.methodology_json or {},
        warnings=list(dict.fromkeys(quality.get("warnings", []))),
    )


def report_out(session: Session) -> ReportOut:
    from .schemas import RecommendationOut

    return ReportOut(
        session=session_out(session),
        generated_at=datetime.now(timezone.utc),
        attendance=attendance_summary(session),
        analytics=analytics_out(session),
        recommendations=[
            RecommendationOut.model_validate(r)
            for r in sorted(session.recommendations, key=lambda r: r.created_at)
        ],
        quality=_quality_payload(session),
        methodology=session.methodology_json or {},
        limitations=LIMITATIONS,
    )
