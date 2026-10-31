"""Background media-processing pipeline with bounded concurrency."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from ..config import get_config
from ..database import SessionLocal
from ..models import (
    AnalysisWindow,
    AttendanceRecord,
    AudioInterval,
    ParticipantTrack,
    ProcessingJob,
    Recommendation,
    RosterEntry,
    Session,
)
from ..schemas import SessionCreate
from . import vision
from .analytics import build_analytics, methodology
from .attendance import decide_attendance, summarize
from .audio import analyze_audio, silence_intervals
from .events import log_event
from .media import MediaValidationError, extract_audio, probe_media, probe_video_frames
from .recommend import AnalyticsContext, build_recommendations
from .settings_service import get_preferences
from .storage import artifact_path, media_path, remove_session_files
from .vision import analyze_video

logger = logging.getLogger(__name__)


class PipelineBusyError(Exception):
    pass


class Pipeline:
    """Single-worker executor: analysis is CPU-bound on student hardware."""

    def __init__(self, max_workers: int = 1, max_pending: int = 3) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="classmind")
        self._lock = threading.Lock()
        self._active: set[str] = set()
        self._pending: set[str] = set()
        self._max_pending = max_pending

    def submit(self, session_id: str) -> str:
        with self._lock:
            if session_id in self._active or session_id in self._pending:
                raise PipelineBusyError("This session is already being processed")
            if len(self._pending) >= self._max_pending:
                raise PipelineBusyError("Processing queue is full; try again shortly")
            self._pending.add(session_id)

        db = SessionLocal()
        try:
            session = db.get(Session, session_id)
            if session is None:
                raise ValueError("Session not found")
            job = ProcessingJob(
                session_id=session_id,
                status="queued",
                stage="queued",
                progress=0.0,
                message="Queued for processing",
            )
            db.add(job)
            session.status = "queued"
            session.error_message = None
            db.commit()
            job_id = job.id
            log_event(db, "info", "processing_queued", "Analysis queued", session_id)
        finally:
            db.close()

        self._executor.submit(self._run_guarded, session_id, job_id)
        return job_id

    def _run_guarded(self, session_id: str, job_id: str) -> None:
        with self._lock:
            self._pending.discard(session_id)
            self._active.add(session_id)
        try:
            run_processing(session_id, job_id)
        except Exception:  # pragma: no cover - defensive; run_processing handles errors
            logger.exception("Unhandled processing failure for %s", session_id)
        finally:
            with self._lock:
                self._active.discard(session_id)

    def run_now(self, session_id: str) -> None:
        """Synchronous execution used by tests and the demo seeder."""
        db = SessionLocal()
        try:
            session = db.get(Session, session_id)
            if session is None:
                raise ValueError("Session not found")
            job = ProcessingJob(
                session_id=session_id,
                status="queued",
                stage="queued",
                progress=0.0,
                message="Queued for processing",
            )
            db.add(job)
            session.status = "queued"
            db.commit()
            job_id = job.id
        finally:
            db.close()
        run_processing(session_id, job_id)

    def is_busy(self) -> bool:
        with self._lock:
            return bool(self._active or self._pending)

    def status(self) -> dict:
        with self._lock:
            return {"active": sorted(self._active), "pending": sorted(self._pending)}

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


pipeline = Pipeline()


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _set_job(db: DbSession, job: ProcessingJob | None, *, progress: float, stage: str, message: str) -> None:
    if job is None:
        return
    job.progress = round(max(0.0, min(100.0, progress)), 1)
    job.stage = stage
    job.message = message
    if job.started_at is None:
        job.started_at = datetime.now(timezone.utc)
    db.commit()


def _fail(db: DbSession, session: Session, job: ProcessingJob | None, message: str) -> None:
    safe = message[:800]
    session.status = "failed"
    session.error_message = safe
    if job is not None:
        job.status = "failed"
        job.stage = "failed"
        job.error = safe
        job.progress = 100.0
        job.finished_at = datetime.now(timezone.utc)
    db.commit()
    log_event(db, "error", "processing_failed", safe, session.id)


def recover_interrupted_jobs() -> int:
    """Mark jobs left running by a crash/restart as failed."""
    db = SessionLocal()
    try:
        jobs = db.scalars(
            select(ProcessingJob).where(ProcessingJob.status.in_(["queued", "processing"]))
        ).all()
        for job in jobs:
            job.status = "failed"
            job.stage = "interrupted"
            job.error = "Processing was interrupted by an application restart."
            job.finished_at = datetime.now(timezone.utc)
        sessions = db.scalars(
            select(Session).where(Session.status.in_(["queued", "processing"]))
        ).all()
        for session in sessions:
            session.status = "failed"
            session.error_message = (
                "Processing was interrupted by an application restart. You can process again."
            )
        if jobs or sessions:
            db.commit()
            log_event(
                db,
                "warning",
                "processing_recovered",
                f"Marked {len(jobs)} interrupted job(s) as failed after restart.",
            )
        return len(jobs)
    finally:
        db.close()


def clear_results(db: DbSession, session_id: str) -> dict[int, tuple[str | None, str | None]]:
    """Remove previous analysis rows, returning track_index -> (roster_id, name)."""
    old_mappings: dict[int, tuple[str | None, str | None]] = {}
    rows = db.execute(
        select(ParticipantTrack.track_index, AttendanceRecord.roster_id, AttendanceRecord.display_name)
        .join(AttendanceRecord, AttendanceRecord.track_id == ParticipantTrack.id)
        .where(ParticipantTrack.session_id == session_id)
    ).all()
    for track_index, roster_id, name in rows:
        if roster_id:
            old_mappings[int(track_index)] = (roster_id, name)

    for model in (AttendanceRecord, ParticipantTrack, AnalysisWindow, AudioInterval, Recommendation):
        db.execute(delete(model).where(model.session_id == session_id))
    db.commit()
    return old_mappings


def _roster_name(db: DbSession, roster_id: str | None) -> str | None:
    if not roster_id:
        return None
    entry = db.get(RosterEntry, roster_id)
    return entry.name if entry else None


# --------------------------------------------------------------------------
# Main pipeline
# --------------------------------------------------------------------------
def run_processing(session_id: str, job_id: str | None = None) -> None:
    db = SessionLocal()
    session: Session | None = None
    job: ProcessingJob | None = None
    try:
        session = db.get(Session, session_id)
        if session is None:
            return
        job = db.get(ProcessingJob, job_id) if job_id else None
        session.status = "processing"
        session.error_message = None
        if job:
            job.status = "processing"
            job.started_at = datetime.now(timezone.utc)
        db.commit()
        _set_job(db, job, progress=2, stage="starting", message="Starting analysis")

        prefs = get_preferences(db)
        video_path = (
            media_path(session_id, session.video_filename) if session.video_filename else None
        )
        audio_upload = (
            media_path(session_id, session.audio_filename) if session.audio_filename else None
        )
        if video_path is None and audio_upload is None:
            raise MediaValidationError("No media has been uploaded for this session")
        if video_path is not None and not video_path.exists():
            raise MediaValidationError("The uploaded video file is missing from local storage")
        if audio_upload is not None and not audio_upload.exists():
            raise MediaValidationError("The uploaded audio file is missing from local storage")

        # ---- probe -------------------------------------------------------
        _set_job(db, job, progress=5, stage="validating", message="Reading media metadata")
        duration = 0.0
        fps = 0.0
        width = height = 0
        if video_path is not None:
            info = probe_media(video_path)
            duration = info.duration_sec
            try:
                fps, width, height, _count = probe_video_frames(video_path)
            except MediaValidationError:
                pass
            session.fps = round(fps, 3) if fps else None
            session.width = width or None
            session.height = height or None
            session.duration_sec = round(duration, 3)

        # ---- audio extraction -------------------------------------------
        wav_path = artifact_path(session_id, "audio-16k.wav")
        audio_source = audio_upload or video_path
        _set_job(db, job, progress=10, stage="audio", message="Extracting audio track")
        audio_extracted = False
        alignment_warning: str | None = None
        if audio_source is not None:
            audio_extracted = extract_audio(audio_source, wav_path)
            if audio_upload is not None and video_path is not None and audio_extracted:
                try:
                    audio_info = probe_media(audio_upload)
                    if abs(audio_info.duration_sec - duration) > 2.0:
                        alignment_warning = (
                            f"Separate audio ({audio_info.duration_sec:.0f}s) and video "
                            f"({duration:.0f}s) differ in length; they are aligned from 0 and "
                            "may drift."
                        )
                except MediaValidationError:
                    pass

        # ---- vision ------------------------------------------------------
        vision_result = None
        if video_path is not None:
            _set_job(db, job, progress=18, stage="vision", message="Detecting and tracking people")

            def progress_cb(done: int, total: int) -> None:
                pct = 18 + (48 * (done / max(1, total)))
                if done % 5 == 0 or done == total:
                    _set_job(
                        db,
                        job,
                        progress=pct,
                        stage="vision",
                        message=f"Analysing frames ({done}/{total})",
                    )

            detector = vision.build_detector(prefs.get("detector_backend"))
            vision_result = analyze_video(
                video_path,
                sample_interval=session.sample_interval_sec,
                max_frames=get_config().max_analysis_frames,
                max_width=get_config().analysis_max_width,
                detector=detector,
                progress_cb=progress_cb,
            )
            session.detector_used = vision_result.detector_name
            session.duration_sec = vision_result.duration_sec or session.duration_sec
            session.fps = vision_result.fps or session.fps
            session.width = vision_result.width or session.width
            session.height = vision_result.height or session.height
            db.commit()
        else:
            from .vision import VisionResult

            audio_duration = 0.0
            if audio_extracted:
                try:
                    audio_duration = probe_media(audio_upload or video_path).duration_sec
                except Exception:
                    audio_duration = 0.0
            vision_result = VisionResult(
                duration_sec=audio_duration,
                fps=0.0,
                width=0,
                height=0,
                sampled_frames=0,
                decode_failures=0,
                effective_interval=session.sample_interval_sec,
                brightness_mean=0.0,
                camera_motion=0.0,
                detector_name="none",
                tracks=[],
                warnings=["No video was supplied; visual indicators are unavailable."],
            )
            session.duration_sec = audio_duration
            session.detector_used = "none"

        # ---- audio analysis ---------------------------------------------
        _set_job(db, job, progress=70, stage="audio_analysis", message="Detecting speech activity")
        audio_result = analyze_audio(
            wav_path, duration_hint=session.duration_sec, backend=get_config().vad_backend
        )
        if alignment_warning:
            audio_result.warnings.append(alignment_warning)
        session.has_audio = audio_result.available
        session.audio_method = audio_result.method
        db.commit()

        # ---- attendance --------------------------------------------------
        _set_job(db, job, progress=78, stage="attendance", message="Applying presence thresholds")
        old_mappings = clear_results(db, session_id)
        decisions = []
        for track in vision_result.tracks:
            decision = decide_attendance(
                track,
                min_presence_sec=session.min_presence_sec,
                late_after_sec=session.late_after_sec,
            )
            decisions.append((track, decision))
        attendance_dicts = [
            {
                "state": d.state,
                "roster_id": old_mappings.get(t.index, (None, None))[0],
                "uncertain": d.uncertain,
            }
            for t, d in decisions
        ]
        attendance_summary = summarize(attendance_dicts)

        for track, decision in decisions:
            roster_id, mapped_name = old_mappings.get(track.index, (None, None))
            if roster_id and _roster_name(db, roster_id) is None:
                roster_id, mapped_name = None, None
            display_name = mapped_name or track.display_label
            db_track = ParticipantTrack(
                session_id=session_id,
                track_index=track.index,
                display_label=display_name,
                roster_id=roster_id,
                identity_status="mapped" if roster_id else "anonymous",
                first_seen_sec=track.first_seen,
                last_seen_sec=track.last_seen,
                duration_sec=track.duration_sec,
                samples_seen=track.samples_seen,
                confidence_avg=track.confidence_avg,
                movement_index=track.movement_index,
                inactive_sec=track.inactive_sec,
                head_center_ratio=track.head_center_ratio,
                head_left_ratio=track.head_left_ratio,
                head_right_ratio=track.head_right_ratio,
                head_unknown_ratio=track.head_unknown_ratio,
                attendance_state=decision.state,
                uncertain=decision.uncertain,
                note=decision.note,
            )
            db.add(db_track)
            db.flush()
            db.add(
                AttendanceRecord(
                    session_id=session_id,
                    track_id=db_track.id,
                    roster_id=roster_id,
                    display_name=display_name,
                    state=decision.state,
                    presence_sec=decision.presence_sec,
                    first_seen_sec=track.first_seen,
                    last_seen_sec=track.last_seen,
                    confidence=track.confidence_avg,
                    uncertain=decision.uncertain,
                    note=decision.note,
                )
            )
        db.commit()

        # ---- windows / analytics ----------------------------------------
        _set_job(db, job, progress=86, stage="analytics", message="Building time-window analytics")
        analytics = build_analytics(
            vision_result,
            audio_result,
            attendance_summary,
            window_sec=session.window_sec,
            sample_interval=session.sample_interval_sec,
            min_presence_sec=session.min_presence_sec,
            late_after_sec=session.late_after_sec,
        )

        for window in analytics["windows"]:
            db.add(
                AnalysisWindow(
                    session_id=session_id,
                    window_index=window.window_index,
                    start_sec=window.start_sec,
                    end_sec=window.end_sec,
                    participant_count=window.participant_count,
                    attendance_changes=window.attendance_changes,
                    movement_index=window.movement_index,
                    active_ratio=window.active_ratio,
                    inactivity_ratio=window.inactivity_ratio,
                    looking_away_ratio=window.looking_away_ratio,
                    audio_active_ratio=window.audio_active_ratio,
                    engagement_score=window.engagement_score,
                    engagement_confidence=window.engagement_confidence,
                    data_quality=window.data_quality,
                    warnings_json=window.warnings,
                    metrics_json=window.metrics,
                )
            )

        if audio_result.available:
            for interval in audio_result.intervals:
                db.add(
                    AudioInterval(
                        session_id=session_id,
                        start_sec=interval.start_sec,
                        end_sec=interval.end_sec,
                        kind="speech",
                        mean_energy=interval.mean_energy,
                    )
                )
            for start, end in silence_intervals(audio_result.intervals, session.duration_sec or 0):
                db.add(
                    AudioInterval(
                        session_id=session_id,
                        start_sec=start,
                        end_sec=end,
                        kind="silence",
                        mean_energy=0.0,
                    )
                )
        db.commit()

        # ---- recommendations --------------------------------------------
        _set_job(db, job, progress=93, stage="recommendations", message="Generating teaching suggestions")
        context = AnalyticsContext(
            duration_sec=session.duration_sec or 0.0,
            windows=analytics["windows"],
            audio=audio_result,
            quality=analytics["quality"],
            movement_summary=analytics["movement_summary"],
            attendance=attendance_summary,
            notes=session.notes,
            session_title=session.title,
            subject=session.subject,
            window_sec=session.window_sec,
        )
        recs, meta = build_recommendations(context)
        for item in recs:
            db.add(
                Recommendation(
                    session_id=session_id,
                    source=item["source"],
                    category=item["category"],
                    title=item["title"],
                    detail=item["detail"],
                    evidence=item["evidence"],
                    observed=item["observed"],
                    interpretation=item["interpretation"],
                    start_sec=item["start_sec"],
                    end_sec=item["end_sec"],
                    priority=item["priority"],
                    confidence=item["confidence"],
                )
            )
        db.commit()

        # ---- finalise ----------------------------------------------------
        quality = dict(analytics["quality"])
        quality.update(
            {
                "average_engagement": analytics["average_engagement"],
                "engagement_confidence": analytics["engagement_confidence"],
                "movement_summary": analytics["movement_summary"],
                "audio_available": audio_result.available,
                "audio_method": audio_result.method,
                "audio_warnings": audio_result.warnings,
                "warnings": analytics["warnings"],
                "recommendation_meta": meta,
                "frames_sampled": vision_result.sampled_frames,
            }
        )
        session.quality_json = quality
        session.methodology_json = analytics["methodology"] or methodology(
            session.window_sec, session.sample_interval_sec
        )
        session.processed_at = datetime.now(timezone.utc)
        session.status = "completed"
        session.error_message = None
        db.commit()

        if prefs.get("delete_media_after_processing"):
            _remove_media_only(session)

        if job:
            job.status = "completed"
            job.stage = "completed"
            job.progress = 100.0
            job.message = "Analysis complete"
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
        log_event(
            db,
            "success",
            "processing_completed",
            f"Analysis completed for '{session.title}' ({len(vision_result.tracks)} tracks).",
            session_id,
        )
    except Exception as exc:  # noqa: BLE001 - surfaced to the teacher, sanitised
        logger.exception("Processing failed for session %s", session_id)
        if session is not None:
            _fail(db, session, job, f"{type(exc).__name__}: {exc}")
        else:
            db.rollback()
    finally:
        db.close()


def _remove_media_only(session: Session) -> None:
    """Retention option: delete recordings but keep analytics."""
    for name in (session.video_filename, session.audio_filename):
        if not name:
            continue
        try:
            media_path(session.id, name).unlink(missing_ok=True)
        except Exception:  # pragma: no cover
            pass
    try:
        artifact_path(session.id, "audio-16k.wav").unlink(missing_ok=True)
    except Exception:  # pragma: no cover
        pass


def delete_session(session_id: str) -> bool:
    db = SessionLocal()
    try:
        session = db.get(Session, session_id)
        if session is None:
            return False
        remove_session_files(session_id)
        db.delete(session)
        db.commit()
        log_event(db, "info", "session_deleted", "Session and local media deleted", None)
        return True
    finally:
        db.close()


def create_session_record(db: DbSession, payload: SessionCreate, is_demo: bool = False) -> Session:
    prefs = get_preferences(db)
    session = Session(
        title=payload.title,
        subject=payload.subject,
        session_date=payload.session_date,
        class_label=payload.class_label,
        notes=payload.notes,
        is_demo=is_demo,
        sample_interval_sec=payload.sample_interval_sec or prefs["sample_interval_sec"],
        min_presence_sec=payload.min_presence_sec or prefs["min_presence_sec"],
        late_after_sec=payload.late_after_sec
        if payload.late_after_sec is not None
        else prefs["late_after_sec"],
        window_sec=payload.window_sec or prefs["window_sec"],
        status="created",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _duration_label(seconds: float | None) -> str:
    if not seconds:
        return "unknown duration"
    return f"{seconds / 60:.1f} min"


def _path_exists(path: Path | None) -> bool:
    return bool(path and path.exists())

