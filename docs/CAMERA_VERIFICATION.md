## 3. Live Camera Verification — PENDING (hardware unavailable)

### 3.1 Software inspection — VERIFIED
- `SessionAnalysis` page has camera index / max-seconds inputs, start/stop buttons, live status display, and a note that camera access requires backend access.
- `backend/app/services/live.py` manages OpenCV `VideoCapture`, writer, thread, events, release in `finally`.
- `backend/app/routers/sessions.py` exposes `/live/start`, `/live/stop`, `/live/status` with appropriate error codes (`503` unavailable, `409` not running / already processing).
- Media is written locally to session directory (`live-{uuid}.mp4`); never exposed publicly.
- No biometric/face processing in live path; video-only (no microphone capture — documented limitation).
- Cleanup: `writer.release(); cap.release()` in finally; `stop_all()` on lifespan shutdown.

### 3.2 Hardware verification — NOT PERFORMED (no webcam on this machine)
- Browser camera permission: not testable without camera.
- Camera device detection: `cv2.VideoCapture(0)` returns `not isOpened()` — documented as expected when no camera.
- Live initialization / frame processing / pipeline integration: endpoint exists, not verifiable without hardware.
- Error handling (no camera): verified by code inspection — raises `LiveError` with explanatory message; frontend shows `liveError`.
- Release / cleanup: verified by code inspection.
- Public exposure: video is stored locally; no public URL; no upload to external service.

### 3.3 Manual verification procedure (if camera is available)
1. Open session analysis page.
2. Enter camera index (default 0) and max seconds.
3. Click Start capture.
4. Confirm status shows active with frame count increasing.
5. Click Stop capture.
6. Confirm session status updates to `uploaded`; video file exists locally.
7. Confirm media is not accessible externally.

Status: **SOFTWARE VERIFIED / HARDWARE PENDING** — not fabricated.
