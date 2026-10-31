"""Pydantic request/response schemas with validation."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AttendanceState = Literal["present", "late", "unconfirmed"]
SessionStatus = Literal["created", "uploaded", "queued", "processing", "completed", "failed"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------
# Sessions
# --------------------------------------------------------------------------
class SessionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    subject: str = Field(default="General", min_length=1, max_length=120)
    session_date: date = Field(default_factory=date.today)
    class_label: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=4000)
    sample_interval_sec: float | None = Field(default=None, ge=0.5, le=30)
    min_presence_sec: float | None = Field(default=None, ge=1, le=3600)
    late_after_sec: float | None = Field(default=None, ge=0, le=7200)
    window_sec: float | None = Field(default=None, ge=30, le=3600)

    @field_validator("title", "subject")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def _late_before_end(self) -> SessionCreate:
        return self


class JobOut(ORMModel):
    id: str
    status: str
    stage: str
    progress: float
    message: str | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class SessionOut(ORMModel):
    id: str
    title: str
    subject: str
    class_label: str | None
    session_date: date
    notes: str | None
    status: str
    error_message: str | None
    is_demo: bool
    duration_sec: float | None
    has_audio: bool
    video_filename: str | None
    audio_filename: str | None
    video_size_bytes: int | None
    audio_size_bytes: int | None
    fps: float | None
    width: int | None
    height: int | None
    sample_interval_sec: float
    min_presence_sec: float
    late_after_sec: float
    window_sec: float
    detector_used: str | None
    audio_method: str | None
    quality_json: dict[str, Any] = Field(default_factory=dict)
    methodology_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None
    attendance_count: int = 0
    track_count: int = 0
    average_engagement: float | None = None


class SessionDetail(SessionOut):
    latest_job: JobOut | None = None


class UploadOut(BaseModel):
    session_id: str
    status: str
    video_filename: str | None = None
    audio_filename: str | None = None
    duration_sec: float | None = None
    has_audio: bool = False
    size_bytes: int | None = None
    message: str


class StatusOut(BaseModel):
    session_id: str
    status: str
    error: str | None = None
    job: JobOut | None = None
    media_ready: bool = False
    progress: float = 0.0
    stage: str | None = None
    message: str | None = None


class ProcessOut(BaseModel):
    session_id: str
    status: str
    job_id: str
    message: str


class LiveStartIn(BaseModel):
    camera_index: int | None = Field(default=None, ge=0, le=10)
    max_seconds: float = Field(default=300, ge=5, le=1800)
    auto_process: bool = True


# --------------------------------------------------------------------------
# Attendance
# --------------------------------------------------------------------------
class TrackOut(ORMModel):
    id: str
    track_index: int
    display_label: str
    roster_id: str | None
    identity_status: str
    first_seen_sec: float
    last_seen_sec: float
    duration_sec: float
    samples_seen: int
    confidence_avg: float
    movement_index: float
    inactive_sec: float
    head_center_ratio: float
    head_left_ratio: float
    head_right_ratio: float
    head_unknown_ratio: float
    attendance_state: str
    uncertain: bool
    note: str | None


class AttendanceOut(ORMModel):
    id: str
    track_id: str
    roster_id: str | None
    display_name: str
    state: str
    presence_sec: float
    first_seen_sec: float
    last_seen_sec: float
    confidence: float
    uncertain: bool
    note: str | None


class AttendanceSummary(BaseModel):
    session_id: str
    session_duration_sec: float | None
    min_presence_sec: float
    late_after_sec: float
    total_detected: int
    present: int
    late: int
    unconfirmed: int
    mapped: int
    anonymous: int
    uncertain: int
    attendance_rate: float | None = Field(
        None, description="(present + late) / total detected participants, percent"
    )
    records: list[AttendanceOut]
    tracks: list[TrackOut]
    warnings: list[str] = Field(default_factory=list)


class RosterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    external_id: str | None = Field(default=None, max_length=64)
    class_label: str | None = Field(default=None, max_length=120)


class RosterOut(ORMModel):
    id: str
    name: str
    external_id: str | None
    class_label: str | None
    created_at: datetime


class TrackMappingIn(BaseModel):
    roster_id: str | None = Field(
        None, description="Roster entry id, or null to remove an existing mapping"
    )
    confirm_manual: bool = Field(
        default=False,
        description="Explicitly confirm this is a manual, approximate mapping (required)",
    )


# --------------------------------------------------------------------------
# Analytics
# --------------------------------------------------------------------------
class WindowOut(ORMModel):
    window_index: int
    start_sec: float
    end_sec: float
    participant_count: int
    attendance_changes: int
    movement_index: float | None
    active_ratio: float | None
    inactivity_ratio: float | None
    looking_away_ratio: float | None
    audio_active_ratio: float | None
    engagement_score: float | None
    engagement_confidence: str | None
    data_quality: str
    warnings_json: list[str]
    metrics_json: dict[str, Any]


class AudioIntervalOut(ORMModel):
    start_sec: float
    end_sec: float
    kind: str
    mean_energy: float


class AudioSummary(BaseModel):
    available: bool
    method: str | None = None
    speech_active_sec: float = 0.0
    speech_ratio: float | None = None
    interval_count: int = 0
    intervals: list[AudioIntervalOut] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AnalyticsOut(BaseModel):
    session_id: str
    title: str
    duration_sec: float | None
    window_sec: float
    average_engagement: float | None
    engagement_confidence: str | None
    peak_window: int | None
    lowest_window: int | None
    windows: list[WindowOut]
    audio: AudioSummary
    movement_summary: dict[str, Any]
    attendance_summary: dict[str, Any]
    quality: dict[str, Any]
    methodology: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Recommendations
# --------------------------------------------------------------------------
class RecommendationOut(ORMModel):
    id: str
    source: str
    category: str
    title: str
    detail: str
    evidence: str
    observed: str
    interpretation: str
    start_sec: float | None
    end_sec: float | None
    priority: str
    confidence: str
    created_at: datetime


class RecommendationResponse(BaseModel):
    session_id: str
    generated_by: str
    llm_available: bool
    llm_status: str
    disclaimer: str
    recommendations: list[RecommendationOut]


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------
class SettingsOut(BaseModel):
    min_presence_sec: float
    sample_interval_sec: float
    window_sec: float
    late_after_sec: float
    detector_backend: str
    ollama_enabled: bool
    ollama_url: str
    ollama_model: str
    retention_days: int
    delete_media_after_processing: bool
    data_dir: str
    database_path: str
    models: dict[str, Any]
    limits: dict[str, Any]


class SettingsUpdate(BaseModel):
    min_presence_sec: float | None = Field(default=None, ge=1, le=3600)
    sample_interval_sec: float | None = Field(default=None, ge=0.5, le=30)
    window_sec: float | None = Field(default=None, ge=30, le=3600)
    late_after_sec: float | None = Field(default=None, ge=0, le=7200)
    detector_backend: Literal["auto", "yolo", "hog", "none"] | None = None
    ollama_enabled: bool | None = None
    ollama_url: str | None = Field(default=None, max_length=300)
    ollama_model: str | None = Field(default=None, max_length=120)
    retention_days: int | None = Field(default=None, ge=0, le=3650)
    delete_media_after_processing: bool | None = None

    @field_validator("ollama_url")
    @classmethod
    def _url_scheme(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip().rstrip("/")
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("ollama_url must start with http:// or https://")
        return value


# --------------------------------------------------------------------------
# Dashboard / health / misc
# --------------------------------------------------------------------------
class HealthOut(BaseModel):
    status: str
    app: str
    version: str
    database: str
    data_dir_writable: bool
    processing_active: bool
    detector: dict[str, Any]
    audio_vad: dict[str, Any]
    llm: dict[str, Any]
    ffmpeg: dict[str, Any]
    timestamp: datetime


class EventOut(ORMModel):
    id: str
    level: str
    event: str
    message: str
    session_id: str | None
    created_at: datetime


class DashboardSession(BaseModel):
    id: str
    title: str
    subject: str
    class_label: str | None
    session_date: date
    status: str
    duration_sec: float | None
    is_demo: bool
    created_at: datetime
    attendance_rate: float | None
    average_engagement: float | None
    error_message: str | None


class DashboardOut(BaseModel):
    total_sessions: int
    completed_sessions: int
    total_attendance_records: int
    average_attendance_rate: float | None
    average_engagement: float | None
    sessions_last_14_days: list[dict[str, Any]]
    engagement_trend: list[dict[str, Any]]
    recent_sessions: list[DashboardSession]
    recent_events: list[EventOut]
    processing: dict[str, Any]
    models: dict[str, Any]
    definitions: dict[str, str]


class ReportOut(BaseModel):
    session: SessionOut
    generated_at: datetime
    attendance: AttendanceSummary
    analytics: AnalyticsOut
    recommendations: list[RecommendationOut]
    quality: dict[str, Any]
    methodology: dict[str, Any]
    limitations: list[str]


class MessageOut(BaseModel):
    message: str
    detail: str | None = None
