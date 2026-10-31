# SkillWallet — ClassMind AI Project Description

## Project Title
ClassMind AI — Multimodal Classroom Intelligence Agent (Local-First)

## Problem Statement
Classrooms generate valuable observational data — student movement, participation, attendance — but most analysis relies either on subjective teacher notes or on cloud AI services that expose student recordings to third-party processing. There is no local, transparent, privacy-preserving tool that turns a classroom video recording into structured attendance estimates, windowed engagement proxies, evidence-linked recommendations, and exportable reports — all without biometric identification, face recognition, or public media hosting.

## Solution Overview
ClassMind AI is a complete local-first application (FastAPI + React/TypeScript + SQLite + OpenCV/YOLO + optional Silero VAD + optional Ollama) that processes classroom recordings on the user's own machine. It provides:

- Anonymous person detection and tracking (YOLO or OpenCV HOG; never biometric)
- Attendance classification with sustained-presence rules and manual roster mapping
- Windowed engagement analytics with transparent methodology and quality warnings
- Evidence-linked teaching recommendations (rule-based + optional local LLM)
- HTML/CSV reports, attendance CSV exports, and a full dashboard
- All data stays local; nothing is uploaded or exposed publicly

## Technical Architecture

```
Frontend: React 19 + Vite 7 + TypeScript + Tailwind CSS + Recharts + Lucide
Backend: FastAPI 0.162 + Pydantic v2 + SQLAlchemy 2 + SQLite
Vision: OpenCV headless + optional Ultralytics YOLOv8n (CPU)
Audio: ffmpeg (bundled via imageio-ffmpeg) + NumPy energy VAD + optional Silero VAD
Recommendations: deterministic rules + optional local Ollama (127.0.0.1:11434)
Storage: SQLite + local filesystem under `./data/`
Deployment: optional Docker Compose (`Dockerfile` + `docker-compose.yml`)
```

Key design choices:
- No face recognition, speaker identification, emotion detection, or demographic inference
- Missing data is reported as unavailable, never as zero engagement
- All outputs include method notes, limitations, and confidence indicators
- Demo data is explicitly labelled simulated; never presented as inference

## Key Features

1. **Media upload and validation** — video/audio file validation with OpenCV/ffmpeg probing
2. **Background processing pipeline** — status polling, progress tracking, error handling
3. **Attendance** — anonymous tracks, sustained-presence rules, manual mapping, warnings
4. **Analytics** — windowed metrics (movement, presence, speech ratio), methodology transparency
5. **Recommendations** — evidence-linked suggestions with priority, confidence, source labels
6. **Reports** — JSON, CSV, HTML, attendance CSV exports
7. **Privacy-first** — local storage, anonymous tracks, retention controls, no biometrics
8. **Live camera capture** — optional OpenCV `VideoCapture` (hardware-dependent; documented as pending)
9. **Settings** — analysis defaults, model status, retention, Ollama config
10. **Dashboard** — aggregate metrics, recent events, processing state

## Project Workflow

1. **Setup** — Python 3.12 venv + Node 20+ + optional vision/audio dependencies
2. **Analysis** — create session → upload media → run processing → review results
3. **Review** — attendance, analytics, recommendations; export reports
4. **Verification** — backend tests (60), frontend tests (42), TypeScript, production build, real media E2E, live UI check
5. **Documentation** — README, architecture, privacy/ethics, limitations, troubleshooting, verification reports

## Verification Evidence

- Backend automated tests: **60 passed**
- Frontend automated tests: **42 passed** across 10 files
- TypeScript: **passes** (`tsc --noEmit`)
- Production build: **passes** (`vite build`; chunked output)
- Real recorded-media E2E: verified with 12 s MP4 + synthesized speech WAV
- Security audit: completed (no biometrics, no cloud dependencies, no secrets)
- Docker Compose: validated (image build blocked by daemon unavailable — documented)

## Conclusion
ClassMind AI demonstrates that classroom observation analytics can be done locally, transparently, and with explicit privacy protections. It serves as both a practical tool and a reference for how AI-assisted education software should handle sensitive student data.
