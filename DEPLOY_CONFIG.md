# Phase Report — Deployment Configuration (Local Only)

## Files created / modified
- `render.yaml` (new, root)
- `vercel.json` (new, root)
- `.env.production` (updated with VITE_API_BASE docs)
- No existing files deleted; Dockerfile / docker-compose preserved

## Phase 1 — Inspect
- Backend entry: `backend/app/main:app`; serves SPA from `frontend/dist`
- Frontend: Vite 7; build output `dist/`; proxy `/api` to 8000 in dev
- Existing env: `.env.example` with `CLASSMIND_` prefixed vars

## Phase 2 — Render (FastAPI backend)
- Service: `classmind-ai` (free tier)
- Runtime: Python 3.12; bind `0.0.0.0:$PORT`
- Build: pip install core + `npm ci && npm run build`
- Start: `python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- Health: `/api/health`
- Env: `CLASSMIND_DATA_DIR`, `CLASSMIND_LOG_LEVEL`, `PYTHONUNBUFFERED`, etc.
- SQLite persistence: NOT guaranteed on Render free (ephemeral). Documented.
- YOLO weights: must be rebuilt/added manually (excluded by `.gitignore`). Documented.
- Blocker: None for config; real deployment requires Render account + manual connection.
- Status: VERIFIED (config valid; not deployed)

## Phase 3 — Vercel (React/Vite frontend)
- Build: `npm ci && npm run build`
- Output: `frontend/dist`
- SPA fallback: routes to `index.html` for all non-file paths (verified via vercel.json routes)
- No redirect to backend; no unnecessary serverless functions
- Status: VERIFIED (config valid; not deployed)

## Phase 4 — Frontend / Backend Connection
- Existing `frontend/src/lib/api.ts` already uses `import.meta.env.VITE_API_BASE` (line 19) with fallback `/api`
- No code change required; smallest needed step was documenting env usage
- `.env.production` documents required `VITE_API_BASE` for production
- CORS: backend uses `cfg.cors_origins` (default localhost only); production needs `CLASSMIND_CORS_ORIGINS` env set on Render to include Vercel domain
- Status: VERIFIED (configurable; no breakage)

## Phase 5 — Verification
- `npm run build`: pass
- `npm run typecheck`: pass
- `pytest`: 60 pass
- `render.yaml`: valid YAML / Render syntax
- `vercel.json`: valid JSON / Vercel syntax
- Docker preserved (no removal)
- Status: VERIFIED

## Required manual steps (NOT performed)
- Create Render account + connect to `saranshnimje/classmind-ai`
- Create Vercel project + connect to same repo
- Set `VITE_API_BASE=https://classmind-ai.onrender.com/api` in Vercel dashboard
- Set `CLASSMIND_CORS_ORIGINS=https://classmind-ai.vercel.app,https://classmind-ai.onrender.com` in Render dashboard
- Upload `data/models/yolov8n.pt` to Render if YOLO needed
- No deployment executed

## Status labels
- Render config: VERIFIED
- Vercel config: VERIFIED
- Frontend connection: VERIFIED / PARTIALLY VERIFIED (needs env set at deploy time)
- Deployment execution: BLOCKED / NOT VERIFIED (awaiting user approval for external service connection)
