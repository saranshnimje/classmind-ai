"""Safe local file storage for uploaded media and generated artifacts."""

from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

from ..config import get_config

SESSION_ID_RE = re.compile(r"^[a-f0-9]{32}$")

VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".avi", ".mkv", ".webm", ".mpeg", ".mpg"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus"}


class StorageError(Exception):
    """Raised for unsafe paths or rejected uploads."""


def validate_session_id(session_id: str) -> str:
    if not SESSION_ID_RE.match(session_id or ""):
        raise StorageError("Invalid session identifier")
    return session_id


def data_root() -> Path:
    return get_config().resolved_data_dir


def session_dir(session_id: str, create: bool = True) -> Path:
    validate_session_id(session_id)
    path = data_root() / "sessions" / session_id
    if create:
        path.mkdir(parents=True, exist_ok=True)
    resolved = path.resolve()
    if data_root() not in resolved.parents and resolved != data_root():
        raise StorageError("Path escapes the data directory")
    return resolved


def safe_resolve(relative_path: str) -> Path:
    """Resolve a stored relative path, refusing anything outside data/."""
    root = data_root()
    candidate = (root / relative_path).resolve()
    if root not in candidate.parents and candidate != root:
        raise StorageError("Path escapes the data directory")
    return candidate


def media_path(session_id: str, filename: str) -> Path:
    validate_session_id(session_id)
    if Path(filename).name != filename:
        raise StorageError("Invalid filename")
    candidate = (session_dir(session_id) / filename).resolve()
    if session_dir(session_id) not in candidate.parents:
        raise StorageError("Path escapes the session directory")
    return candidate


async def save_upload(
    upload: UploadFile,
    session_id: str,
    kind: str,
    max_mb: int | None = None,
) -> tuple[str, Path, int]:
    """Stream an upload to disk with extension/size validation.

    Returns (stored_filename, absolute_path, size_bytes). The original client
    filename is never used as a path component.
    """
    if kind not in {"video", "audio"}:
        raise StorageError("Unknown media kind")
    original = upload.filename or ""
    suffix = Path(original).suffix.lower()
    allowed = VIDEO_EXTENSIONS if kind == "video" else AUDIO_EXTENSIONS
    if suffix not in allowed:
        raise StorageError(
            f"Unsupported {kind} format '{suffix or 'unknown'}'. "
            f"Allowed: {', '.join(sorted(allowed))}"
        )

    limit_mb = max_mb if max_mb is not None else get_config().max_upload_mb
    limit_bytes = limit_mb * 1024 * 1024
    target = session_dir(session_id) / f"{kind}-{uuid.uuid4().hex[:12]}{suffix}"
    written = 0
    try:
        with target.open("wb") as handle:
            while chunk := await upload.read(1024 * 1024):
                written += len(chunk)
                if written > limit_bytes:
                    raise StorageError(f"File exceeds the {limit_mb} MB limit")
                handle.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    if written == 0:
        target.unlink(missing_ok=True)
        raise StorageError("Uploaded file is empty")

    return target.name, target, written


def remove_session_files(session_id: str) -> None:
    path = session_dir(session_id, create=False)
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def artifact_path(session_id: str, name: str) -> Path:
    """Path for generated artifacts (audio wav, exports) inside the session dir."""
    if Path(name).name != name:
        raise StorageError("Invalid artifact name")
    return session_dir(session_id) / name


def temp_dir() -> Path:
    path = data_root() / "temp"
    path.mkdir(parents=True, exist_ok=True)
    return path


def dir_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
