# Troubleshooting

## Setup and installation

### Python version or wheel errors

Use **Python 3.12** (3.11+ should work). Python 3.14 may not have wheels for
`torch`, `torchvision`, or `ultralytics`.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend/requirements-dev.txt
```

Check:

```powershell
.\.venv\Scripts\python.exe --version
```

### `uv` installation

```powershell
uv venv --python 3.12
uv pip install --python .venv\Scripts\python.exe -r backend/requirements-dev.txt
```

### Frontend install fails

Use Node 20+ (tested with Node 24). Delete `node_modules` and `package-lock.json` only
if the lockfile is corrupted, then reinstall:

```powershell
cd frontend
npm install
```

### `npm run dev` cannot reach the backend

- Start the backend on port **8000**.
- Vite proxies `/api` to `http://127.0.0.1:8000`.
- If you changed the backend port, update `frontend/vite.config.ts` or set
  `VITE_API_BASE` for the frontend build.

---

## Backend startup

### Port already in use

```powershell
Get-NetTCPConnection -LocalPort 8000
```

Stop the conflicting process or run on another port:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8001
```

### `PermissionError` on the data directory

Set a writable location:

```powershell
$env:CLASSMIND_DATA_DIR = "C:\Users\<you>\ClassMindData"
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8000
```

### Database is locked

SQLite allows one writer. Close other app instances or long-running scripts using the
same `data/classmind.db`. Restart the backend after an interrupted job; startup recovers
interrupted jobs.

### App starts but health shows degraded

`GET /api/health` reports detector, VAD, and ffmpeg status. A degraded component usually
means optional packages or model weights are missing; core functionality can still work.

---

## Media upload

### `invalid_media` or `upload_rejected`

- Check the extension is allowed (`.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`, `.wav`,
  `.mp3`, and others by default).
- Check the file is a real media file, not a renamed text file.
- Check the size against `CLASSMIND_MAX_UPLOAD_MB` (default 512 MB).
- Check the duration against `CLASSMIND_MAX_MEDIA_DURATION_SEC`.

### Video uploads but analysis finds no people

- Confirm the video actually contains people and is not a blank/screen recording.
- Try YOLO instead of HOG (`detector_backend=yolo`), or lower
  `CLASSMIND_YOLO_CONFIDENCE`.
- Use a shorter sample interval to catch brief appearances.
- Check the quality warnings; `sampled_frames` may be too low.

### Audio not detected

- Confirm the file has an audio stream (`ffprobe` or a media player).
- Audio-only sessions are supported; upload the audio as the audio file.
- Separate audio shorter/longer than the video produces an alignment warning.

---

## Detection and models

### YOLO is not used

- `GET /api/health` shows `detector.active`.
- Install the optional stack:

```powershell
pip install -r backend/requirements-vision.txt
```

- Place `yolov8n.pt` in `data/models/` for offline use.
- If downloads are disabled (`CLASSMIND_ALLOW_MODEL_DOWNLOAD=false`), weights must exist
  locally.
- Set `detector_backend=hog` to use the built-in detector.

### YOLO is very slow

CPU inference can take seconds per sampled frame.

- Increase `sample_interval_sec` (e.g. 5–10 for long recordings).
- Reduce `max_analysis_frames`.
- Reduce `analysis_max_width` or `yolo_imgsz`.
- Use a shorter clip for testing.
- Use HOG for a quick coarse pass.

### PyTorch installation issues on Windows

Install the CPU wheel explicitly if the default index resolves a CUDA build:

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

Then install `ultralytics` and `silero-vad`.

---

## Audio / VAD

### Speech ratio is zero

- The audio may be silence, noise, music, or a synthetic tone. Silero VAD is
  speech-oriented and may reject non-speech.
- Try `CLASSMIND_VAD_BACKEND=energy` to use the energy VAD.
- Check the extracted audio with a media player.

### Too much speech detected

- Energy VAD is sensitive to noise. Use Silero if available.
- Improve the recording or use a cleaner audio track.
- Treat speech activity as a coarse signal, not a transcript.

---

## Frontend

### Blank page after building

- Confirm `frontend/dist/index.html` exists.
- Restart the backend so it picks up the build.
- Check the browser console and the backend log.
- The backend serves the SPA for non-`/api` paths; `/api/...` unknown routes return JSON
  404.

### Deep link returns 404

The backend must serve the SPA. If you use a separate static server, configure it to fall
back to `index.html` for client-side routes.

### Backend health shows "Checking backend..." or disconnected

- Confirm the backend is running and reachable at `/api/health`.
- In development, use the Vite server (port 5173) so the proxy applies.
- In production, open the backend URL (port 8000).
- Check browser network errors and CORS (default allowed origins are local Vite ports).

### Charts do not render

- Recharts needs a sized container; the app provides responsive wrappers.
- In tests, `ResizeObserver` is mocked in `src/test/setup.ts`.
- Check the browser console for errors.

---

## Tests

### Backend tests fail with import errors

Run from the repository root so `pytest.ini` sets `pythonpath = .`:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

### Frontend tests fail with "not a function" API errors

Every page calls specific API helpers. If you add a helper used during render, add it to
the page test's `apiMock` (for example `reportUrl`, `attendanceCsvUrl`).

### File upload test does not trigger validation

`@testing-library/user-event` filters files by the input's `accept` attribute by default.
Use `userEvent.setup({ applyAccept: false })` when testing unsupported formats.

---

## Docker

### Image build is slow or fails

The provided Dockerfile installs only the core stack (no PyTorch/YOLO) to keep the image
small. If you need YOLO, extend the image with `backend/requirements-vision.txt`.

### Data does not persist

`docker-compose.yml` mounts `./data` to `/app/data`. Confirm the mount and write
permissions.

### Camera/live capture does not work in Docker

Containers need explicit device access. Live capture is optional and not verified in
Docker.

---

## Still stuck?

1. Check the backend console log for the traceback.
2. Check `GET /api/health` and `GET /api/settings/models`.
3. Reproduce with a short, known-good clip.
4. Run the automated tests to distinguish an environment issue from a code issue.
5. Inspect `data/sessions/<id>/` to confirm media and extracted audio exist.
