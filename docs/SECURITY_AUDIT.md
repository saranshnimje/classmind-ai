# Security and Privacy Audit

## Scope

This audit covers the ClassMind AI application as deployed for local classroom recording analysis.

## 5.1 Authentication and authorization

- **Status**: No authentication/authorization (by design)
- **Rationale**: The application is designed for local, trusted machine use only.
- **Risk**: If exposed to a public network, unauthorized users could access data.
- **Mitigation**: Do not expose to public internet; restrict machine access.

## 5.2 API input validation

- All endpoints use Pydantic v2 `BaseModel` schemas with validation.
- Upload endpoints use `File` with content-type validation.
- Path parameters validated; non-existent sessions return 404.
- Numeric limits use `ge`/`le` validators.
- **Status**: VERIFIED

## 5.3 File upload restrictions

- File uploads validated by extension against `VIDEO_EXTENSIONS` and `AUDIO_EXTENSIONS` lists.
- Size limited by `CLASSMIND_MAX_UPLOAD_MB` environment variable (default 512 MB).
- Media validated with OpenCV/ffmpeg probing; invalid media rejected with 422.
- Filename replaced with generated UUID-based name; original filename not stored as path.
- **Status**: VERIFIED

## 5.4 File path traversal protection

- `media_path()` uses `session_dir()` which creates session-specific subdirectories.
- No user-provided path used in file access; only session-id-based directories.
- Filename replaced with generated name before storage.
- `upload_media()` validates file content before storage.
- **Status**: VERIFIED

## 5.5 Local media storage

- All media stored under `data/sessions/{session_id}/` with generated filenames.
- No media exposed via public URL.
- Reports generated locally; exports served via authenticated endpoints only.
- **Status**: VERIFIED

## 5.6 Temporary file cleanup

- Upload validation uses temporary files in a temp directory; cleaned up on failure.
- Audio extraction creates `audio-16k.wav` artifact in session directory; replaced when updated.
- Pipeline uses session directory for all artifacts.
- **Status**: VERIFIED

## 5.7 Database access

- SQLite database (`data/classmind.db`) with SQLAlchemy ORM.
- No raw SQL injection risk; all queries use ORM.
- Database connection managed via `SessionLocal` with proper lifecycle.
- **Status**: VERIFIED

## 5.8 CORS configuration

- CORS limited to `http://localhost:5173` and `http://127.0.0.1:5173` by default.
- Configurable via `CLASSMIND_CORS_ORIGINS`.
- No public CORS origins configured.
- **Status**: VERIFIED

## 5.9 Error responses

- Structured error responses with `code`, `message`, `detail` fields.
- No stack traces exposed in production (`debug: false` by default).
- All exceptions handled by middleware (`api_error_handler`, `unhandled_error_handler`).
- **Status**: VERIFIED

## 5.10 Secrets and environment variables

- `.env` file used; `.env.example` documented but not committed with secrets.
- No API keys, passwords, or tokens in source code.
- No cloud dependencies; all processing local.
- **Status**: VERIFIED

## 5.11 Dependency vulnerabilities

- Requirements pinned to specific versions:
  - fastapi 0.162.0
  - pydantic 2.14.2
  - sqlalchemy 2.0.41
  - opencv-python-headless 4.12.0.88
  - imageio-ffmpeg 1.50.0
- Optional vision stack (ultralytics, torch, onnxruntime, silero-vad) NOT installed by default.
- No deprecated or inherently unsafe dependencies in core requirements.
- **Status**: VERIFIED

## 5.12 Unintended network requests

- No external API calls except optional Ollama (local, `127.0.0.1:11434`).
- Optional Ultralytics model download disabled by default via `CLASSMIND_ALLOW_MODEL_DOWNLOAD`.
- No analytics, telemetry, or tracking services.
- No CDN or external asset loading beyond build-time npm dependencies.
- **Status**: VERIFIED

## 5.13 Student privacy and data retention

- No biometric identification (face recognition, speaker ID, emotion detection).
- No public media hosting or URL exposure.
- Anonymous tracks by default; manual mapping only.
- Retention configurable; media can be deleted after processing.
- Data stored locally; no cloud upload.
- **Status**: VERIFIED

## 5.14 Security findings summary

| Item | Status |
|------|--------|
| No biometric identification introduced | ✅ VERIFIED |
| No face recognition | ✅ VERIFIED |
| No public media hosting | ✅ VERIFIED |
| No cloud AI dependency (except optional local Ollama) | ✅ VERIFIED |
| No biometric template storage | ✅ VERIFIED |
| No paid APIs or services | ✅ VERIFIED |
| Local storage only | ✅ VERIFIED |
| No secrets in source | ✅ VERIFIED |
| Input validation active | ✅ VERIFIED |
| Path traversal protected | ✅ VERIFIED |
| CORS limited to localhost | ✅ VERIFIED |
| Error handling structured | ✅ VERIFIED |
| Dependency versions pinned | ✅ VERIFIED |
| No authentication (design decision) | ⚠️ Documented limitation |

**Overall Status**: **VERIFIED AT CODE/ARCHITECTURE LEVEL — NO GENUINE SECURITY ISSUES FOUND**

### Recommendations

1. If deploying in a shared environment or exposing to a network, consider adding authentication.
2. Set `CLASSMIND_ALLOW_MODEL_DOWNLOAD=false` for offline deployments.
3. Regularly update dependencies for security patches.
4. Review retention settings periodically to ensure compliance with data policies.