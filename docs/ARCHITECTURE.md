# Architecture

This document describes how ClassMind AI moves data from an uploaded recording to
attendance, analytics, recommendations, and reports.

## High-level components

```
┌────────────────────────────────────────────────────────────────────┐
│ React SPA (Vite, TypeScript, Tailwind, Recharts)                   │
│ Dashboard · Sessions · Session analysis · Attendance · Analytics   │
│ Recommendations · Settings · About/Privacy                         │
└───────────────────────────────┬────────────────────────────────────┘
                                │ JSON / multipart over /api
┌───────────────────────────────▼────────────────────────────────────┐
│ FastAPI application                                                │
│  routers: health, dashboard, sessions, attendance, analytics,      │
│           settings, demo                                           │
│  services: storage, media, vision, audio, analytics, attendance,   │
│            recommend, report, pipeline, demo, events, live         │
└───────────────────────────────┬────────────────────────────────────┘
                                │ SQLAlchemy
┌───────────────────────────────▼────────────────────────────────────┐
│ SQLite database + local filesystem                                 │
│  data/classmind.db                                                 │
│  data/sessions/<session_id>/  (media, extracted audio)             │
│  data/exports/                (generated exports, if used)         │
│  data/models/                 (YOLO weights)                       │
└────────────────────────────────────────────────────────────────────┘
```

The backend can serve the built SPA from `frontend/dist`, so production use needs only
one process and one port.

## Request lifecycle

1. **Create session** — `POST /api/sessions` stores metadata and per-session analysis
   thresholds.
2. **Upload** — `POST /api/sessions/{id}/upload` accepts a video and/or audio file.
   Files are streamed to a temporary location, size/extension checked, probed with
   OpenCV/ffmpeg, then moved into the session directory. A failed validation removes the
   temporary file and leaves existing media untouched.
3. **Process** — `POST /api/sessions/{id}/process` creates a persisted job and starts the
   background pipeline. The API returns `202` immediately.
4. **Poll** — `GET /api/sessions/{id}/status` reports status, stage, progress, and errors.
5. **Read results** — attendance, analytics, recommendations, and reports are read from
   SQLite. No recomputation happens on read.
6. **Export** — JSON/CSV/HTML reports are generated on demand from persisted results.

## Processing pipeline

`backend/app/services/pipeline.py` runs these stages:

1. **Validate** — media exists, metadata probe, duration/fps/dimensions.
2. **Audio extraction** — ffmpeg converts the audio source to 16 kHz mono WAV.
3. **Vision** — sample frames at `sample_interval_sec`, resize to `analysis_max_width`,
   detect people, track across samples, derive movement/head/face proxies.
4. **Audio analysis** — VAD produces speech-active intervals.
5. **Attendance** — sustained-presence rules classify each track.
6. **Window analytics** — aggregate observations and audio into windows.
7. **Recommendations** — rule engine (and optional Ollama) produces evidence-linked
   suggestions.
8. **Persist** — replace previous tracks/windows/attendance/recommendations atomically,
   store quality and methodology JSON, mark the session completed.

Failures set the session and job to `failed` with a readable message; results are not
partially exposed as complete.

### Sampling and detection

- Default sample interval: 2 s. Default analysis width: 640 px. Default frame cap: 900.
- **YOLO** (optional): Ultralytics YOLOv8n, person class only, CPU by default.
- **HOG** (built in): OpenCV HOG + SVM people detector.
- **None**: detection disabled; audio-only analytics still work.

### Tracking

Detections are associated across samples with:

- greedy IoU matching, then
- centre-distance fallback for fast motion,
- post-hoc fragment stitching for short gaps.

Tracks are anonymous. The tracker does not use faces, appearance embeddings, or
biometrics.

### Head/face proxies

A frontal-face Haar cascade is run inside each person box. The face centre relative to
the box gives a coarse `center`/`left`/`right`/`unknown` label. This is **not** gaze
tracking and is often unknown, especially in wide classroom shots.

## Attendance rules

For each track:

- `presence_sec` = observed span (last seen − first seen).
- If `presence_sec < min_presence_sec` → **unconfirmed**.
- Else if `first_seen_sec >= late_after_sec` → **late**.
- Else → **present**.

Attendance rate = `(present + late) / total_detected`, expressed as a percentage.
`total_detected` is the number of tracks, not the number of enrolled students. Tracks
can fragment, so the count is an estimate and is accompanied by warnings.

Manual mapping changes the display name and roster link only; it does not change the
observed presence values.

## Engagement proxy

For each window, available signals are combined:

```
visual = 0.6 * active_ratio + 0.4 * movement_index
audio  = min(1, audio_active_ratio / 0.6)
score  = 0.65 * visual + 0.35 * audio   (when both exist)
```

If one signal is missing, the available component is used with renormalised weights. If
neither exists, the score is `null`; it is never set to zero. Confidence is `high`,
`medium`, or `low` based on signal coverage, observation count, and participant count.

`methodology_json` stores the exact definition, formula, thresholds, and confidence rules
shown in the UI and reports.

## Data model

Core tables:

- `sessions` — metadata, thresholds, status, media filenames, quality/methodology JSON.
- `processing_jobs` — status, stage, progress, message, timestamps.
- `participant_tracks` — anonymous track observations and derived proxies.
- `attendance_records` — per-track state, presence, confidence, optional roster mapping.
- `analysis_windows` — per-window metrics, confidence, quality, warnings.
- `audio_intervals` — speech/silence intervals and mean energy.
- `recommendations` — source, category, evidence, observed, interpretation, interval.
- `roster_entries` — optional names/external IDs for manual mapping.
- `app_settings` — persisted preferences.
- `events` — recent operational events for the dashboard.

## Frontend

- Route-scoped pages use `/attendance/:id`, `/analytics/:id`, `/recommendations/:id`;
  base routes show a session picker.
- Pages are lazy-loaded with `React.lazy`/`Suspense`.
- Shared chart code is split into a `charts` chunk.
- The API client is typed and maps structured errors to `ApiError`.
- Theme preference and last-opened session are stored locally in the browser.

## Security and safety boundaries

- Uploaded filenames are replaced with generated names; path traversal is rejected.
- Uploads are size-limited and extension-checked, then probed as real media.
- The SPA fallback only serves files inside `frontend/dist`.
- API responses set `nosniff`, `SAMEORIGIN`, `no-referrer`, and `no-store` for `/api`.
- CORS is limited to the local Vite origins by default.
- There is no authentication because the app is intended to run on a trusted local
  machine. Do not expose it directly to the public internet.
