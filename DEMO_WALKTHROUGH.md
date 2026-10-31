# Mentor Demonstration — 5-Minute Walkthrough

Estimated duration: ~5 minutes (with brief pauses for explanation)

## Setup (before demo, already completed)
- Backend running locally (port 8000)
- Frontend accessible (port 5173 dev or port 8000 production build)
- A completed session (`cd0f4db8b6064bcebf81bdc89b54166d`) available in database for quick review
- Demo session available (optional)

---

## Minute 1 — Overview & Privacy

**What to say:**
> "ClassMind AI is a local-only classroom intelligence agent. It takes a video and optional audio file, detects anonymous tracks, estimates attendance, produces windowed engagement analytics, and generates evidence-linked recommendations — all on this machine, with no biometric identification and no cloud dependencies."

**Action:**
- Open the app URL.
- Point to the privacy banner at the footer (local processing, anonymous tracks, proxy not assessment).
- Open `/about` briefly to confirm: local processing, no face recognition, no identity inference, manual mapping only.

---

## Minute 2 — Real Recorded-Media Pipeline

**What to say:**
> "This session was verified with a real 12-second video plus a synthesized speech track. The pipeline ran YOLO detection, tracked 12 anonymous participants, produced attendance, a windowed analytics result, and recommendations — without any fabricated results."

**Action:**
- Open `/analytics/cd0f4db8b6064bcebf81bdc89b54166d` (or a completed session).
- Show: status = completed; detector = yolo; audio = silero; 12 tracks; 6 present / 6 unconfirmed; 50% attendance; 1 window; 76.8% speech ratio; 3 recommendations.
- Point to `data_quality` (partial — because no frontal faces visible; correctly reported, not hidden).
- Point to `methodology` section showing the exact engagement proxy formula.

---

## Minute 3 — Attendance & Recommendations

**What to say:**
> "Tracks are anonymous. Attendance reflects only visible, trackable people — not a student roll. Manual mapping is required if names are needed, and the mapping is always marked uncertain. Recommendations are ruled-based with evidence, not guesses about students."

**Action:**
- Open `/attendance/<id>`.
- Show: total detected, present/late/unconfirmed counts, warnings.
- Show a track with manual mapping optional.
- Open `/recommendations/<id>`.
- Show a recommendation with evidence, interval, observed values, interpretation, and source (`rules`).
- Note: `generated_by` = `rules`; `llm_available` = false (Ollama not running; fallback works).

---

## Minute 4 — Reports, Downloads, and Settings

**What to say:**
> "Every result can be exported — JSON for integration, CSV for spreadsheets, HTML for sharing with colleagues. The settings page shows real-time component status and allows retention and analysis preference adjustments."

**Action:**
- From session page, open `/reports/<id>` briefly (show JSON structure with quality, windows, recommendations).
- Mention HTML report (`/reports/<id>.html`) and attendance CSV (`/attendance/<id>.csv`).
- Open `/settings`: show detector (yolo active), VAD (silero active), Ollama (disabled/unreachable, documented), limits.

---

## Minute 5 — Documentation, Verification, and Blockers

**What to say:**
> "Everything is documented — architecture, privacy/ethics, limitations, troubleshooting, security audit, camera and Ollama verification. The only unverified items are Docker image build — because Docker Desktop daemon isn't running on this machine — and live camera capture — because there's no webcam. Nothing has been fabricated; nothing has been changed to hide anything."

**Action:**
- Open `README.md` in editor or browser tab.
- Point to verification table (60 backend, 42 frontend, E2E done; Docker, camera, Ollama listed clearly).
- Open `DOCKER_BLOCKER.md` briefly to show transparency.
- Open `docs/CAMERA_VERIFICATION.md` to show software-verified / hardware-pending status.
- Confirm `data/models/yolov8n.pt` preserved locally (not in repo).
- Confirm no `.env` secrets exist; `.env.example` is template only.
- Confirm no GitHub repo created, no push performed, no fabricated demo URL.

---

## Closing

**Key message:**
> "This is not a prototype with hidden gaps. The gaps (Docker daemon unavailable, no camera hardware) are documented explicitly rather than hidden. All working features are verified with automated tests and real media. The privacy design is verifiable from source — no biometrics, no cloud, no public URLs, no secrets in code."

**Stop after closing — ask user for approval to proceed with submission actions (repo creation, SkillWallet upload, etc.). Do NOT commit, push, or publish without approval.**
