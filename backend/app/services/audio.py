"""Audio activity analysis (voice activity detection).

Default backend is a transparent energy-based VAD implemented with NumPy.
If ``silero-vad`` and PyTorch are installed, Silero VAD is used instead
(``CLASSMIND_VAD_BACKEND=silero`` forces it; ``energy`` disables it).

Loudness is never treated as engagement and speakers are never identified.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .media import read_wav_mono16

logger = logging.getLogger(__name__)

FRAME_SEC = 0.03
MERGE_GAP_SEC = 0.35
MIN_SPEECH_SEC = 0.2

_silero_model = None
_silero_failed = False


@dataclass
class SpeechInterval:
    start_sec: float
    end_sec: float
    mean_energy: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end_sec - self.start_sec)


@dataclass
class AudioAnalysis:
    available: bool
    method: str | None = None
    duration_sec: float = 0.0
    speech_sec: float = 0.0
    speech_ratio: float | None = None
    intervals: list[SpeechInterval] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    noise_floor: float = 0.0
    threshold: float = 0.0


def _merge_flags(flags: np.ndarray, frame_sec: float) -> list[tuple[float, float]]:
    intervals: list[tuple[float, float]] = []
    start: float | None = None
    for idx, active in enumerate(flags):
        t0 = idx * frame_sec
        t1 = (idx + 1) * frame_sec
        if active and start is None:
            start = t0
        elif not active and start is not None:
            intervals.append((start, t0))
            start = None
    if start is not None:
        intervals.append((start, len(flags) * frame_sec))

    merged: list[tuple[float, float]] = []
    for start, end in intervals:
        if merged and start - merged[-1][1] <= MERGE_GAP_SEC:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return [(s, e) for s, e in merged if e - s >= MIN_SPEECH_SEC]


def _energy_vad(samples: np.ndarray, rate: int) -> tuple[list[tuple[float, float]], float, float]:
    frame_len = max(1, int(rate * FRAME_SEC))
    count = len(samples) // frame_len
    if count == 0:
        return [], 0.0, 0.0
    frames = samples[: count * frame_len].reshape(count, frame_len)
    rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1))
    noise_floor = float(np.percentile(rms, 20))
    threshold = max(noise_floor * 2.5, 0.004)
    flags = rms > threshold
    # Require a tiny amount of context: drop isolated single-frame blips later
    # through the minimum-duration merge rule.
    intervals = _merge_flags(flags, FRAME_SEC)
    return intervals, noise_floor, threshold


def _silero_available() -> bool:
    global _silero_failed
    if _silero_failed:
        return False
    try:
        import torch  # noqa: F401
        import silero_vad  # noqa: F401

        return True
    except Exception:
        return False


def _get_silero():
    global _silero_model, _silero_failed
    if _silero_model is not None:
        return _silero_model
    try:
        from silero_vad import load_silero_vad

        _silero_model = load_silero_vad()
        return _silero_model
    except Exception as exc:  # pragma: no cover - optional dependency
        logger.info("Silero VAD unavailable: %s", exc)
        _silero_failed = True
        return None


def _silero_vad(samples: np.ndarray, rate: int) -> list[tuple[float, float]] | None:
    if rate != 16000:
        return None
    model = _get_silero()
    if model is None:
        return None
    import torch

    chunk = 512
    count = len(samples) // chunk
    if count == 0:
        return []
    try:
        model.reset_states()
    except Exception:
        pass
    probs: list[float] = []
    with torch.no_grad():
        for idx in range(count):
            audio = torch.from_numpy(samples[idx * chunk : (idx + 1) * chunk].copy()).float()
            try:
                prob = model(audio, 16000)
                probs.append(float(prob.item()))
            except Exception:  # pragma: no cover - model signature differences
                _silero_failed = True
                return None
    flags = np.array([p >= 0.5 for p in probs])
    return _merge_flags(flags, chunk / rate)


def analyze_audio(
    wav_path: Path,
    *,
    duration_hint: float | None = None,
    backend: str = "auto",
) -> AudioAnalysis:
    if not wav_path.exists():
        return AudioAnalysis(
            available=False, warnings=["No audio track could be extracted from this recording."]
        )
    try:
        samples, rate = read_wav_mono16(wav_path)
    except Exception as exc:
        return AudioAnalysis(available=False, warnings=[f"Audio could not be decoded: {exc}"])

    if samples.size == 0 or float(np.max(np.abs(samples))) < 1e-4:
        return AudioAnalysis(
            available=True,
            method="energy",
            duration_sec=0.0,
            warnings=["The audio track is silent; no speech activity was measured."],
        )

    duration = len(samples) / float(rate)
    if duration_hint:
        duration = min(duration, float(duration_hint))

    method = "energy"
    intervals: list[tuple[float, float]] = []
    if backend in {"auto", "silero"} and _silero_available():
        silero = _silero_vad(samples, rate)
        if silero is not None:
            intervals = silero
            method = "silero"
    if method == "energy":
        intervals, noise_floor, threshold = _energy_vad(samples, rate)
    else:
        noise_floor, threshold = 0.0, 0.0

    speech_intervals: list[SpeechInterval] = []
    for start, end in intervals:
        end = min(end, duration)
        if end - start < MIN_SPEECH_SEC:
            continue
        s0 = int(start * rate)
        s1 = int(end * rate)
        energy = float(np.sqrt(np.mean(samples[s0:s1].astype(np.float64) ** 2))) if s1 > s0 else 0.0
        speech_intervals.append(
            SpeechInterval(round(start, 3), round(end, 3), round(energy, 6))
        )

    speech_sec = sum(i.duration for i in speech_intervals)
    warnings: list[str] = []
    if not speech_intervals:
        warnings.append(
            "No speech-like activity was detected. This does not mean the class was disengaged."
        )
    if duration < 5:
        warnings.append("Audio clip is very short; activity ratios are unstable.")

    return AudioAnalysis(
        available=True,
        method=method,
        duration_sec=round(duration, 3),
        speech_sec=round(speech_sec, 3),
        speech_ratio=round(speech_sec / duration, 4) if duration > 0 else None,
        intervals=speech_intervals,
        warnings=warnings,
        noise_floor=round(noise_floor, 6),
        threshold=round(threshold, 6),
    )


def speech_overlap(intervals: list[SpeechInterval], start: float, end: float) -> float:
    """Seconds of speech overlapping [start, end]."""
    if end <= start:
        return 0.0
    total = 0.0
    for interval in intervals:
        overlap = min(end, interval.end_sec) - max(start, interval.start_sec)
        if overlap > 0:
            total += overlap
    return min(total, end - start)


def silence_intervals(intervals: list[SpeechInterval], duration: float) -> list[tuple[float, float]]:
    silence: list[tuple[float, float]] = []
    cursor = 0.0
    for interval in sorted(intervals, key=lambda i: i.start_sec):
        if interval.start_sec - cursor > 0.5:
            silence.append((cursor, interval.start_sec))
        cursor = max(cursor, interval.end_sec)
    if duration - cursor > 0.5:
        silence.append((cursor, duration))
    return [(round(a, 3), round(b, 3)) for a, b in silence]


def vad_status(backend: str = "auto") -> dict:
    silero = _silero_available() if backend in {"auto", "silero"} else False
    return {
        "backend_requested": backend,
        "active": "silero" if silero else "energy",
        "silero_available": silero,
        "note": (
            "Silero VAD is installed and will be used."
            if silero
            else "Using the built-in energy VAD (no extra model required)."
        ),
    }


def _round(value: float) -> float:
    return math.floor(value * 1000) / 1000
