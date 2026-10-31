"""Session management, media upload, processing and optional live capture."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ..config import get_config
from ..database import get_db
from ..errors import ApiError
from ..models import ProcessingJob, Session
from ..schemas import (
    JobOut,
    LiveStartIn,
    ProcessOut,
    SessionCreate,
    SessionDetail,
    SessionOut,
    StatusOut,
    UploadOut,
)
from ..serializers import session_out
from ..services.events import log_event
from ..services.live import LiveError, live_manager
from ..services.media import (
    MediaValidationError,
    probe_media,
    probe_video_frames,
    validate_audio,
    validate_video,
)
from ..services.pipeline import PipelineBusyError, clear_results, create_session_record, pipeline
from ..services.storage import (
    StorageError,
    artifact_path,
    media_path,
    remove_session_files,
    save_upload,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sessions"])


def get_session_or_404(db: DbSession, session_id: str) -> Session:
    session = db.get(Session, session_id)
    if session is None:
        raise ApiError(404, "session_not_found", "Session not found")
    return session


def _latest_job(db: DbSession, session_id: str) -> ProcessingJob | None:
    return db.scalars(
        select(ProcessingJob)
        .where(ProcessingJob.session_id == session_id)
        .order_by(ProcessingJob.created_at.desc())
        .limit(1)
    ).first()


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    db: DbSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
    include_demo: bool = Query(default=True),
    q: str | None = Query(default=None, max_length=120),
) -> list[SessionOut]:
    stmt = select(Session).order_by(Session.created_at.desc())
    if status:
        stmt = stmt.where(Session.status == status)
    if not include_demo:
        stmt = stmt.where(Session.is_demo.is_(False))
    if q:
        stmt = stmt.where(Session.title.ilike(f"%{q}%"))
    stmt = stmt.offset(offset).limit(limit)
    return [session_out(s) for s in db.scalars(stmt).all()]


@router.post("/sessions", response_model=SessionOut, status_code=201)
def create_session(payload: SessionCreate, db: DbSession = Depends(get_db)) -> SessionOut:
    session = create_session_record(db, payload)
    log_event(
        db,
        "info",
        "session_created",
        f"Session '{session.title}' created for {session.session_date.isoformat()}.",
        session.id,
    )
    return session_out(session)


@router.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session(session_id: str, db: DbSession = Depends(get_db)) -> SessionDetail:
    session = get_session_or_404(db, session_id)
    detail = SessionDetail(**session_out(session).model_dump())
    job = _latest_job(db, session_id)
    detail.latest_job = JobOut.model_validate(job) if job else None
    return detail


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str, db: DbSession = Depends(get_db)) -> Response:
    session = get_session_or_404(db, session_id)
    if session_id in pipeline.status().get("active", []) or session_id in pipeline.status().get(
        "pending", []
    ):
        raise ApiError(409, "session_processing", "Cannot delete a session while it is processing")
    if live_manager.status(session_id).get("active"):
        raise ApiError(409, "session_recording", "Stop the live capture before deleting")
    title = session.title
    remove_session_files(session_id)
    db.delete(session)
    db.commit()
    log_event(db, "info", "session_deleted", f"Session '{title}' and local media deleted.")
    return Response(status_code=204)


@router.post("/sessions/{session_id}/upload", response_model=UploadOut, status_code=202)
async def upload_media(
    session_id: str,
    video: UploadFile | None = File(default=None),
    audio: UploadFile | None = File(default=None),
    db: DbSession = Depends(get_db),
) -> UploadOut:
    session = get_session_or_404(db, session_id)
    if not video and not audio:
        raise ApiError(400, "missing_file", "Provide a video file, an audio file, or both")
    if session_id in pipeline.status().get("active", []):
        raise ApiError(409, "session_processing", "Cannot replace media while processing")

    cfg = get_config()
    saved_video: tuple[str, int] | None = None
    saved_audio: tuple[str, int] | None = None
    try:
        if video is not None:
            filename, path, size = await save_upload(video, session_id, "video", cfg.max_upload_mb)
            try:
                info = validate_video(path)
                fps, width, height, _ = probe_video_frames(path)
            except MediaValidationError:
                path.unlink(missing_ok=True)
                raise
            saved_video = (filename, size)
            session.duration_sec = info.duration_sec
            session.fps = round(fps, 3) if fps else None
            session.width = width or None
            session.height = height or None
            session.has_audio = info.has_audio

        if audio is not None:
            filename, path, size = await save_upload(audio, session_id, "audio", cfg.max_upload_mb)
            try:
                audio_info = validate_audio(path)
            except MediaValidationError:
                path.unlink(missing_ok=True)
                raise
            saved_audio = (filename, size)
            if session.duration_sec is None:
                session.duration_sec = audio_info.duration_sec
            session.has_audio = True

        # Replace old files only after the new upload validated successfully.
        if saved_video:
            if session.video_filename and session.video_filename != saved_video[0]:
                media_path(session_id, session.video_filename).unlink(missing_ok=True)
            if session.audio_filename:
                media_path(session_id, session.audio_filename).unlink(missing_ok=True)
                session.audio_filename = None
                session.audio_size_bytes = None
            session.video_filename, session.video_size_bytes = saved_video
        if saved_audio:
            if session.audio_filename and session.audio_filename != saved_audio[0]:
                media_path(session_id, session.audio_filename).unlink(missing_ok=True)
            session.audio_filename, session.audio_size_bytes = saved_audio

        artifact_path(session_id, "audio-16k.wav").unlink(missing_ok=True)
        clear_results(db, session_id)
        session.status = "uploaded"
        session.error_message = None
        session.processed_at = None
        session.quality_json = {}
        session.methodology_json = {}
        session.detector_used = None
        session.audio_method = None
        db.commit()
        log_event(
            db,
            "info",
            "media_uploaded",
            "Media uploaded and validated locally; stored only in the local data directory.",
            session_id,
        )
        return UploadOut(
            session_id=session_id,
            status=session.status,
            video_filename=session.video_filename,
            audio_filename=session.audio_filename,
            duration_sec=session.duration_sec,
            has_audio=session.has_audio,
            size_bytes=(saved_video or saved_audio or (None, None))[1],
            message="Media uploaded and validated. Start processing when ready.",
        )
    except StorageError as exc:
        raise ApiError(400, "upload_rejected", str(exc)) from exc
    except MediaValidationError as exc:
        raise ApiError(422, "invalid_media", str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.post("/sessions/{session_id}/process", response_model=ProcessOut, status_code=202)
def start_processing(session_id: str, db: DbSession = Depends(get_db)) -> ProcessOut:
    session = get_session_or_404(db, session_id)
    if not session.video_filename and not session.audio_filename:
        raise ApiError(400, "no_media", "Upload a recording before starting analysis")
    if session.status in {"queued", "processing"}:
        raise ApiError(409, "already_processing", "This session is already queued or processing")
    try:
        job_id = pipeline.submit(session_id)
    except PipelineBusyError as exc:
        raise ApiError(409, "queue_busy", str(exc)) from exc
    return ProcessOut(
        session_id=session_id,
        status="queued",
        job_id=job_id,
        message="Analysis queued. Poll the status endpoint for progress.",
    )


@router.get("/sessions/{session_id}/status", response_model=StatusOut)
def processing_status(session_id: str, db: DbSession = Depends(get_db)) -> StatusOut:
    session = get_session_or_404(db, session_id)
    job = _latest_job(db, session_id)
    live = live_manager.status(session_id)
    message = job.message if job else session.error_message
    if live.get("active"):
        message = live.get("message")
    return StatusOut(
        session_id=session_id,
        status=session.status,
        error=session.error_message,
        job=JobOut.model_validate(job) if job else None,
        media_ready=bool(session.video_filename or session.audio_filename),
        progress=job.progress if job else (100.0 if session.status == "completed" else 0.0),
        stage=job.stage if job else None,
        message=message,
    )


# --------------------------------------------------------------------------
# Optional live capture
# --------------------------------------------------------------------------
@router.post("/sessions/{session_id}/live/start")
def start_live(
    session_id: str, payload: LiveStartIn, db: DbSession = Depends(get_db)
) -> dict:
    session = get_session_or_404(db, session_id)
    if session.status in {"queued", "processing"}:
        raise ApiError(409, "already_processing", "This session is currently processing")
    cfg = get_config()
    try:
        status = live_manager.start(
            session_id,
            camera_index=payload.camera_index if payload.camera_index is not None else cfg.live_camera_index,
            max_seconds=min(payload.max_seconds, cfg.live_max_seconds),
            auto_process=payload.auto_process,
        )
    except LiveError as exc:
        raise ApiError(503, "live_unavailable", str(exc)) from exc
    log_event(db, "info", "live_capture_started", "Live camera capture started.", session_id)
    return status


@router.post("/sessions/{session_id}/live/stop")
def stop_live(session_id: str, db: DbSession = Depends(get_db)) -> dict:
    get_session_or_404(db, session_id)
    try:
        return live_manager.stop(session_id)
    except LiveError as exc:
        raise ApiError(409, "live_not_running", str(exc)) from exc


@router.get("/sessions/{session_id}/live/status")
def live_status(session_id: str, db: DbSession = Depends(get_db)) -> dict:
    get_session_or_404(db, session_id)
    return live_manager.status(session_id)
