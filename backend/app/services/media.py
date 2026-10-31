"""Media probing, validation, audio extraction and WAV helpers.

Uses the ffmpeg binary bundled with ``imageio-ffmpeg`` so no system-wide
ffmpeg installation is required. OpenCV handles frame decoding.
"""

from __future__ import annotations

import re
import subprocess
import wave
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np

from ..config import get_config
from .storage import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS


class MediaValidationError(Exception):
    """Raised when media cannot be used for analysis."""


@dataclass
class MediaInfo:
    path: Path
    duration_sec: float
    has_video: bool
    has_audio: bool
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    warnings: list[str] = field(default_factory=list)


_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
_VIDEO_RE = re.compile(r"Stream #\d+:\d+.*?: Video: ([^,\s]+).*?(\d{2,5})x(\d{2,5})")
_AUDIO_RE = re.compile(r"Stream #\d+:\d+.*?: Audio: ([^,\s]+)")
_FPS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*fps")


def ffmpeg_path() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def ffmpeg_version() -> str | None:
    try:
        out = subprocess.run(
            [ffmpeg_path(), "-version"], capture_output=True, text=True, timeout=20
        )
        return out.stdout.splitlines()[0] if out.stdout else None
    except Exception:  # pragma: no cover - environment dependent
        return None


def _run_ffmpeg_probe(path: Path) -> str:
    try:
        proc = subprocess.run(
            [ffmpeg_path(), "-hide_banner", "-i", str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except subprocess.TimeoutExpired as exc:  # pragma: no cover
        raise MediaValidationError("Timed out while reading media metadata") from exc
    return (proc.stderr or "") + (proc.stdout or "")


def probe_media(path: Path) -> MediaInfo:
    if not path.exists():
        raise MediaValidationError("Media file not found")
    text = _run_ffmpeg_probe(path)
    if "Invalid data found" in text or "moov atom not found" in text:
        raise MediaValidationError("The file is not a valid or complete media file")

    duration = 0.0
    if match := _DURATION_RE.search(text):
        hours, minutes, seconds = match.groups()
        duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)

    video_match = _VIDEO_RE.search(text)
    audio_match = _AUDIO_RE.search(text)
    width = height = None
    if video_match:
        width, height = int(video_match.group(2)), int(video_match.group(3))
    fps_match = _FPS_RE.search(text)
    fps = float(fps_match.group(1)) if fps_match else None

    warnings: list[str] = []
    if duration <= 0:
        # Some containers report N/A; fall back to OpenCV frame count.
        cap = cv2.VideoCapture(str(path))
        if cap.isOpened():
            count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            rate = cap.get(cv2.CAP_PROP_FPS) or 25
            if count and rate:
                duration = float(count) / float(rate)
        cap.release()
    if duration <= 0:
        raise MediaValidationError("Could not determine media duration")

    return MediaInfo(
        path=path,
        duration_sec=round(duration, 3),
        has_video=bool(video_match) or path.suffix.lower() in VIDEO_EXTENSIONS,
        has_audio=bool(audio_match),
        width=width,
        height=height,
        fps=fps,
        video_codec=video_match.group(1) if video_match else None,
        audio_codec=audio_match.group(1) if audio_match else None,
        warnings=warnings,
    )


def validate_video(path: Path) -> MediaInfo:
    cfg = get_config()
    if path.suffix.lower() not in VIDEO_EXTENSIONS:
        raise MediaValidationError("Unsupported video format")
    info = probe_media(path)
    if not info.has_video:
        raise MediaValidationError("The uploaded file does not contain a video stream")
    if info.duration_sec < cfg.min_media_duration_sec:
        raise MediaValidationError("Video is too short to analyse (minimum 1 second)")
    if info.duration_sec > cfg.max_media_duration_sec:
        raise MediaValidationError(
            f"Video is longer than the {cfg.max_media_duration_sec / 3600:.1f} hour limit"
        )
    cap = cv2.VideoCapture(str(path))
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        raise MediaValidationError("The video could not be decoded (missing codec or corrupt data)")
    return info


def validate_audio(path: Path) -> MediaInfo:
    cfg = get_config()
    if path.suffix.lower() not in AUDIO_EXTENSIONS:
        raise MediaValidationError("Unsupported audio format")
    info = probe_media(path)
    if not info.has_audio:
        raise MediaValidationError("The uploaded file does not contain an audio stream")
    if info.duration_sec < cfg.min_media_duration_sec:
        raise MediaValidationError("Audio is too short to analyse (minimum 1 second)")
    if info.duration_sec > cfg.max_media_duration_sec:
        raise MediaValidationError("Audio exceeds the maximum duration")
    return info


def extract_audio(source: Path, target_wav: Path, max_seconds: float | None = None) -> bool:
    """Extract/normalise audio to 16 kHz mono PCM WAV. Returns False if no audio."""
    target_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_path(),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-acodec",
        "pcm_s16le",
    ]
    if max_seconds:
        cmd += ["-t", f"{max_seconds:.3f}"]
    cmd.append(str(target_wav))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:  # pragma: no cover
        return False
    if proc.returncode != 0 or not target_wav.exists() or target_wav.stat().st_size <= 44:
        target_wav.unlink(missing_ok=True)
        return False
    return True


def read_wav_mono16(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as handle:
        if handle.getsampwidth() != 2:
            raise MediaValidationError("Expected 16-bit PCM WAV")
        channels = handle.getnchannels()
        rate = handle.getframerate()
        raw = handle.readframes(handle.getnframes())
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples, rate


def write_wav_mono16(path: Path, samples: np.ndarray, rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(pcm.tobytes())


def probe_video_frames(path: Path) -> tuple[float, int, int, float]:
    """Return (fps, width, height, frame_count) via OpenCV."""
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise MediaValidationError("OpenCV could not open the video")
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        return fps, width, height, count
    finally:
        cap.release()
