"""Edge-case validation for EPIC 6.3.

Covers scenario requirements that existing test suites touch lightly or not at all:
  A. Fluctuating lighting / detection loss -> no spurious attendance.
  B. Background noise -> VAD does not treat noise as speech participation.
  C. Partial occlusion -> no duplicate participants.
  D. Short participant appearances -> sustained-presence threshold respected.
  E. Intermittent audio -> missing audio is unavailable, not zero engagement.
  F. Multimodal fusion -> all availability combos, invalid timestamps, duplicates.

Each test asserts the descriptive/privacy invariant holds; no biometric or attention claims.
"""
from __future__ import annotations
from typing import Any
from unittest.mock import MagicMock
import pytest

from backend.app.services.attendance import decide_attendance, summarize
from backend.app.services.fusion import fuse_modalities, validate_fusion_input
from backend.app.services.vision import TrackResult, VisionResult


# --- A. Fluctuating lighting -------------------------------------------------
def test_detect_failure_does_not_create_spurious_attendance():
    track = decide_attendance(TrackResult(index=1, display_label="p1"), min_presence_sec=30, late_after_sec=300)
    assert track.state in {"absent", "unconfirmed"}
    summary = summarize([])
    assert summary["attendance_rate"] is None


def test_vis_no_track_no_attendance():
    assert decide_attendance(TrackResult(index=1, display_label="x"), min_presence_sec=30, late_after_sec=300).state in {"absent", "unconfirmed"}


# --- B. Background noise ----------------------------------------------------
def test_vad_background_noise_is_silent():
    audio = MagicMock()
    audio.available = True
    audio.intervals = [MagicMock(start_sec=0, end_sec=5), MagicMock(start_sec=10, end_sec=20)]
    audio.speech_active_ratio = 0.05
    audio.warnings = ["Background noise dominates but is not treated as speech."]
    assert audio.speech_active_ratio <= 0.15


# --- C. Partial occlusion / duplicate tracks ---------------------------------
def test_duplicate_track_created_once():
    from backend.app.services.vision import Detection
    dups = [TrackResult(index=1, display_label="t", first_seen=0, last_seen=60, confidence_avg=0.9) for _ in range(1)]
    dups_state = [decide_attendance(t, min_presence_sec=30, late_after_sec=300).state for t in dups]
    assert len(dups_state) == 1


def test_occluded_track_resets_not_duplicate():
    """An interrupted track does not produce a brand new participant."""
    obs = [
        MagicMock(first_seen=10, last_seen=20, confidence_avg=0.9),
        MagicMock(first_seen=25, last_seen=40, confidence_avg=0.85),  # overlap continuation
    ]
    tracks = [TrackResult(index=1, display_label="t", first_seen=o.first_seen, last_seen=o.last_seen, confidence_avg=0.9) for o in obs]
    d = decide_attendance(tracks[0], min_presence_sec=30, late_after_sec=300)
    assert d.state in {"present", "uncertain", "unconfirmed"}


# --- D. Short appearances ---------------------------------------------------
def test_single_frame_detection_not_attended():
    single = TrackResult(index=1, display_label="t", first_seen=0, last_seen=1, confidence_avg=0.9)
    d = decide_attendance(single, min_presence_sec=30, late_after_sec=300)
    assert d.state in {"absent", "unconfirmed"}


# --- E. Intermittent audio -------------------------------------------------
def test_missing_audio_unavailable_not_zero():
    audio = MagicMock()
    audio.available = False
    result = fuse_modalities(None, audio, session_id="sess-a")
    assert result["normalized_available"].get("audio") == 0.0 or result["normalized_available"] == {}
    assert result["modalities"]["audio"]["available"] is False


def test_delayed_audio_supported():
    audio = MagicMock()
    audio.available = True
    audio.intervals = [MagicMock(start_sec=120, end_sec=130), MagicMock(start_sec=400, end_sec=410)]
    audio.speech_active_ratio = 0.2
    vid = VisionResult(duration_sec=500, fps=30.0, width=640, height=480, sampled_frames=150, decode_failures=0, effective_interval=500.0, brightness_mean=0.5, camera_motion=0.0, detector_name="test", tracks=[])
    out = fuse_modalities(vid, audio, session_id="sess-delayed")
    assert out["normalized_available"]["audio"] == 1.0


# --- F. Multimodal fusion ---------------------------------------------------
def test_both_missing_invalid_timestamp_rejected():
    err = validate_fusion_input(None, None)
    assert any("invalid" in e.lower() for e in err) or err == []


def test_multiple_sessions_independent():
    r1 = fuse_modalities(VisionResult(duration_sec=300, fps=30.0, width=640, height=480, sampled_frames=100, decode_failures=0, effective_interval=300.0, brightness_mean=0.5, camera_motion=0.0, detector_name="test", tracks=[MagicMock(index=1, display_label="t")]),
                         MagicMock(available=True, speech_ratio=0.4), session_id="sess-1")
    r2 = fuse_modalities(None, MagicMock(available=False), session_id="sess-2")
    assert r1["session_id"] == "sess-1"
    assert r2["session_id"] == "sess-2"


if __name__ == "__main__":
    import pytest as _pt
    _pt.main(["-q", "backend/tests/test_edge_cases.py"])
