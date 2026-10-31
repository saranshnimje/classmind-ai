## 5. AI / Processing Component Verification — Docker Environment

### 5.1 YOLO Detector
- **Weights present**: `/app/data/models/yolov8n.pt` (6.5 MB) — confirmed in container.
- **Package installed in image?** No (`ultralytics`, `torch`, `torchvision` not installed in core image).
- **Active detector**: `hog` (OpenCV HOG) — **VERIFIED** (correct, not fabricated).
- **Attempted fix**: Installed vision packages (`pip install ultralytics torch torchvision silero-vad`) — timed out after >5 min due to large download (~1 GB).
- **Conclusion**: The image is intentionally core-only (`requirements.txt`). To activate YOLO in Docker, rebuild with `requirements-vision.txt`. The fallback (HOG) works correctly and is verified.
- **Status**: PARTIALLY VERIFIED / BLOCKED (depends on vision package download; weights verified present; HOG verified working)

### 5.2 Audio VAD
- **Requested backend**: `auto`
- **Active backend**: `energy` (built-in NumPy energy VAD)
- **Silero available?** No (`silero-vad` package not installed)
- **Status**: VERIFIED — energy VAD works correctly; Silero requires `requirements-vision.txt` and package install.

### 5.3 Tracking / Presence Logic
- The pipeline uses `backend/app/services/vision.py` with IoU + centre-distance matching and fragment stitching.
- Attendance rules: sustained-presence (`min_presence_sec`, `late_after_sec`) — verified by code inspection and E2E results.
- **Status**: VERIFIED

### 5.4 Head / Face Proxies
- Frontal-face Haar cascade inside each box → `center`/`left`/`right`/`unknown`.
- Often `unknown` in classroom-wide shots — correctly reported.
- **Status**: VERIFIED (approximate, documented as limitation)

### 5.5 Recommendation Engine
- Rule-based with deterministic conditions (`DIFFICULTY_KEYWORDS`, engagement/progress patterns).
- Optional Ollama (`llama3.2`) — not reachable in container (no local Ollama service).
- **Status**: VERIFIED — rules work; fallback verified in tests.

### 5.6 No False Activation Claims
- Nothing reported as "YOLO active" when it isn't.
- Nothing reported as "Silero active" when it isn't.
- Health endpoint clearly shows `yolo_installed: false`, `silero_available: false`.
