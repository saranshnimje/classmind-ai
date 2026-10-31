# Deployment and Hosted Demo

## Public URLs

- Frontend: https://classmind--ai.vercel.app
- Alternate production frontend domain: https://classmind-ai-kohl.vercel.app
- Backend: https://classmind-ai.onrender.com
- Health endpoint: https://classmind-ai.onrender.com/api/health
- API docs: https://classmind-ai.onrender.com/docs
- GitHub: https://github.com/saranshnimje/classmind-ai

## Topology

```text
Browser
  |
  | HTTPS
  v
Vercel static frontend (frontend/)
  |
  | HTTPS /api/* requests; CORS allowlist
  v
Render Free web service (FastAPI)
  |-- SQLite database on instance filesystem
  |-- uploaded media / exports on instance filesystem
  |-- OpenCV HOG person detector (verified fallback)
  |-- energy-based audio VAD (verified fallback)
  |-- optional Ollama integration (not available in hosted runtime)
  `-- optional YOLO/Silero extras (not installed in verified free runtime)
```

## Git-based deployment

- Vercel project is connected to the GitHub repository with the frontend root directory set to `frontend`.
- Render Blueprint is configured from `render.yaml`, repository branch `master`, root directory `.`.
- A push to `master` triggers the connected deployments automatically.
- `render.yaml` includes both production Vercel origins in `CLASSMIND_CORS_ORIGINS`:
  - `https://classmind--ai.vercel.app`
  - `https://classmind-ai-kohl.vercel.app`
  and the local Vite development origins.

## Free-tier caveats

- Render Free may suspend/sleep when idle; the first request can have a cold-start delay.
- The service filesystem is ephemeral. SQLite rows, uploaded media, and exports can disappear after restart/redeploy.
- No persistent disk or managed database is configured.
- The hosted app currently has no authentication, authorization, or tenant isolation. All visitors share the same backend service/data store.
- Do not upload actual classroom recordings, identifiable student data, or confidential media to the public demo. Use synthetic/demo data only.
- The free runtime health check previously confirmed HOG and energy-VAD fallbacks, FFmpeg availability, and Ollama unavailability. These are runtime facts, not a promise that optional model inference is available.

## Self-hosting

For a persistent/private evaluation, run the backend and frontend on a trusted machine you control and configure `CLASSMIND_DATA_DIR` to a protected local directory. Follow the root README Quick start. Keep the host private and apply institutional consent, retention, and access policies before using real classroom data.

## Deployment verification

On 2026-10-31, Render reported the deployment for commit `3aea1104323f044f1cdb879f24302da766af74c3` as `live`. Render logs showed HTTP 200 responses for `/api/health`, `/api/dashboard`, `/api/sessions`, and `/api/settings`. This confirms backend request handling at that time; it is not a complete browser-based end-to-end test of every feature.
