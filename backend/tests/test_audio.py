"""Audio activity detection and interval maths."""

from __future__ import annotations

import numpy as np

from backend.app.services.audio import (
    analyze_audio,
    silence_intervals,
    speech_overlap,
    vad_status,
)
from backend.app.services.media import write_wav_mono16


def make_speech_wav(path, seconds=6, rate=16000):
    t = np.arange(seconds * rate) / rate
    # Speech-like bursts: 1s on, 0.5s off.
    gate = (np.sin(2 * np.pi * (1 / 1.5) * t) > 0).astype(np.float32)
    samples = 0.15 * np.sin(2 * np.pi * 220 * t).astype(np.float32) * gate
    samples += np.random.default_rng(7).normal(0, 0.002, samples.shape).astype(np.float32)
    write_wav_mono16(path, samples, rate)
    return path


def test_energy_vad_finds_speech(tmp_path):
    wav = make_speech_wav(tmp_path / "speech.wav", seconds=6)
    result = analyze_audio(wav, backend="energy")
    assert result.available is True
    assert result.method == "energy"
    assert result.duration_sec == 6.0
    assert result.speech_sec > 1.0
    assert result.speech_ratio is not None and 0.2 < result.speech_ratio < 0.9
    assert len(result.intervals) >= 1
    for interval in result.intervals:
        assert 0 <= interval.start_sec < interval.end_sec <= 6.05


def test_silent_audio_is_reported(tmp_path):
    wav = tmp_path / "silent.wav"
    write_wav_mono16(wav, np.zeros(16000 * 3, dtype=np.float32))
    result = analyze_audio(wav, backend="energy")
    assert result.available is True
    assert result.speech_sec == 0
    assert result.speech_ratio in (0.0, None)
    assert any("silent" in w.lower() for w in result.warnings)


def test_missing_audio_is_unavailable(tmp_path):
    result = analyze_audio(tmp_path / "does-not-exist.wav")
    assert result.available is False
    assert result.speech_ratio is None
    assert result.warnings


def test_speech_overlap_and_silence():
    wav_intervals = [
        type("I", (), {"start_sec": 1.0, "end_sec": 3.0, "duration": 2.0})(),
        type("I", (), {"start_sec": 6.0, "end_sec": 8.0, "duration": 2.0})(),
    ]
    assert speech_overlap(wav_intervals, 0, 4) == 2.0
    assert speech_overlap(wav_intervals, 2, 7) == 2.0
    assert speech_overlap(wav_intervals, 3, 5) == 0.0

    silence = silence_intervals(wav_intervals, 10.0)
    assert (0.0, 1.0) in silence
    assert (3.0, 6.0) in silence
    assert (8.0, 10.0) in silence


def test_vad_status_reports_backend():
    status = vad_status("energy")
    assert status["active"] == "energy"
    assert "backend_requested" in status
