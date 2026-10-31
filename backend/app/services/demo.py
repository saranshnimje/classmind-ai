"""Scripted demo dataset.

This is *simulated* data, generated locally without any model inference, and is
always labelled as demo data. It exists so the dashboard and reports can be
demonstrated without a classroom recording. Real sessions never contain it.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session as DbSession

from ..models import (
    AnalysisWindow,
    AttendanceRecord,
    AudioInterval,
    ParticipantTrack,
    Recommendation,
    Session,
)
from .analytics import WindowMetrics, methodology
from .audio import AudioAnalysis, SpeechInterval
from .events import log_event
from .recommend import AnalyticsContext, rule_recommendations

DEMO_WARNING = "Simulated demo data — no real video/audio inference was performed."


def _score(active: float, movement: float, audio: float) -> float:
    visual = 0.6 * active + 0.4 * movement
    audio_component = min(1.0, audio / 0.6)
    return round(0.65 * visual + 0.35 * audio_component, 4)


def _speech_intervals() -> list[SpeechInterval]:
    plan = [
        (0, 105.0, 0.35),
        (300, 120.0, 0.40),
        (600, 90.0, 0.30),
        (900, 45.0, 0.15),
        (1200, 10.0, 0.03),
        (1500, 15.0, 0.05),
    ]
    intervals: list[SpeechInterval] = []
    for start, length, ratio in plan:
        # Split into 20-second bursts so the timeline looks realistic.
        cursor = start + 5
        remaining = length
        while remaining > 0.5 and cursor < start + 300:
            chunk = min(20.0, remaining)
            intervals.append(
                SpeechInterval(
                    start_sec=round(cursor, 2),
                    end_sec=round(cursor + chunk, 2),
                    mean_energy=round(0.02 + ratio * 0.1, 5),
                )
            )
            cursor += chunk + 25
            remaining -= chunk
    return intervals


def seed_demo_session(db: DbSession) -> Session:
    session = Session(
        title="[DEMO] Introduction to Recursion",
        subject="Computer Science",
        class_label="CS-201 · Demo",
        session_date=date.today(),
        notes=(
            "Simulated demonstration session. Students found the recursion topic difficult "
            "today, especially the base-case examples."
        ),
        status="completed",
        is_demo=True,
        duration_sec=1800.0,
        fps=25.0,
        width=1280,
        height=720,
        has_audio=True,
        sample_interval_sec=2.0,
        min_presence_sec=60.0,
        late_after_sec=300.0,
        window_sec=300.0,
        detector_used="simulated",
        audio_method="simulated",
        processed_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.flush()

    tracks = [
        # first, last, duration, samples, conf, movement, inactive, head ratios, state
        (0.0, 1790.0, 1790.0, 895, 0.84, 0.46, 140.0, (0.42, 0.18, 0.10, 0.30), "present"),
        (0.0, 1782.0, 1782.0, 891, 0.81, 0.39, 210.0, (0.38, 0.22, 0.12, 0.28), "present"),
        (0.0, 1795.0, 1795.0, 897, 0.79, 0.52, 95.0, (0.45, 0.15, 0.11, 0.29), "present"),
        (0.0, 1770.0, 1770.0, 885, 0.74, 0.33, 320.0, (0.30, 0.26, 0.18, 0.26), "present"),
        (420.0, 1780.0, 1360.0, 680, 0.72, 0.30, 260.0, (0.35, 0.20, 0.14, 0.31), "late"),
        (1750.0, 1770.0, 20.0, 11, 0.41, 0.20, 20.0, (0.20, 0.10, 0.10, 0.60), "unconfirmed"),
    ]
    for index, (first, last, duration, samples, conf, movement, inactive, heads, state) in enumerate(
        tracks, start=1
    ):
        note = (
            f"Sustained presence for {duration:.0f}s."
            if state == "present"
            else (
                "First tracked 420s into the session (after the 300s arrival window)."
                if state == "late"
                else "Tracked for 20s, below the 60s minimum presence threshold."
            )
        )
        db_track = ParticipantTrack(
            session_id=session.id,
            track_index=index,
            display_label=f"Participant {index}",
            identity_status="anonymous",
            first_seen_sec=first,
            last_seen_sec=last,
            duration_sec=duration,
            samples_seen=samples,
            confidence_avg=conf,
            movement_index=movement,
            inactive_sec=inactive,
            head_center_ratio=heads[0],
            head_left_ratio=heads[1],
            head_right_ratio=heads[2],
            head_unknown_ratio=heads[3],
            attendance_state=state,
            uncertain=state == "unconfirmed",
            note=note,
        )
        db.add(db_track)
        db.flush()
        db.add(
            AttendanceRecord(
                session_id=session.id,
                track_id=db_track.id,
                display_name=db_track.display_label,
                state=state,
                presence_sec=duration,
                first_seen_sec=first,
                last_seen_sec=last,
                confidence=conf,
                uncertain=state == "unconfirmed",
                note=note,
            )
        )

    window_plan = [
        (6, 1, 0.62, 0.70, 0.35, "good"),
        (5, 0, 0.55, 0.65, 0.40, "good"),
        (6, 1, 0.48, 0.60, 0.30, "good"),
        (5, 0, 0.36, 0.45, 0.15, "partial"),
        (4, 0, 0.28, 0.35, 0.03, "partial"),
        (4, 0, 0.22, 0.30, 0.05, "partial"),
    ]
    windows: list[WindowMetrics] = []
    for idx, (people, arrivals, movement, active, audio_ratio, quality) in enumerate(window_plan):
        start = idx * 300.0
        warnings = [DEMO_WARNING]
        if audio_ratio < 0.05:
            warnings.append("Very little speech activity in this window.")
        windows.append(
            WindowMetrics(
                window_index=idx,
                start_sec=start,
                end_sec=start + 300.0,
                participant_count=people,
                attendance_changes=arrivals,
                movement_index=movement,
                active_ratio=active,
                inactivity_ratio=round(1 - active, 2),
                looking_away_ratio=round(0.22 + idx * 0.01, 3),
                audio_active_ratio=audio_ratio,
                engagement_score=_score(active, movement, audio_ratio),
                engagement_confidence="medium",
                data_quality=quality,
                warnings=warnings,
                metrics={
                    "observations": people * 30,
                    "face_visible_ratio": 0.71,
                    "head_down_ratio": 0.04,
                    "speech_sec": round(audio_ratio * 300, 1),
                    "window_sec": 300.0,
                },
            )
        )
        db.add(
            AnalysisWindow(
                session_id=session.id,
                window_index=idx,
                start_sec=start,
                end_sec=start + 300.0,
                participant_count=people,
                attendance_changes=arrivals,
                movement_index=movement,
                active_ratio=active,
                inactivity_ratio=round(1 - active, 2),
                looking_away_ratio=round(0.22 + idx * 0.01, 3),
                audio_active_ratio=audio_ratio,
                engagement_score=_score(active, movement, audio_ratio),
                engagement_confidence="medium",
                data_quality=quality,
                warnings_json=warnings,
                metrics_json={
                    "observations": people * 30,
                    "face_visible_ratio": 0.71,
                    "head_down_ratio": 0.04,
                    "speech_sec": round(audio_ratio * 300, 1),
                    "window_sec": 300.0,
                },
            )
        )

    intervals = _speech_intervals()
    for interval in intervals:
        db.add(
            AudioInterval(
                session_id=session.id,
                start_sec=interval.start_sec,
                end_sec=interval.end_sec,
                kind="speech",
                mean_energy=interval.mean_energy,
            )
        )
    for start, end in [(0.0, 5.0), (110.0, 300.0), (420.0, 600.0), (690.0, 900.0), (945.0, 1200.0), (1210.0, 1500.0)]:
        db.add(
            AudioInterval(
                session_id=session.id, start_sec=start, end_sec=end, kind="silence", mean_energy=0.0
            )
        )

    speech_sec = sum(i.duration for i in intervals)
    audio = AudioAnalysis(
        available=True,
        method="simulated",
        duration_sec=1800.0,
        speech_sec=round(speech_sec, 2),
        speech_ratio=round(speech_sec / 1800.0, 4),
        intervals=intervals,
        warnings=[DEMO_WARNING],
    )

    attendance_summary = {
        "total_detected": 6,
        "present": 4,
        "late": 1,
        "unconfirmed": 1,
        "mapped": 0,
        "anonymous": 6,
        "uncertain": 1,
        "attendance_rate": round(5 / 6 * 100, 2),
    }
    quality = {
        "score": "partial",
        "detector": "simulated",
        "sampled_frames": 900,
        "decode_failures": 0,
        "effective_sample_interval_sec": 2.0,
        "brightness_mean": 118.0,
        "camera_motion": 2.1,
        "face_visible_ratio": 0.71,
        "audio_available": True,
        "audio_method": "simulated",
        "warnings": [DEMO_WARNING],
    }
    movement_summary = {
        "tracked_participants": 6,
        "mean_movement_index": 0.37,
        "total_inactive_sec": 1045.0,
        "longest_inactive_sec": 320.0,
        "inactive_participants": 1,
        "face_visible_ratio": 0.71,
    }
    context = AnalyticsContext(
        duration_sec=1800.0,
        windows=windows,
        audio=audio,
        quality=quality,
        movement_summary=movement_summary,
        attendance=attendance_summary,
        notes=session.notes,
        session_title=session.title,
        subject=session.subject,
        window_sec=300.0,
    )
    for rec in rule_recommendations(context):
        db.add(
            Recommendation(
                session_id=session.id,
                source=rec.source,
                category=rec.category,
                title=rec.title,
                detail=rec.detail,
                evidence=rec.evidence,
                observed=rec.observed,
                interpretation=rec.interpretation,
                start_sec=rec.start_sec,
                end_sec=rec.end_sec,
                priority=rec.priority,
                confidence=rec.confidence,
            )
        )

    avg = round(
        sum(w.engagement_score * (w.end_sec - w.start_sec) for w in windows)
        / sum(w.end_sec - w.start_sec for w in windows),
        4,
    )
    quality.update(
        {
            "average_engagement": avg,
            "engagement_confidence": "medium",
            "movement_summary": movement_summary,
            "audio_warnings": [DEMO_WARNING],
            "warnings": [DEMO_WARNING],
            "demo": True,
            "simulated": True,
            "recommendation_meta": {
                "generated_by": "rules",
                "llm_available": False,
                "llm_status": "Demo data; rule engine only.",
            },
        }
    )
    session.quality_json = quality
    session.methodology_json = methodology(300.0, 2.0)
    db.commit()
    db.refresh(session)
    log_event(
        db,
        "info",
        "demo_seeded",
        "Simulated demo session created and clearly labelled as demo data.",
        session.id,
    )
    return session
