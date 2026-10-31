"""Time-window multimodal aggregation and the transparent engagement proxy.

The engagement proxy is a descriptive summary of *observable* signals, not a
validated measure of attention, comprehension or learning. Missing signals are
excluded from the blend rather than treated as zeros.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .audio import AudioAnalysis, speech_overlap
from .vision import TrackResult, VisionResult
from .fusion import fuse_modalities

MOVEMENT_ACTIVE_THRESHOLD = 0.002  # normalised displacement per sample
MOVEMENT_SCALE = 20.0  # 5% of frame width per sample => movement index 1.0
AUDIO_FULL_ACTIVITY = 0.6  # 60% speech-active time saturates the audio component


@dataclass
class WindowMetrics:
    window_index: int
    start_sec: float
    end_sec: float
    participant_count: int = 0
    attendance_changes: int = 0
    movement_index: float | None = None
    active_ratio: float | None = None
    inactivity_ratio: float | None = None
    looking_away_ratio: float | None = None
    audio_active_ratio: float | None = None
    engagement_score: float | None = None
    engagement_confidence: str | None = None
    data_quality: str = "partial"
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


def _window_bounds(duration: float, window_sec: float) -> list[tuple[float, float]]:
    if duration <= 0:
        return [(0.0, float(window_sec))]
    count = max(1, math.ceil(duration / window_sec - 1e-9))
    bounds = [(i * window_sec, min(duration, (i + 1) * window_sec)) for i in range(count)]
    # Merge a very short trailing window into the previous one.
    if len(bounds) > 1 and (bounds[-1][1] - bounds[-1][0]) < 0.25 * window_sec:
        prev_start = bounds[-2][0]
        bounds = bounds[:-2] + [(prev_start, duration)]
    return [(round(a, 3), round(b, 3)) for a, b in bounds if b > a]


def _window_metrics(
    index: int,
    start: float,
    end: float,
    tracks: list[TrackResult],
    audio: AudioAnalysis,
    interval: float,
    global_warnings: list[str],
    is_last: bool,
) -> WindowMetrics:
    length = max(1e-6, end - start)

    def in_window(t: float) -> bool:
        if start <= t < end:
            return True
        return is_last and abs(t - end) < 1e-6

    participants = 0
    arrivals = 0
    movements: list[float] = []
    inactive_flags: list[bool] = []
    face_total = 0
    face_visible = 0
    away = 0
    down = 0
    observation_count = 0
    head_total = 0

    for track in tracks:
        observations = [o for o in track.observations if in_window(o.t)]
        if not observations:
            continue
        participants += 1
        if start <= track.first_seen < end:
            arrivals += 1
        observation_count += len(observations)
        first_obs = track.observations[0] if track.observations else None
        for obs in observations:
            if first_obs is not None and obs is first_obs:
                continue
            movements.append(obs.movement_norm)
            inactive_flags.append(obs.inactive)
            if obs.face_visible:
                face_visible += 1
                head_total += 1
                if obs.head in {"left", "right"}:
                    away += 1
                if obs.head == "down":
                    down += 1
        face_total += len(observations)

    warnings = list(global_warnings)
    metrics: dict[str, Any] = {
        "observations": observation_count,
        "face_visible_ratio": round(face_visible / face_total, 4) if face_total else None,
        "head_down_ratio": round(down / head_total, 4) if head_total else None,
        "speech_sec": 0.0,
        "window_sec": round(length, 3),
    }

    movement_index = None
    active_ratio = None
    inactivity_ratio = None
    if len(movements) >= 2:
        mean_move = float(np.mean(movements))
        movement_index = round(float(np.clip(mean_move * MOVEMENT_SCALE, 0.0, 1.0)), 4)
        active_ratio = round(float(np.mean([m >= MOVEMENT_ACTIVE_THRESHOLD for m in movements])), 4)
        inactivity_ratio = round(1.0 - active_ratio, 4)
    elif participants > 0:
        warnings.append("Too few movement observations in this window for visual indicators.")

    looking_away_ratio = round(away / head_total, 4) if head_total else None

    audio_ratio = None
    if audio.available and audio.duration_sec > 0:
        overlap = speech_overlap(audio.intervals, start, end)
        audio_ratio = round(min(1.0, overlap / length), 4)
        metrics["speech_sec"] = round(overlap, 2)

    if not audio.available:
        warnings.append("Audio unavailable; audio activity is unknown for this window, not zero.")
    if participants == 0:
        warnings.append("No tracked participants in this window.")

    visual_component = None
    if movement_index is not None and active_ratio is not None:
        visual_component = 0.6 * active_ratio + 0.4 * movement_index

    audio_component = None
    if audio_ratio is not None:
        audio_component = min(1.0, audio_ratio / AUDIO_FULL_ACTIVITY)

    score = None
    confidence = None
    if visual_component is not None and audio_component is not None:
        score = 0.65 * visual_component + 0.35 * audio_component
        if len(movements) >= 10 and participants >= 2:
            confidence = "high"
        elif len(movements) >= 4:
            confidence = "medium"
        else:
            confidence = "low"
    elif visual_component is not None:
        score = visual_component
        confidence = "medium" if len(movements) >= 6 and participants >= 2 else "low"
    elif audio_component is not None:
        score = audio_component
        confidence = "low"

    if score is not None:
        score = round(float(np.clip(score, 0.0, 1.0)), 4)

    if score is None:
        quality = "poor"
    elif warnings or confidence == "low":
        quality = "partial"
    else:
        quality = "good"

    return WindowMetrics(
        window_index=index,
        start_sec=start,
        end_sec=end,
        participant_count=participants,
        attendance_changes=arrivals,
        movement_index=movement_index,
        active_ratio=active_ratio,
        inactivity_ratio=inactivity_ratio,
        looking_away_ratio=looking_away_ratio,
        audio_active_ratio=audio_ratio,
        engagement_score=score,
        engagement_confidence=confidence,
        data_quality=quality,
        warnings=sorted(set(warnings)),
        metrics=metrics,
    )


def build_windows(
    tracks: list[TrackResult],
    audio: AudioAnalysis,
    duration: float,
    window_sec: float,
    sample_interval: float,
    global_warnings: list[str],
) -> list[WindowMetrics]:
    bounds = _window_bounds(duration, window_sec)
    return [
        _window_metrics(
            i, start, end, tracks, audio, sample_interval, global_warnings, i == len(bounds) - 1
        )
        for i, (start, end) in enumerate(bounds)
    ]


def _weighted_average(windows: list[WindowMetrics]) -> tuple[float | None, str | None]:
    scored = [w for w in windows if w.engagement_score is not None]
    if not scored:
        return None, None
    total = sum(w.end_sec - w.start_sec for w in scored)
    if total <= 0:
        value = float(np.mean([w.engagement_score for w in scored]))
    else:
        value = sum((w.end_sec - w.start_sec) * w.engagement_score for w in scored) / total
    confidences = [w.engagement_confidence for w in scored]
    if all(c == "high" for c in confidences):
        confidence = "high"
    elif any(c in {"high", "medium"} for c in confidences):
        confidence = "medium"
    else:
        confidence = "low"
    if len(scored) < len(windows):
        confidence = "low" if confidence == "medium" else confidence
    return round(value, 4), confidence


def build_movement_summary(tracks: list[TrackResult], audio: AudioAnalysis) -> dict[str, Any]:
    if not tracks:
        return {
            "tracked_participants": 0,
            "mean_movement_index": None,
            "total_inactive_sec": 0.0,
            "longest_inactive_sec": 0.0,
            "inactive_participants": 0,
            "face_visible_ratio": None,
        }
    total_obs = sum(t.samples_seen for t in tracks)
    face_obs = sum(t.face_visible_ratio * t.samples_seen for t in tracks)
    return {
        "tracked_participants": len(tracks),
        "mean_movement_index": round(float(np.mean([t.movement_index for t in tracks])), 4),
        "total_inactive_sec": round(sum(t.inactive_sec for t in tracks), 2),
        "longest_inactive_sec": round(max(t.inactive_sec for t in tracks), 2),
        "inactive_participants": sum(
            1 for t in tracks if t.inactive_sec >= 60 and t.movement_index < 0.1
        ),
        "face_visible_ratio": round(face_obs / total_obs, 4) if total_obs else None,
    }


def build_quality(
    vision: VisionResult,
    audio: AudioAnalysis,
    tracks: list[TrackResult],
) -> dict[str, Any]:
    warnings = list(vision.warnings) + list(audio.warnings)
    face_total = sum(t.samples_seen for t in tracks)
    face_visible = sum(t.face_visible_ratio * t.samples_seen for t in tracks)
    face_ratio = round(face_visible / face_total, 4) if face_total else None
    if face_total and face_ratio is not None and face_ratio < 0.2:
        warnings.append(
            "Faces were rarely visible; head-orientation indicators are mostly unknown."
        )
    if vision.sampled_frames < 4:
        warnings.append("Very few frames were sampled; indicators are coarse.")

    if vision.sampled_frames == 0 or not tracks:
        score = "poor"
    elif warnings:
        score = "partial"
    else:
        score = "good"

    return {
        "score": score,
        "detector": vision.detector_name,
        "sampled_frames": vision.sampled_frames,
        "decode_failures": vision.decode_failures,
        "effective_sample_interval_sec": vision.effective_interval,
        "brightness_mean": vision.brightness_mean,
        "camera_motion": vision.camera_motion,
        "face_visible_ratio": face_ratio,
        "audio_available": audio.available,
        "audio_method": audio.method,
        "warnings": sorted(set(warnings)),
    }


def methodology(window_sec: float, sample_interval: float) -> dict[str, Any]:
    return {
        "engagement_proxy": {
            "definition": (
                "A descriptive 0-1 blend of observable movement, presence activity and "
                "speech activity. It is NOT a validated measure of attention, emotion, "
                "comprehension or learning."
            ),
            "formula": (
                "visual = 0.6 * active_ratio + 0.4 * movement_index; "
                "audio = min(1, audio_active_ratio / 0.6); "
                "score = 0.65 * visual + 0.35 * audio when both exist, "
                "otherwise the available component alone (weights renormalised)."
            ),
            "movement_index": (
                "mean centre displacement between samples / frame width, "
                f"multiplied by {MOVEMENT_SCALE:.0f} and clipped to 0-1."
            ),
            "active_ratio": (
                f"share of movement observations above {MOVEMENT_ACTIVE_THRESHOLD} of frame width."
            ),
            "missing_data_policy": (
                "Missing camera or audio signals are excluded from the blend, never set to "
                "zero. If neither signal exists the score is null and no judgement is made."
            ),
            "confidence_rules": {
                "high": "both audio and visual signals, >=10 movement observations, >=2 participants",
                "medium": "both signals with fewer observations, or >=6 visual observations",
                "low": "single signal or sparse observations",
            },
            "window_sec": window_sec,
            "sample_interval_sec": sample_interval,
        },
        "attendance": {
            "rule": (
                "A track counts as Present/Late only if it persists for the configured "
                "minimum presence duration. Shorter tracks are Unconfirmed."
            ),
            "late_rule": "First seen after the configured arrival window => Late.",
            "identity": (
                "Tracks are anonymous by default. Names appear only after a teacher manually "
                "maps a track to an authorised roster entry. No face recognition is used."
            ),
        },
        "head_orientation": {
            "method": "OpenCV Haar frontal-face position relative to the body box (approximate).",
            "limitations": (
                "Only frontal faces are detected; turned heads usually become 'unknown'. "
                "Do not interpret orientation as attention."
            ),
        },
        "audio": {
            "method": "Voice activity detection on a 16 kHz mono track; no speaker identification.",
            "limitations": "Speech activity is not equivalent to student participation or engagement.",
        },
    }


def build_analytics(
    vision: VisionResult,
    audio: AudioAnalysis,
    attendance_summary: dict[str, Any],
    *,
    window_sec: float,
    sample_interval: float,
    min_presence_sec: float,
    late_after_sec: float,
) -> dict[str, Any]:
    quality = build_quality(vision, audio, vision.tracks)
    global_warnings = list(quality["warnings"])
    windows = build_windows(
        vision.tracks,
        audio,
        vision.duration_sec,
        window_sec,
        vision.effective_interval,
        global_warnings,
    )
    average, confidence = _weighted_average(windows)
    scored = [w for w in windows if w.engagement_score is not None]
    peak = max(scored, key=lambda w: w.engagement_score) if scored else None
    low = min(scored, key=lambda w: w.engagement_score) if scored else None

    return {
        "windows": windows,
        "average_engagement": average,
        "engagement_confidence": confidence,
        "peak_window": peak.window_index if peak else None,
        "lowest_window": low.window_index if low else None,
        "movement_summary": build_movement_summary(vision.tracks, audio),
        "quality": quality,
        "warnings": global_warnings,
        "methodology": methodology(window_sec, sample_interval),
        "audio": audio,
        "attendance_summary": attendance_summary,
        "duration_sec": vision.duration_sec,
        "window_sec": window_sec,
        "min_presence_sec": min_presence_sec,
        "late_after_sec": late_after_sec,
        "fusion_session_descriptor": fuse_modalities(vision, audio, session_id=None),
    }
