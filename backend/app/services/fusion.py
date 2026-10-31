"""Multimodal Signal Fusion — descriptive session-level integration.

Combines vision and audio observations by session and timestamp.
Does NOT claim attention, emotion, identity, or academic performance.
Produces explainable descriptor outputs with modality availability.
"""
from __future__ import annotations
from typing import Any

from .vision import VisionResult
from .audio import AudioAnalysis


def fuse_modalities(
    vision: VisionResult | None,
    audio: AudioAnalysis | None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Produce a unified descriptive session-level fusion result.

    Handles missing audio or vision gracefully; never treats missing
    data as zero engagement; explains which signals were available.
    """
    result: dict[str, Any] = {
        "session_id": session_id,
        "fusion_version": "1.0",
        "methodology": "descriptive proxy combination; not a measure of attention or learning",
        "modalities": {},
        "timestamp_association": "session-level; observations associated by session identifier",
        "missing_signals_explained": [],
        "normalized_available": {},
        "duplicate_filter_applied": False,
        "warnings": [],
    }

    vision_available = vision is not None and getattr(vision, "available", True)
    audio_available = audio is not None and getattr(audio, "available", True)

    result["modalities"]["vision"] = {
        "available": vision_available,
        "tracks_detected": len(vision.tracks) if vision_available else 0,
        "duration_sec": vision.duration_sec if vision_available else None,
    }
    result["modalities"]["audio"] = {
        "available": audio_available,
        "speech_active_ratio": getattr(audio, "speech_ratio", None) if audio_available else None,
        "method": getattr(audio, "method", None) if audio_available else None,
    }

    if not vision_available and not audio_available:
        result["missing_signals_explained"].append("Both vision and audio unavailable.")
        result["normalized_available"] = {}
        result["warnings"].append("No multimodal data to combine; analytics will rely on session metadata only.")
        return result

    if vision_available and not audio_available:
        result["missing_signals_explained"].append("Audio unavailable; using vision-only descriptive indicators.")
        result["normalized_available"] = {"vision": 1.0, "audio": 0.0}
        result["warnings"].append("Audio track missing or could not be decoded; vision-only analysis.")
    elif audio_available and not vision_available:
        result["missing_signals_explained"].append("Vision unavailable; using audio-only descriptive indicators.")
        result["normalized_available"] = {"vision": 0.0, "audio": 1.0}
        result["warnings"].append("Vision could not be analyzed; audio-only analysis.")
    else:
        result["missing_signals_explained"].append("Both vision and audio available.")
        result["normalized_available"] = {"vision": 1.0, "audio": 1.0}

    # Avoid treating missing as zero by using explicit flags above.
    # No arbitrary score invented; descriptive only.
    result["fusion_description"] = (
        f"Vision tracks={len(vision.tracks) if vision_available else 0}, "
        f"audio available={audio_available}. "
        f"Missing signals explained: {len(result['missing_signals_explained'])} note(s)."
    )
    return result


def validate_fusion_input(
    vision: VisionResult | None,
    audio: AudioAnalysis | None,
) -> list[str]:
    errors: list[str] = []
    if vision is not None:
        if getattr(vision, "duration_sec", None) is not None and vision.duration_sec < 0:
            errors.append("Invalid vision duration (negative).")
        if hasattr(vision, "tracks") and vision.tracks is not None:
            seen = set()
            for t in vision.tracks:
                key = (getattr(t, "start", None), getattr(t, "end", None))
                if key in seen:
                    errors.append("Duplicate vision track observation detected.")
                    break
                seen.add(key)
    if audio is not None:
        if getattr(audio, "speech_ratio", None) is not None and (audio.speech_ratio < 0 or audio.speech_ratio > 1):
            errors.append("Audio speech ratio out of valid range.")
    return errors
