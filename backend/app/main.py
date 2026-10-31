"""FastAPI application entry point.

Run from the repository root:
    .venv/Scripts/python -m uvicorn backend.app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import PROJECT_ROOT, get_config
from .database import SessionLocal, init_db
from .errors import (
    ApiError,
    api_error_handler,
    error_payload,
    http_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from .routers import analytics, attendance, dashboard, demo, health, sessions, settings
from .services.events import log_event
from .services.live import live_manager
from .services.pipeline import pipeline, recover_interrupted_jobs
from .services.settings_service import apply_retention, load_preferences_into_config

cfg = get_config()
logging.basicConfig(
    level=getattr(logging, cfg.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("classmind")

FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        load_preferences_into_config(db)
        recover_interrupted_jobs()
        removed = apply_retention(db)
        log_event(
            db,
            "info",
            "app_started",
            "ClassMind AI started locally."
            + (f" Retention removed {removed} old session(s)." if removed else ""),
        )
    finally:
        db.close()
    logger.info("ClassMind AI ready (data dir: %s)", cfg.resolved_data_dir)
    try:
        yield
    finally:
        live_manager.stop_all()
        pipeline.shutdown()
        logger.info("ClassMind AI stopped")


app = FastAPI(
    title="ClassMind AI — Multimodal Attendance & Engagement Agent",
    description=(
        "Privacy-preserving local classroom analysis. All media is processed on this machine. "
        "Detected people remain anonymous until a teacher explicitly maps them to a roster. "
        "Engagement values are descriptive proxies, not assessments of students."
    ),
    version=cfg.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(StarletteHTTPException, http_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.url.path.startswith("/api"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


for module in (health, dashboard, sessions, attendance, analytics, settings, demo):
    app.include_router(module.router, prefix="/api")


@app.get("/api", include_in_schema=False)
def api_root() -> dict:
    return {
        "app": cfg.app_name,
        "version": cfg.app_version,
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str):
    # Production backend-only mode: prevent serving React SPA at root
    if os.environ.get("CLASSMIND_BACKEND_ONLY") == "true" and (full_path == "" or full_path == "/"):
        return JSONResponse(
            status_code=200,
            content={
                "service": "ClassMind AI backend",
                "status": "running",
                "docs": "/docs",
                "health": "/api/health",
                "version": cfg.app_version,
            },
        )
    if full_path.startswith("api"):
        return JSONResponse(
            status_code=404, content=error_payload("not_found", "API endpoint not found")
        )

    if FRONTEND_DIST.exists():
        candidate = (FRONTEND_DIST / full_path).resolve()
        if full_path and FRONTEND_DIST.resolve() in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(index)

    return HTMLResponse(
        status_code=200,
        content=f"""<!doctype html><html><head><meta charset="utf-8">
<title>ClassMind AI</title>
<style>body{{font-family:system-ui,Segoe UI,sans-serif;max-width:720px;margin:64px auto;padding:0 24px;color:#1f2937;line-height:1.6}}
code{{background:#f3f4f6;padding:2px 6px;border-radius:4px}}a{{color:#4338ca}}</style></head>
<body><h1>ClassMind AI backend is running</h1>
<p>The React frontend has not been built yet, or <code>frontend/dist</code> is missing.</p>
<ol>
<li>API docs: <a href="/docs">/docs</a></li>
<li>Health: <a href="/api/health">/api/health</a></li>
<li>Development UI: <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run dev</code> (http://localhost:5173)</li>
<li>Production build: <code>cd frontend &amp;&amp; npm run build</code>, then reload this page.</li>
</ol>
<p>Data directory: <code>{cfg.resolved_data_dir}</code></p>
</body></html>""",
    )
