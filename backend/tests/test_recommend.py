"""Rule-based recommendation generation and LLM fallback behaviour."""

from __future__ import annotations

from backend.app.services.analytics import WindowMetrics
from backend.app.services.audio import AudioAnalysis, SpeechInterval
from backend.app.services.recommend import (
    AnalyticsContext,
    build_recommendations,
    rule_recommendations,
)


def window(index, score, start=None, audio=0.3, movement=0.4, participants=5):
    start = index * 300.0 if start is None else start
    return WindowMetrics(
        window_index=index,
        start_sec=start,
        end_sec=start + 300.0,
        participant_count=participants,
        movement_index=movement,
        active_ratio=movement + 0.1,
        inactivity_ratio=1 - movement - 0.1,
        audio_active_ratio=audio,
        engagement_score=score,
        engagement_confidence="medium",
        data_quality="good",
        warnings=[],
    )


def audio(intervals=None, available=True):
    return AudioAnalysis(
        available=available,
        method="energy",
        duration_sec=1800.0,
        speech_sec=sum(i.duration for i in (intervals or [])),
        speech_ratio=0.2,
        intervals=intervals or [],
    )


def context(windows, audio_result=None, notes=None, attendance=None, quality=None):
    return AnalyticsContext(
        duration_sec=1800.0,
        windows=windows,
        audio=audio_result or audio(),
        quality=quality
        or {"score": "good", "warnings": []},
        movement_summary={
            "tracked_participants": 5,
            "longest_inactive_sec": 30,
            "mean_movement_index": 0.3,
        },
        attendance=attendance
        or {
            "total_detected": 5,
            "present": 5,
            "late": 0,
            "unconfirmed": 0,
            "mapped": 0,
            "anonymous": 5,
            "attendance_rate": 100.0,
        },
        notes=notes,
        session_title="Algorithms",
        subject="CS",
    )


def test_declining_windows_trigger_interactive_suggestion():
    windows = [window(0, 0.72), window(1, 0.55), window(2, 0.38)]
    recs = rule_recommendations(context(windows))
    titles = [r.title.lower() for r in recs]
    assert any("interactive" in title for title in titles)
    rec = next(r for r in recs if "interactive" in r.title.lower())
    assert "0.72" in rec.evidence and "0.38" in rec.evidence
    assert rec.start_sec == 0.0
    assert rec.end_sec == 900.0
    assert rec.source == "rule"


def test_long_silence_recommendation_has_interval():
    intervals = [SpeechInterval(0.0, 20.0, 0.05)]
    recs = rule_recommendations(context([window(0, 0.5)], audio_result=audio(intervals)))
    rec = next((r for r in recs if "silent" in r.title.lower()), None)
    assert rec is not None
    assert rec.start_sec == 20.0
    assert rec.end_sec == 1800.0
    assert "silence" in rec.evidence.lower()


def test_teacher_notes_are_used_as_evidence():
    recs = rule_recommendations(
        context([window(0, 0.5)], notes="Students found recursion difficult today.")
    )
    rec = next((r for r in recs if "revisit" in r.title.lower()), None)
    assert rec is not None
    assert rec.priority == "high"
    assert "recursion difficult" in rec.evidence


def test_unconfirmed_attendance_is_not_treated_as_absence():
    attendance = {
        "total_detected": 4,
        "present": 1,
        "late": 0,
        "unconfirmed": 3,
        "mapped": 0,
        "anonymous": 4,
        "attendance_rate": 25.0,
    }
    recs = rule_recommendations(context([window(0, 0.5)], attendance=attendance))
    rec = next(r for r in recs if "unconfirmed" in r.title.lower())
    assert "not that the student was absent" in rec.interpretation.lower()


def test_low_quality_recommendation_quotes_warnings():
    quality = {"score": "partial", "warnings": ["Low average frame brightness."]}
    recs = rule_recommendations(context([window(0, 0.5)], quality=quality))
    rec = next(r for r in recs if "capture" in r.title.lower())
    assert "Low average frame brightness" in rec.evidence


def test_build_recommendations_without_llm_marks_rules_only(monkeypatch):
    from backend.app.config import get_config

    monkeypatch.setattr(get_config(), "ollama_enabled", False)
    recs, meta = build_recommendations(context([window(0, 0.7), window(1, 0.5), window(2, 0.3)]))
    assert recs
    assert all(item["source"] == "rule" for item in recs)
    assert meta["generated_by"] == "rules"
    assert meta["llm_available"] is False
    assert "not" in meta["disclaimer"].lower()


def test_no_data_produces_no_fabricated_engagement_claim():
    ctx = context([], quality={"score": "poor", "warnings": ["No people were detected."]})
    recs = rule_recommendations(ctx)
    # A capture-quality suggestion is legitimate; no suggestion may claim measured low engagement.
    for rec in recs:
        assert "disengaged" not in rec.detail.lower()
        assert "lazy" not in rec.detail.lower()
