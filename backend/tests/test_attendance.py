"""Attendance threshold and presence-duration rules."""

from __future__ import annotations

import pytest

from backend.app.services.attendance import decide_attendance, summarize
from backend.app.services.vision import TrackResult


def make_track(**kwargs) -> TrackResult:
    defaults = dict(
        index=1,
        display_label="Participant 1",
        first_seen=0.0,
        last_seen=60.0,
        duration_sec=60.0,
        samples_seen=30,
        confidence_avg=0.8,
        uncertain=False,
    )
    defaults.update(kwargs)
    return TrackResult(**defaults)


def test_below_threshold_is_unconfirmed():
    track = make_track(duration_sec=10.0, last_seen=10.0, samples_seen=5)
    decision = decide_attendance(track, min_presence_sec=30, late_after_sec=300)
    assert decision.state == "unconfirmed"
    assert "below the 30s" in decision.note
    assert decision.presence_sec == 10.0


def test_above_threshold_is_present():
    decision = decide_attendance(make_track(), min_presence_sec=30, late_after_sec=300)
    assert decision.state == "present"
    assert decision.uncertain is False


def test_late_arrival():
    track = make_track(first_seen=400.0, last_seen=500.0, duration_sec=100.0)
    decision = decide_attendance(track, min_presence_sec=30, late_after_sec=300)
    assert decision.state == "late"
    assert "arrival window" in decision.note


def test_single_observation_is_unconfirmed():
    track = make_track(samples_seen=1, duration_sec=0.0, last_seen=0.0)
    decision = decide_attendance(track, min_presence_sec=1, late_after_sec=300)
    assert decision.state == "unconfirmed"
    assert decision.uncertain is True
    assert "not evidence of absence" in decision.note


def test_low_confidence_keeps_uncertain_flag():
    track = make_track(uncertain=True)
    decision = decide_attendance(track, min_presence_sec=30, late_after_sec=300)
    assert decision.state == "present"
    assert decision.uncertain is True
    assert "uncertain" in decision.note.lower()


def test_threshold_boundary_is_inclusive():
    track = make_track(duration_sec=30.0, last_seen=30.0)
    decision = decide_attendance(track, min_presence_sec=30, late_after_sec=300)
    assert decision.state == "present"


def test_summary_counts_and_rate():
    records = [
        {"state": "present", "roster_id": "r1", "uncertain": False},
        {"state": "late", "roster_id": None, "uncertain": False},
        {"state": "unconfirmed", "roster_id": None, "uncertain": True},
    ]
    summary = summarize(records)
    assert summary["total_detected"] == 3
    assert summary["present"] == 1
    assert summary["late"] == 1
    assert summary["unconfirmed"] == 1
    assert summary["attendance_rate"] == pytest.approx(66.67, abs=0.01)
    assert summary["mapped"] == 1
    assert summary["anonymous"] == 2


def test_summary_empty_dataset():
    summary = summarize([])
    assert summary["total_detected"] == 0
    assert summary["attendance_rate"] is None
