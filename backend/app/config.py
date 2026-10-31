"""Application configuration.

All values can be overridden with CLASSMIND_* environment variables, e.g.
CLASSMIND_DATA_DIR=D:/classmind-data.  Defaults are local-first: nothing is
uploaded anywhere and no API key is required.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CLASSMIND_", env_file=".env", extra="ignore"
    )

    app_name: str = "ClassMind AI"
    app_version: str = "1.0.0"
    debug: bool = False

    # --- storage -----------------------------------------------------------
    data_dir: Path = Field(default=PROJECT_ROOT / "data")
    database_url: str | None = None

    max_upload_mb: int = 512
    max_media_duration_sec: float = 4 * 60 * 60
    min_media_duration_sec: float = 1.0

    # --- analysis defaults -------------------------------------------------
    sample_interval_sec: float = 2.0
    min_presence_sec: float = 30.0
    late_after_sec: float = 300.0
    window_sec: float = 300.0
    max_analysis_frames: int = 900
    analysis_max_width: int = 640
    vad_backend: str = "auto"  # auto | energy | silero

    # --- detector ----------------------------------------------------------
    detector_backend: str = "auto"  # auto | yolo | hog | none
    yolo_model: str = "yolov8n.pt"
    yolo_confidence: float = 0.35
    yolo_imgsz: int = 480
    allow_model_download: bool = True

    # --- optional local LLM ------------------------------------------------
    ollama_enabled: bool = False
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_sec: float = 60.0

    # --- live capture ------------------------------------------------------
    live_camera_index: int = 0
    live_max_seconds: float = 300.0

    # --- misc --------------------------------------------------------------
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("detector_backend")
    @classmethod
    def _valid_backend(cls, value: str) -> str:
        allowed = {"auto", "yolo", "hog", "none"}
        value = value.lower().strip()
        if value not in allowed:
            raise ValueError(f"detector_backend must be one of {sorted(allowed)}")
        return value

    @property
    def resolved_data_dir(self) -> Path:
        return Path(os.path.expanduser(str(self.data_dir))).resolve()

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{(self.resolved_data_dir / 'classmind.db').as_posix()}"

    @property
    def resolved_database_path(self) -> str:
        url = self.resolved_database_url
        if url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "", 1)
        return url

    def ensure_dirs(self) -> None:
        for sub in ("", "sessions", "temp", "models", "exports"):
            (self.resolved_data_dir / sub).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_config() -> AppConfig:
    cfg = AppConfig()
    cfg.ensure_dirs()
    return cfg
