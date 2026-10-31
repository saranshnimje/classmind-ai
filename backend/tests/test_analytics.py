"""Time-window aggregation and missing-data behaviour."""

from __future__ import annotations

import pytest

from backend.app.services.analytics import build_analytics, build_windows, methodology
from backend.app.services.audio import AudioAnalysis, SpeechInterval
from backend.app.services.vision import Observation, TrackResult, VisionResult


def make_track(index: int, start: float, end: float, movement: float = 0.01) -> TrackResult:
    observations = []
    t = start
    first = True
    while t <= end + 1e-9:
        observations.append(
            Observation(
                t=t,
                bbox=(10.0, 10.0, 60.0, 120.0),
                confidence=0.85,
                movement_norm=0.0 if first else movement,
                inactive=(not first) and movement < 0.002,
                head="center" if first else "unknown",
                face_visible=first,
            )
        )
        first = False
        t += 2.0
    return TrackResult(
        index=index,
        display_label=f"Participant {index}",
        observations=observations,
        first_seen=start,
        last_seen=end,
        duration_sec=end - start,
        samples_seen=len(observations),
        confidence_avg=0.85,
        movement_index=0.2,
        inactive_sec=0.0,
        head_center_ratio=0.1,
        head_unknown_ratio=0.9,
        face_visible_ratio=0.1,
    )


def vision(tracks, duration=600.0) -> VisionResult:
    return VisionResult(
        duration_sec=duration,
        fps=25.0,
        width=640,
        height=360,
        sampled_frames=30,
        decode_failures=0,
        effective_interval=2.0,
        brightness_mean=110.0,
        camera_motion=1.0,
        detector_name="test",
        tracks=tracks,
        max_simultaneous=len(tracks),
        warnings=[],
    )


def audio_with(speech: bool = True) -> AudioAnalysis:
    if not speech:
        return AudioAnalysis(
            available=False,
            warnings=["Audio unavailable; audio activity is unknown for this window, not zero."],
        )
    return AudioAnalysis(
        available=True,
        method="energy",
        duration_sec=600.0,
        speech_sec=60.0,
        speech_ratio=0.1,
        intervals=[SpeechInterval(0.0, 60.0, 0.05)],
    )


def test_window_partitioning_and_short_tail_merge():
    tracks = [make_track(1, 0, 310)]
    windows = build_windows(tracks, audio_with(), 310.0, 300.0, 2.0, [])
    assert len(windows) == 1
    assert windows[0].start_sec == 0
    assert windows[0].end_sec == 310.0

    windows = build_windows([make_track(1, 0, 900)], audio_with(), 900.0, 300.0, 2.0, [])
    assert len(windows) == 3


def test_missing_audio_does_not_zero_the_score():
    tracks = [make_track(1, 0, 300, movement=0.02)]
    windows = build_windows(tracks, audio_with(False), 300.0, 300.0, 2.0, [])
    window = windows[0]
    assert window.audio_active_ratio is None
    assert window.engagement_score is not None
    expected_visual = 0.6 * window.active_ratio + 0.4 * window.movement_index
    assert window.engagement_score == pytest.approx(expected_visual, abs=1e-4)
    assert window.engagement_confidence in {"low", "medium"}
    assert any("Audio unavailable" in w for w in window.warnings)


def test_no_signals_produces_no_score():
    windows = build_windows([], audio_with(False), 300.0, 300.0, 2.0, [])
    assert windows[0].engagement_score is None
    assert windows[0].data_quality == "poor"
    assert windows[0].participant_count == 0


def test_audio_only_has_low_confidence():
    audio = AudioAnalysis(
        available=True,
        method="energy",
        duration_sec=300.0,
        speech_sec=150.0,
        speech_ratio=0.5,
        intervals=[SpeechInterval(0.0, 150.0, 0.05)],
    )
    windows = build_windows([], audio, 300.0, 300.0, 2.0, [])
    window = windows[0]
    assert window.audio_active_ratio == pytest.approx(0.5, abs=1e-3)
    assert window.engagement_score == pytest.approx(min(1.0, 0.5 / 0.6), abs=1e-4)
    assert window.engagement_confidence == "low"
    assert window.movement_index is None


def test_audio_ratio_uses_window_overlap():
    audio = AudioAnalysis(
        available=True,
        method="energy",
        duration_sec=600.0,
        speech_sec=30.0,
        speech_ratio=0.05,
        intervals=[SpeechInterval(0.0, 30.0, 0.05)],
    )
    windows = build_windows([], audio, 600.0, 300.0, 2.0, [])
    assert windows[0].audio_active_ratio == pytest.approx(0.1, abs=1e-3)
    assert windows[1].audio_active_ratio == pytest.approx(0.0, abs=1e-3)


def test_attendance_changes_count_new_arrivals():
    tracks = [make_track(1, 0, 600), make_track(2, 350, 600)]
    windows = build_windows(tracks, audio_with(), 600.0, 300.0, 2.0, [])
    assert windows[0].attendance_changes == 1
    assert windows[1].attendance_changes == 1


def test_session_analytics_without_any_tracks():
    result = build_analytics(
        vision([], duration=120.0),
        audio_with(False),
        {"total_detected": 0, "present": 0, "late": 0, "unconfirmed": 0, "attendance_rate": None},
        window_sec=300.0,
        sample_interval=2.0,
        min_presence_sec=30,
        late_after_sec=300,
    )
    assert result["average_engagement"] is None
    assert result["peak_window"] is None
    assert result["quality"]["score"] == "poor"
    assert result["methodology"]["engagement_proxy"]["window_sec"] == 300.0


def test_methodology_documents_missing_data_policy():
    doc = methodology(300.0, 2.0)
    assert "never" in doc["engagement_proxy"]["missing_data_policy"].lower()
    assert "not" in doc["engagement_proxy"]["definition"].lower()
    assert "face recognition" in doc["attendance"]["identity"].lower()
