# Privacy & Security Audit — Docker Run (Local Only)

Status: VERIFIED (local trusted machine; no authentication by design)

- No biometric identification / face recognition / speaker ID introduced.
- No public media URLs; all storage under `data/sessions/` (volume-mounted).
- File upload validation: extension, size (default 512 MB), media probing (OpenCV/ffmpeg).
- Path traversal protected: session-id-based directories only; filenames replaced with UUIDs.
- Temporary file cleanup: upload validation uses temp files; cleaned on failure.
- Database: SQLite (`data/classmind.db`) with SQLAlchemy ORM; no raw SQL injection.
- CORS: limited to `localhost:5173` / `127.0.0.1:5173`.
- Error responses: structured (`code`, `message`, `detail`); no stack traces exposed.
- Secrets: no `.env` file; only `.env.example` template; no API keys / tokens in source.
- Dependencies: pinned in `requirements.txt`; `requirements-vision.txt` optional.
- No cloud AI dependency by default; optional local Ollama (`127.0.0.1:11434`) disabled.
- No telemetry / analytics / tracking.
- Data retention: configurable from Settings; media can be deleted after processing.
- Live camera: video-only (no microphone); local file storage; no external exposure.
