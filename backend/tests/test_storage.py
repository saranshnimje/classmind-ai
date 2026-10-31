"""Storage safety: path traversal, size limits, extension validation."""

from __future__ import annotations

import asyncio
import io

import pytest
from starlette.datastructures import UploadFile

from backend.app.services.storage import (
    StorageError,
    media_path,
    safe_resolve,
    save_upload,
    session_dir,
    validate_session_id,
)

SESSION_ID = "a" * 32


def test_invalid_session_ids_rejected():
    for bad in ["../etc", "abc", "A" * 32, "a" * 31, ""]:
        with pytest.raises(StorageError):
            validate_session_id(bad)


def test_path_traversal_rejected():
    with pytest.raises(StorageError):
        media_path(SESSION_ID, "../secret.mp4")
    with pytest.raises(StorageError):
        safe_resolve("../../Windows/System32/config")


def test_session_dir_is_inside_data_root():
    path = session_dir(SESSION_ID)
    assert path.name == SESSION_ID
    assert path.exists()


def test_unsupported_extension_rejected():
    upload = UploadFile(io.BytesIO(b"hello"), filename="notes.txt")
    with pytest.raises(StorageError, match="Unsupported"):
        asyncio.run(save_upload(upload, SESSION_ID, "video"))


def test_size_limit_enforced():
    upload = UploadFile(io.BytesIO(b"x" * 2048), filename="clip.mp4")
    with pytest.raises(StorageError, match="limit"):
        asyncio.run(save_upload(upload, SESSION_ID, "video", max_mb=0))


def test_empty_upload_rejected():
    upload = UploadFile(io.BytesIO(b""), filename="clip.mp4")
    with pytest.raises(StorageError, match="empty"):
        asyncio.run(save_upload(upload, SESSION_ID, "video"))


def test_valid_upload_uses_internal_filename():
    upload = UploadFile(io.BytesIO(b"fake-bytes"), filename="lesson.mp4")
    name, path, size = asyncio.run(save_upload(upload, SESSION_ID, "video"))
    assert name.startswith("video-")
    assert name.endswith(".mp4")
    assert name != "lesson.mp4"
    assert path.exists()
    assert size == len(b"fake-bytes")
