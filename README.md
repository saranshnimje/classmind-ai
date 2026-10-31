# ClassMind AI — Multimodal Attendance & Engagement Agent

ClassMind AI is a **local-first classroom analysis application**. It turns a recorded
classroom video (and optionally a separate audio track) into anonymous attendance
estimates, windowed engagement proxies, data-quality notes, evidence-linked teaching
suggestions, and exportable reports.

Everything runs on the machine that hosts the backend. There is **no face recognition,
no speaker identification, no emotion detection, no demographic inference, no cloud AI
API, and no public media URL**. Detected people stay anonymous unless a teacher
explicitly maps a track to a roster entry.

> Engagement is a **descriptive proxy** built from observable signals (movement, active
> presence, speech activity). It is not a validated measure of attention, learning,
> teaching quality, or student behaviour, and must not be used for grading or discipline.

---

## Contents

- [What it does](#what-it-does)
- [Screens](#screens)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Quick start](#quick-start)
- [Using the app](#using-the-app)
- [Configuration](#configuration)
- [API](#api)
- [Testing](#testing)
- [Demo data](#demo-data)
- [Privacy and ethics](#privacy-and-ethics)
- [Limitations](#limitations)
- [Troubleshooting](#troubleshooting)
- [Project structure](#project-structure)
- [Verification status](#verification-status)

---

## What it does

### Attendance (anonymous by default)
- Detects **people**, not faces or identities, using YOLO (optional extra) or OpenCV HOG.
- Tracks detections across sampled frames with IoU/centre-distance matching and
  fragment stitching.
- Applies **sustained-presence rules**:
  - **Present** — observed for at least the configured minimum presence time.
  - **Late** — first observed after the configured late threshold.
  - **Unconfirmed** — visible, but not long enough to classify confidently.
- Exposes a roster for **manual** track-to-student mapping. Mapping is never automatic.
- Shows warnings when tracks are short, fragmented, or otherwise uncertain.

### Engagement analytics
- Splits the recording into configurable windows (default 300 s).
- Computes a transparent proxy from available signals:
  - movement index (frame-difference / track displacement),
  - active presence ratio,
  - speech-active ratio from local VAD.
- **Missing data is excluded, never scored as zero.** Confidence drops when a signal is
  unavailable.
- Reports per-window quality, confidence, warnings, and the exact methodology used.
- Includes a head-orientation proxy from frontal-face position (approximate, frequently
  `unknown`; not gaze tracking).

### Audio
- Extracts a 16 kHz mono track with the bundled ffmpeg.
- Uses **Silero VAD** automatically when installed, otherwise a NumPy energy VAD.
- Produces speech-active intervals and a speech ratio.
- Handles audio-only sessions and missing audio gracefully.

### Recommendations
- Deterministic, rule-based suggestions derived from observed windows and attendance.
- Each suggestion includes **evidence**, an **interval**, **observed** values, and a
  separate **interpretation** so the inference is not presented as fact.
- Optional local **Ollama** support; if unreachable or disabled, rules are used and the
  source is labelled.
- Never generates advice about individual students.

### Reports and operations
- JSON, CSV, HTML report, and attendance CSV exports.
- Persistent SQLite database.
- Background processing with progress/status polling.
- Retention policy and optional media deletion after processing.
- Dashboard with aggregate metrics, trends, recent sessions, and processing state.
- Simulated demo dataset, always labelled as demo data.

---

## Screens

The React app includes:

1. **Dashboard** — aggregate metrics, trends, recent sessions/events, demo controls.
2. **Sessions** — searchable/filterable session list with status and metrics.
3. **Create session** — metadata and per-session analysis overrides.
4. **Session analysis** — upload, validation, progress polling, results summary,
   reports, optional live capture.
5. **Attendance** — counts, warnings, anonymous tracks, manual mapping, roster CRUD.
6. **Analytics** — window charts, detail table, audio timeline, methodology, quality.
7. **Recommendations** — evidence-linked suggestions with filters and source labels.
8. **Settings** — analysis defaults, detector/model status, retention, Ollama status.
9. **About / Privacy** — method notes, privacy and ethical-use guidance.

---

## Architecture

```
React + Vite + TypeScript + Tailwind + Recharts
                    │  /api (JSON, multipart)
                    ▼
              FastAPI (Python 3.12)
        ┌───────────┼────────────┐
        │           │            │
   SQLAlchemy    Services     Static SPA
     SQLite     (vision,      (frontend/dist)
                 audio,
                 analytics,
                 attendance,
                 recommend,
                 report)
                    │
             Local data directory
        (media, SQLite DB, exports, models)
```

- **Backend:** FastAPI, Pydantic v2, SQLAlchemy 2, SQLite.
- **Vision:** OpenCV; optional Ultralytics YOLO + PyTorch CPU.
- **Audio:** ffmpeg (via `imageio-ffmpeg`), NumPy energy VAD, optional Silero VAD.
- **Frontend:** React 19, Vite 7, TypeScript, Tailwind CSS, Recharts, Lucide.
- **Processing:** background thread/worker abstraction with a persisted job row.

More detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Requirements

- **Python 3.12** recommended (3.11+). Python 3.14 may not have wheels for the optional
  PyTorch/YOLO stack.
- **Node.js 20+** and npm (tested with Node 24).
- **ffmpeg** is bundled through `imageio-ffmpeg`; a system ffmpeg is not required.
- Optional: a webcam for live capture.
- Optional: [Ollama](https://ollama.com/) for local LLM suggestions.
- No GPU required. YOLO CPU inference is supported but slower.

### Python dependencies

| File | Purpose |
| --- | --- |
| `backend/requirements.txt` | Core runtime (FastAPI, OpenCV headless, NumPy, ffmpeg helper). |
| `backend/requirements-dev.txt` | Core + pytest, coverage, httpx, ruff. |
| `backend/requirements-vision.txt` | Optional YOLO + PyTorch CPU + Silero VAD (large download). |

The app works with core dependencies only: OpenCV HOG detection and energy VAD are
built in.

---

## Quick start

### 1. Create a virtual environment

PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend/requirements-dev.txt
```

With `uv`:

```powershell
uv venv --python 3.12
uv pip install --python .venv\Scripts\python.exe -r backend/requirements-dev.txt
```

Optional vision stack (YOLO + Silero):

```powershell
pip install -r backend/requirements-vision.txt
```

### 2. Run the backend

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

- API docs: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/api/health>

### 3. Run the frontend (development)

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` to `127.0.0.1:8000`.

### 4. Or build the frontend for single-server use

```powershell
cd frontend
npm run build
```

The backend serves `frontend/dist` at <http://127.0.0.1:8000>. Deep links fall back to
`index.html`, so the SPA works without a separate web server.

### 5. Optional: Docker Compose

A `Dockerfile` and `docker-compose.yml` are included for the **core** stack (HOG +
energy VAD). The image is not built or verified in the development environment used for
this project; treat Docker as an optional convenience.

```powershell
docker compose up --build
```

Open <http://127.0.0.1:8000>. Data persists in `./data`.

---

## Using the app

1. **Create a session** with a title, subject, class label, date, and optional analysis
   overrides.
2. **Upload** a classroom video and/or a separate audio file. Files are validated by
   extension, size, and media probing.
3. **Run analysis.** Processing happens in the background; the page polls status and
   progress.
4. **Review attendance.** Tracks are anonymous. If you want names, map a track to a
   roster entry and confirm the mapping.
5. **Review analytics.** Inspect windows, charts, audio intervals, methodology, and
   quality warnings.
6. **Review recommendations.** Each suggestion shows its evidence, interval, observed
   values, interpretation, priority, confidence, and source.
7. **Export** the HTML report, report CSV, or attendance CSV.

Supported extensions and limits are configurable; defaults include `.mp4`, `.mov`,
`.avi`, `.mkv`, `.webm`, `.wav`, `.mp3`, and more.

### Recorded-media end-to-end check (manual)

With the backend running and a short video/audio pair:

```powershell
$body = @{ title='E2E lesson'; subject='Science'; session_date='2026-10-31' } | ConvertTo-Json
$s = Invoke-RestMethod -Uri http://127.0.0.1:8000/api/sessions -Method Post -ContentType 'application/json' -Body $body
curl.exe -s -X POST "http://127.0.0.1:8000/api/sessions/$($s.id)/upload" -F "video=@lesson.mp4" -F "audio=@lesson.wav"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/sessions/$($s.id)/process" -Method Post
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/sessions/$($s.id)/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/sessions/$($s.id)/analytics"
```

---

## Configuration

Configuration is read from environment variables prefixed with `CLASSMIND_`, and from a
`.env` file in the repository root. See [`.env.example`](.env.example).

| Variable | Default | Description |
| --- | --- | --- |
| `CLASSMIND_DATA_DIR` | `./data` | Database, uploaded media, exports, model weights. |
| `CLASSMIND_DATABASE_URL` | SQLite in data dir | Override the SQLAlchemy URL. |
| `CLASSMIND_SAMPLE_INTERVAL_SEC` | `2.0` | Frame sampling interval. |
| `CLASSMIND_MIN_PRESENCE_SEC` | `30` | Minimum observed presence for **Present**. |
| `CLASSMIND_LATE_AFTER_SEC` | `300` | First-seen threshold for **Late**. |
| `CLASSMIND_WINDOW_SEC` | `300` | Analytics window length. |
| `CLASSMIND_MAX_ANALYSIS_FRAMES` | `900` | Safety cap on sampled frames. |
| `CLASSMIND_ANALYSIS_MAX_WIDTH` | `640` | Frames are resized before detection. |
| `CLASSMIND_DETECTOR_BACKEND` | `auto` | `auto`, `yolo`, `hog`, or `none`. |
| `CLASSMIND_YOLO_MODEL` | `yolov8n.pt` | Weight name; resolved from `data/models`. |
| `CLASSMIND_YOLO_CONFIDENCE` | `0.35` | YOLO person confidence threshold. |
| `CLASSMIND_YOLO_IMGSZ` | `480` | YOLO inference size. |
| `CLASSMIND_ALLOW_MODEL_DOWNLOAD` | `true` | Allow Ultralytics to fetch weights once. |
| `CLASSMIND_VAD_BACKEND` | `auto` | `auto`, `energy`, or `silero`. |
| `CLASSMIND_OLLAMA_ENABLED` | `false` | Enable optional local LLM suggestions. |
| `CLASSMIND_OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama endpoint. |
| `CLASSMIND_OLLAMA_MODEL` | `llama3.2` | Ollama model name. |
| `CLASSMIND_MAX_UPLOAD_MB` | `512` | Per-file upload limit. |
| `CLASSMIND_MAX_MEDIA_DURATION_SEC` | `14400` | Maximum accepted media duration. |
| `CLASSMIND_LOG_LEVEL` | `INFO` | Python logging level. |

Persisted preferences (analysis defaults, detector backend, Ollama settings, retention)
are managed from the **Settings** page and stored in SQLite. Environment values provide
the initial defaults.

### Model weights and offline use

- Place `yolov8n.pt` in `data/models/` to avoid a first-use download.
- Set `CLASSMIND_ALLOW_MODEL_DOWNLOAD=false` to enforce fully offline operation.
- Without YOLO, select `hog` or leave `auto`: HOG works with core dependencies only.

---

## API

All endpoints are under `/api`. Interactive docs are at `/docs`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | App, database, detector, VAD, ffmpeg, LLM status. |
| `GET` | `/dashboard` | Aggregate metrics, trends, recent events, processing state. |
| `GET` | `/sessions` | List sessions (`status`, `q`, `include_demo` filters). |
| `POST` | `/sessions` | Create a session. |
| `GET` | `/sessions/{id}` | Session detail and latest job. |
| `DELETE` | `/sessions/{id}` | Delete session, media, and results. |
| `POST` | `/sessions/{id}/upload` | Upload video and/or audio (multipart). |
| `POST` | `/sessions/{id}/process` | Queue analysis. |
| `GET` | `/sessions/{id}/status` | Job progress and stage. |
| `GET` | `/sessions/{id}/attendance` | Attendance summary, records, tracks. |
| `GET` | `/sessions/{id}/attendance.csv` | Attendance CSV export. |
| `POST` | `/sessions/{id}/attendance/{track_id}/map` | Manually map/unmap a track. |
| `GET` | `/sessions/{id}/analytics` | Windows, audio, quality, methodology. |
| `GET` | `/sessions/{id}/recommendations` | Evidence-linked suggestions. |
| `GET` | `/sessions/{id}/report` | Full JSON report. |
| `GET` | `/sessions/{id}/report.html` | Printable HTML report (`?download=true`). |
| `GET` | `/sessions/{id}/report.csv` | Report CSV. |
| `POST` | `/sessions/{id}/live/start` | Optional live camera capture. |
| `POST` | `/sessions/{id}/live/stop` | Stop live capture. |
| `GET` | `/sessions/{id}/live/status` | Live capture status. |
| `GET`/`POST` | `/roster` | List/create roster entries. |
| `DELETE` | `/roster/{id}` | Delete a roster entry. |
| `GET`/`PUT` | `/settings` | Read/update persisted preferences. |
| `GET` | `/settings/models` | Detector, VAD, and Ollama availability. |
| `POST` | `/settings/retention/apply` | Apply retention now. |
| `POST` | `/demo/seed` | Create a labelled simulated demo session. |
| `DELETE` | `/demo` | Remove all demo sessions. |

Errors use a consistent shape:

```json
{ "error": { "code": "invalid_media", "message": "...", "detail": null } }
```

---

## Testing

### Backend

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Coverage includes storage safety, media validation, audio VAD, attendance rules,
window analytics, recommendations, settings/retention, API errors, and a recorded-media
workflow with real codec decoding and a deterministic mocked detector.

### Frontend

```powershell
cd frontend
npm test          # Vitest + Testing Library
npm run typecheck # tsc --noEmit
npm run build     # production build
```

### Real-detector verification

Real YOLO inference was run on the OpenCV `vtest.avi` sample with CPU PyTorch. It is
slow (roughly seconds per sampled frame at `imgsz=480` on the verification machine), so
use a sensible sample interval and short recordings for interactive testing. Track
fragmentation can occur on crowded footage; the app reports quality warnings rather than
hiding this.

---

## Demo data

`POST /api/demo/seed` (or **Load demo data** on the dashboard) creates a scripted,
simulated session. It is explicitly labelled `Demo data — simulated` in the UI and in
reports. It does **not** run inference and must not be presented as real classroom
evidence. Use **Clear demo data** to remove all demo sessions.

---

## Privacy and ethics

- **Local only.** Media and results are stored under `data/`; no upload to a cloud
  service, no telemetry, no API keys.
- **Anonymous by default.** No face recognition, biometric templates, speaker
  identification, emotion detection, or demographic classification.
- **Manual identity mapping only.** A teacher may map a track to a roster entry; the
  app records that the mapping is manual and uncertain.
- **Proxy, not assessment.** Engagement is a coarse descriptive signal. It is not
  attention, comprehension, learning, or teaching quality.
- **Missing data is unknown.** No audio or no usable video never means low engagement.
- **Human judgement required.** Recommendations are decision support, not verdicts.
- **Retention controls.** Configure retention days and optional media deletion.
- **Consent and policy.** Obtain appropriate consent and follow your institution's
  policies before recording a classroom.

See [`docs/PRIVACY_AND_ETHICS.md`](docs/PRIVACY_AND_ETHICS.md) for the full statement.

---

## Limitations

- Person detection does not establish identity; tracks are approximate and may split,
  merge, or disappear.
- Attendance reflects who was **visible and trackable**, not who was physically present.
- Head orientation is a frontal-face-position proxy, not gaze tracking; it is often
  unknown.
- Movement and speech activity are coarse; teacher speech is not distinguished from
  student speech.
- Occlusion, low light, camera motion, small faces, and crowded rooms reduce reliability.
- YOLO CPU inference is slow; sampling and image size trade accuracy for speed.
- Live camera capture depends on hardware and has not been verified on every platform.
- Ollama suggestions depend on a locally running model; rules are the fallback.
- The app does not replace direct observation or professional judgement.

See [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

---

## Troubleshooting

Common issues:

- **`ModuleNotFoundError` / wheel errors** — use Python 3.12 and reinstall requirements.
- **YOLO unavailable** — install `requirements-vision.txt`, or use `hog`; place weights
  in `data/models/` for offline use.
- **Slow analysis** — increase `sample_interval_sec`, reduce `max_analysis_frames`, or
  use a shorter clip.
- **No audio detected** — check the file has an audio stream; audio-only sessions are
  supported.
- **Frontend cannot reach API** — run the backend on port 8000 and use the Vite dev
  server, or build the frontend so the backend serves it.
- **Port already in use** — stop the other process or choose another port.
- **Permission denied on data directory** — set `CLASSMIND_DATA_DIR` to a writable path.

Full guide: [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md).

---

## Project structure

```
ClassMind AI/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, SPA serving, lifespan
│   │   ├── config.py            # env-driven settings
│   │   ├── database.py          # SQLAlchemy engine/session
│   │   ├── models.py            # ORM models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── serializers.py       # ORM -> API payloads
│   │   ├── errors.py            # structured API errors
│   │   ├── routers/             # health, sessions, attendance, analytics, ...
│   │   └── services/            # media, vision, audio, analytics, attendance,
│   │                            # recommend, report, pipeline, demo, storage
│   ├── tests/                   # pytest suite
│   └── requirements*.txt
├── frontend/
│   ├── src/
│   │   ├── pages/               # 9 pages + NotFound
│   │   ├── components/          # layout, UI, charts, session picker
│   │   ├── lib/                 # API client, types, formatting, hooks
│   │   └── test/                # fixtures and setup
│   ├── package.json
│   └── vite.config.ts
├── data/                        # local runtime data (gitignored)
├── docs/                        # architecture, privacy, limitations, troubleshooting
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── pytest.ini
└── README.md
```

---

## Verification status

Verified on the development machine (Windows, Python 3.12.13, Node 24.19.0):

| Area | Status | Evidence |
| --- | --- | --- |
| Backend automated tests | **DONE** | 60 tests pass (`pytest`). |
| Frontend automated tests | **DONE** | 42 tests pass across 10 files (`vitest`). |
| TypeScript typecheck | **DONE** | `tsc --noEmit` passes. |
| Production frontend build | **DONE** | `vite build` succeeds; code-split chunks emitted. |
| Real recorded-media pipeline | **DONE** | 12 s MP4 + speech WAV: YOLO detection, tracking, attendance, 1 window, Silero speech intervals, recommendations, JSON/CSV/HTML reports. |
| Live UI verification | **DONE** | Dashboard and analytics rendered against the live backend with no console errors. |
| Optional live camera capture | **NOT VERIFIED** | Requires camera hardware; endpoint/scaffolding exists. |
| Docker image | **NOT VERIFIED** | Files provided; image was not built in this environment. |
| Ollama suggestions | **NOT VERIFIED** | Optional local model was not running; rule fallback verified. |

Demo sessions are simulated and are not included in the inference claims above.

---

## License / attribution

This project was built as a SkillWallet "Generative AI with Google Cloud" submission.
It uses open-source libraries (FastAPI, OpenCV, Ultralytics YOLO, Silero VAD, React,
Recharts, Tailwind CSS, Lucide). Review each dependency's license before redistribution.
