"""SQLAlchemy ORM models for ClassMind AI."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(String(120), nullable=False, default="General")
    class_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    session_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(24), default="created", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    video_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audio_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    video_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audio_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_audio: Mapped[bool] = mapped_column(Boolean, default=False)

    sample_interval_sec: Mapped[float] = mapped_column(Float, default=2.0)
    min_presence_sec: Mapped[float] = mapped_column(Float, default=30.0)
    late_after_sec: Mapped[float] = mapped_column(Float, default=300.0)
    window_sec: Mapped[float] = mapped_column(Float, default=300.0)

    detector_used: Mapped[str | None] = mapped_column(String(48), nullable=True)
    audio_method: Mapped[str | None] = mapped_column(String(48), nullable=True)
    quality_json: Mapped[dict] = mapped_column(JSON, default=dict)
    methodology_json: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tracks: Mapped[list[ParticipantTrack]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    attendance: Mapped[list[AttendanceRecord]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    windows: Mapped[list[AnalysisWindow]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    audio_intervals: Mapped[list[AudioInterval]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    recommendations: Mapped[list[Recommendation]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    jobs: Mapped[list[ProcessingJob]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )


class RosterEntry(Base):
    """Teacher-authorised roster. No biometric data is stored."""

    __tablename__ = "roster_entries"
    __table_args__ = (UniqueConstraint("class_label", "name", name="uq_roster_class_name"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    class_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ParticipantTrack(Base):
    __tablename__ = "participant_tracks"
    __table_args__ = (UniqueConstraint("session_id", "track_index", name="uq_track_session_index"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    track_index: Mapped[int] = mapped_column(Integer, nullable=False)
    display_label: Mapped[str] = mapped_column(String(120), nullable=False)
    roster_id: Mapped[str | None] = mapped_column(
        ForeignKey("roster_entries.id", ondelete="SET NULL"), nullable=True
    )
    identity_status: Mapped[str] = mapped_column(String(24), default="anonymous")

    first_seen_sec: Mapped[float] = mapped_column(Float, default=0.0)
    last_seen_sec: Mapped[float] = mapped_column(Float, default=0.0)
    duration_sec: Mapped[float] = mapped_column(Float, default=0.0)
    samples_seen: Mapped[int] = mapped_column(Integer, default=0)
    confidence_avg: Mapped[float] = mapped_column(Float, default=0.0)

    movement_index: Mapped[float] = mapped_column(Float, default=0.0)
    inactive_sec: Mapped[float] = mapped_column(Float, default=0.0)
    head_center_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    head_left_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    head_right_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    head_unknown_ratio: Mapped[float] = mapped_column(Float, default=1.0)

    attendance_state: Mapped[str] = mapped_column(String(24), default="unconfirmed")
    uncertain: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped[Session] = relationship(back_populates="tracks")
    attendance: Mapped[AttendanceRecord | None] = relationship(
        back_populates="track", uselist=False, cascade="all, delete-orphan", passive_deletes=True
    )


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    track_id: Mapped[str] = mapped_column(
        ForeignKey("participant_tracks.id", ondelete="CASCADE"), unique=True
    )
    roster_id: Mapped[str | None] = mapped_column(
        ForeignKey("roster_entries.id", ondelete="SET NULL"), nullable=True
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    presence_sec: Mapped[float] = mapped_column(Float, default=0.0)
    first_seen_sec: Mapped[float] = mapped_column(Float, default=0.0)
    last_seen_sec: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    uncertain: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[Session] = relationship(back_populates="attendance")
    track: Mapped[ParticipantTrack] = relationship(back_populates="attendance")


class AnalysisWindow(Base):
    __tablename__ = "analysis_windows"
    __table_args__ = (UniqueConstraint("session_id", "window_index", name="uq_window_session_index"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    window_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_sec: Mapped[float] = mapped_column(Float, nullable=False)
    end_sec: Mapped[float] = mapped_column(Float, nullable=False)

    participant_count: Mapped[int] = mapped_column(Integer, default=0)
    attendance_changes: Mapped[int] = mapped_column(Integer, default=0)
    movement_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    active_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    inactivity_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    looking_away_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    audio_active_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    engagement_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    engagement_confidence: Mapped[str | None] = mapped_column(String(16), nullable=True)
    data_quality: Mapped[str] = mapped_column(String(16), default="partial")
    warnings_json: Mapped[list] = mapped_column(JSON, default=list)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)

    session: Mapped[Session] = relationship(back_populates="windows")


class AudioInterval(Base):
    __tablename__ = "audio_intervals"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    start_sec: Mapped[float] = mapped_column(Float, nullable=False)
    end_sec: Mapped[float] = mapped_column(Float, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), default="speech")
    mean_energy: Mapped[float] = mapped_column(Float, default=0.0)

    session: Mapped[Session] = relationship(back_populates="audio_intervals")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(24), default="rule")
    category: Mapped[str] = mapped_column(String(48), default="engagement")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    observed: Mapped[str] = mapped_column(Text, nullable=False)
    interpretation: Mapped[str] = mapped_column(Text, nullable=False)
    start_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    confidence: Mapped[str] = mapped_column(String(16), default="low")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[Session] = relationship(back_populates="recommendations")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(24), default="queued")
    stage: Mapped[str] = mapped_column(String(48), default="queued")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[Session] = relationship(back_populates="jobs")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value_json: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class SystemEvent(Base):
    __tablename__ = "system_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    level: Mapped[str] = mapped_column(String(16), default="info")
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
