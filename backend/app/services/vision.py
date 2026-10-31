"""Vision pipeline: person detection, tracking and behavioural proxies.

Two detector backends are supported:

* ``yolo`` - Ultralytics YOLO (optional extra, CPU inference, ``yolov8n.pt``).
* ``hog``  - OpenCV's built-in HOG + SVM people detector (no download).

Both are *person* detectors only. They cannot identify who a person is, and
every indicator produced here is an approximate behavioural proxy.
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from ..config import get_config

logger = logging.getLogger(__name__)

PERSON_CLASS_ID = 0


# --------------------------------------------------------------------------
# Data structures
# --------------------------------------------------------------------------
@dataclass
class Detection:
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2
    confidence: float


@dataclass
class Observation:
    t: float
    bbox: tuple[float, float, float, float]
    confidence: float
    movement_norm: float = 0.0
    inactive: bool = True
    head: str = "unknown"
    face_visible: bool = False


@dataclass
class TrackResult:
    index: int
    display_label: str
    observations: list[Observation] = field(default_factory=list)
    first_seen: float = 0.0
    last_seen: float = 0.0
    duration_sec: float = 0.0
    samples_seen: int = 0
    confidence_avg: float = 0.0
    movement_index: float = 0.0
    inactive_sec: float = 0.0
    head_center_ratio: float = 0.0
    head_left_ratio: float = 0.0
    head_right_ratio: float = 0.0
    head_unknown_ratio: float = 1.0
    face_visible_ratio: float = 0.0
    uncertain: bool = False

    def bbox_at(self, t: float) -> tuple[float, float, float, float] | None:
        best = None
        for obs in self.observations:
            if obs.t <= t:
                best = obs
            else:
                break
        return best.bbox if best else None


@dataclass
class VisionResult:
    duration_sec: float
    fps: float
    width: int
    height: int
    sampled_frames: int
    decode_failures: int
    effective_interval: float
    brightness_mean: float
    camera_motion: float
    detector_name: str
    tracks: list[TrackResult] = field(default_factory=list)
    max_simultaneous: int = 0
    warnings: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# Detectors
# --------------------------------------------------------------------------
class BaseDetector:
    name = "none"
    available = False
    detail = ""

    def detect(self, frame: np.ndarray) -> list[Detection]:  # pragma: no cover - interface
        raise NotImplementedError


class NullDetector(BaseDetector):
    name = "none"
    available = True
    detail = "Detection disabled by configuration."

    def detect(self, frame: np.ndarray) -> list[Detection]:
        return []


class HogDetector(BaseDetector):
    name = "hog"
    available = True
    detail = "OpenCV HOG + SVM people detector (built in, no model download)."

    def __init__(self) -> None:
        self._hog = cv2.HOGDescriptor()
        self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect(self, frame: np.ndarray) -> list[Detection]:
        # HOG works best when the frame is not too large.
        rects, weights = self._hog.detectMultiScale(
            frame, winStride=(8, 8), padding=(8, 8), scale=1.05
        )
        detections: list[Detection] = []
        for (x, y, w, h), weight in zip(rects, weights):
            if w < 32 or h < 64:
                continue
            confidence = float(np.clip(float(weight) / 2.0, 0.05, 1.0))
            detections.append(
                Detection(bbox=(float(x), float(y), float(x + w), float(y + h)), confidence=confidence)
            )
        return _non_max_suppression(detections, threshold=0.45)


class YoloDetector(BaseDetector):
    name = "yolo"

    def __init__(self, model_name: str, conf: float, imgsz: int, allow_download: bool) -> None:
        cfg = get_config()
        models_dir = cfg.resolved_data_dir / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        from ultralytics import YOLO  # imported lazily: heavy optional dependency

        try:
            from ultralytics import settings as ultra_settings

            ultra_settings.update({"weights_dir": str(models_dir)})
        except Exception:  # pragma: no cover - ultralytics version differences
            pass

        candidate = Path(model_name)
        if not candidate.is_absolute() and (models_dir / candidate.name).exists():
            candidate = models_dir / candidate.name
        if not candidate.exists() and not allow_download:
            raise RuntimeError(
                f"YOLO weights '{model_name}' are not present in {models_dir} and downloads are disabled."
            )
        self._model = YOLO(str(candidate) if candidate.exists() else model_name)
        self._conf = conf
        self._imgsz = imgsz
        self.available = True
        self.detail = f"Ultralytics YOLO person detector ({model_name}, CPU)."

    def detect(self, frame: np.ndarray) -> list[Detection]:
        results = self._model.predict(
            frame, classes=[PERSON_CLASS_ID], conf=self._conf, imgsz=self._imgsz, verbose=False
        )
        detections: list[Detection] = []
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
                detections.append(
                    Detection(bbox=(x1, y1, x2, y2), confidence=float(box.conf[0].item()))
                )
        return detections


_yolo_cache: dict[str, BaseDetector] = {}


def build_detector(backend: str | None = None) -> BaseDetector:
    """Instantiate the configured detector, degrading gracefully."""
    cfg = get_config()
    backend = (backend or cfg.detector_backend or "auto").lower()

    if backend == "none":
        return NullDetector()
    if backend == "hog":
        return HogDetector()
    if backend == "yolo":
        key = f"{cfg.yolo_model}:{cfg.yolo_confidence}:{cfg.yolo_imgsz}"
        if key not in _yolo_cache:
            _yolo_cache[key] = YoloDetector(
                cfg.yolo_model, cfg.yolo_confidence, cfg.yolo_imgsz, cfg.allow_model_download
            )
        return _yolo_cache[key]

    # auto: prefer YOLO when installed, otherwise HOG.
    try:
        key = f"{cfg.yolo_model}:{cfg.yolo_confidence}:{cfg.yolo_imgsz}"
        if key not in _yolo_cache:
            _yolo_cache[key] = YoloDetector(
                cfg.yolo_model, cfg.yolo_confidence, cfg.yolo_imgsz, cfg.allow_model_download
            )
        return _yolo_cache[key]
    except Exception as exc:  # pragma: no cover - depends on optional install
        logger.info("YOLO unavailable (%s); falling back to OpenCV HOG", exc)
        return HogDetector()


def detector_status(backend: str | None = None) -> dict:
    """Report model availability without downloading anything."""
    cfg = get_config()
    requested = (backend or cfg.detector_backend or "auto").lower()
    yolo_installed = False
    try:
        import importlib.util

        yolo_installed = importlib.util.find_spec("ultralytics") is not None
    except Exception:
        yolo_installed = False
    model_path = cfg.resolved_data_dir / "models" / Path(cfg.yolo_model).name
    weights_present = model_path.exists()
    if requested == "none":
        active = "none"
    elif requested == "hog":
        active = "hog"
    else:
        active = "yolo" if yolo_installed else "hog"
    return {
        "requested": requested,
        "yolo_installed": yolo_installed,
        "yolo_weights_present": weights_present,
        "yolo_weights_path": str(model_path),
        "active": active,
        "note": (
            "YOLO weights download once on first use (internet required); "
            "after that inference is fully local."
            if not weights_present
            else "YOLO weights available locally."
        ),
    }


def _non_max_suppression(detections: list[Detection], threshold: float = 0.45) -> list[Detection]:
    if not detections:
        return []
    boxes = np.array([d.bbox for d in detections], dtype=np.float32)
    scores = np.array([d.confidence for d in detections], dtype=np.float32)
    keep = cv2.dnn.NMSBoxes(
        [[int(b[0]), int(b[1]), int(b[2] - b[0]), int(b[3] - b[1])] for b in boxes],
        scores.tolist(),
        score_threshold=0.0,
        nms_threshold=threshold,
    )
    if len(keep) == 0:
        return []
    indices = np.array(keep).flatten().tolist()
    return [detections[i] for i in indices]


# --------------------------------------------------------------------------
# Tracking
# --------------------------------------------------------------------------
def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = inter_w * inter_h
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _match_score(
    track_bbox: tuple[float, float, float, float],
    det_bbox: tuple[float, float, float, float],
    iou_threshold: float,
) -> float:
    """Combined IoU + centre-distance affinity.

    Sparse frame sampling means a walking person can move entirely outside its
    previous box, so IoU alone fragments tracks. A conservative centre-distance
    fallback with a size-similarity check keeps continuity without matching
    wildly different detections.
    """
    iou = _iou(track_bbox, det_bbox)
    if iou >= iou_threshold:
        return 1.0 + iou

    ax1, ay1, ax2, ay2 = track_bbox
    bx1, by1, bx2, by2 = det_bbox
    a_w, a_h = max(1.0, ax2 - ax1), max(1.0, ay2 - ay1)
    b_w, b_h = max(1.0, bx2 - bx1), max(1.0, by2 - by1)
    diag = ((a_w + a_h) / 2.0 + (b_w + b_h) / 2.0) / 2.0
    centre_dist = math.dist(
        ((ax1 + ax2) / 2, (ay1 + ay2) / 2), ((bx1 + bx2) / 2, (by1 + by2) / 2)
    )
    height_ratio = b_h / a_h
    width_ratio = b_w / a_w
    if (
        centre_dist <= 0.65 * diag
        and 0.5 <= height_ratio <= 2.0
        and 0.5 <= width_ratio <= 2.0
    ):
        return max(0.0, 1.0 - centre_dist / (0.65 * diag))
    return 0.0


class IouTracker:
    """Greedy IoU tracker with a short occlusion tolerance."""

    def __init__(self, iou_threshold: float = 0.25, max_missed: int = 2) -> None:
        self.iou_threshold = iou_threshold
        self.max_missed = max_missed
        self._tracks: dict[int, dict] = {}
        self._next_index = 1
        self.max_simultaneous = 0

    def update(self, detections: list[Detection], t: float) -> list[tuple[int, Detection, float]]:
        assigned: dict[int, Detection] = {}
        used_tracks: set[int] = set()
        matches: list[tuple[int, Detection, float]] = []

        candidates: list[tuple[float, int, int]] = []
        for tid, state in self._tracks.items():
            for di, det in enumerate(detections):
                score = _match_score(state["bbox"], det.bbox, self.iou_threshold)
                if score > 0:
                    candidates.append((score, tid, di))
        candidates.sort(reverse=True)

        used_dets: set[int] = set()
        for score, tid, di in candidates:
            if tid in used_tracks or di in used_dets:
                continue
            used_tracks.add(tid)
            used_dets.add(di)
            assigned[tid] = detections[di]
            matches.append((tid, detections[di], score))

        for di, det in enumerate(detections):
            if di in used_dets:
                continue
            tid = self._next_index
            self._next_index += 1
            self._tracks[tid] = {"bbox": det.bbox, "missed": 0}
            assigned[tid] = det
            matches.append((tid, det, 1.0))

        for tid in list(self._tracks):
            if tid in assigned:
                self._tracks[tid]["bbox"] = assigned[tid].bbox
                self._tracks[tid]["missed"] = 0
            else:
                self._tracks[tid]["missed"] += 1
                if self._tracks[tid]["missed"] > self.max_missed:
                    del self._tracks[tid]

        self.max_simultaneous = max(self.max_simultaneous, len(assigned))
        return matches


# --------------------------------------------------------------------------
# Head orientation proxy (Haar cascade)
# --------------------------------------------------------------------------
class HeadPoseEstimator:
    """Approximate head orientation from frontal-face position inside a body box.

    This is deliberately conservative: when no face is detected the orientation
    is reported as ``unknown`` rather than guessed.
    """

    def __init__(self) -> None:
        cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        self._cascade = cv2.CascadeClassifier(cascade_path)
        self.available = not self._cascade.empty()

    def estimate(self, frame: np.ndarray, bbox: tuple[float, float, float, float]) -> tuple[str, bool]:
        if not self.available:
            return "unknown", False
        x1, y1, x2, y2 = (int(v) for v in bbox)
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 - x1 < 24 or y2 - y1 < 48:
            return "unknown", False
        # Search the upper 65% of the person box for a face.
        upper = frame[y1 : y1 + int((y2 - y1) * 0.65), x1:x2]
        gray = cv2.cvtColor(upper, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = self._cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(24, 24))
        if len(faces) == 0:
            return "unknown", False
        fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
        body_cx = (x2 - x1) / 2
        body_h = y2 - y1
        face_cx = fx + fw / 2
        offset = (face_cx - body_cx) / max(1.0, (x2 - x1) / 2)
        face_cy_rel = (fy + fh / 2) / max(1.0, body_h)
        if face_cy_rel > 0.5:
            return "down", True
        if offset < -0.35:
            return "left", True
        if offset > 0.35:
            return "right", True
        return "center", True


# --------------------------------------------------------------------------
# Video analysis
# --------------------------------------------------------------------------
def _scaled_interval(duration: float, requested: float, max_frames: int) -> float:
    if duration <= 0:
        return requested
    if duration / requested <= max_frames:
        return requested
    return max(requested, duration / max_frames)


def _bbox_center(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def _bbox_diag(bbox: tuple[float, float, float, float]) -> float:
    return max(1.0, ((bbox[2] - bbox[0]) + (bbox[3] - bbox[1])) / 2.0)


def _size_compatible(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> bool:
    a_w, a_h = max(1.0, a[2] - a[0]), max(1.0, a[3] - a[1])
    b_w, b_h = max(1.0, b[2] - b[0]), max(1.0, b[3] - b[1])
    return 0.5 <= b_h / a_h <= 2.0 and 0.5 <= b_w / a_w <= 2.0


def _stitch_fragments(
    track_obs: dict[int, list[Observation]], interval: float
) -> dict[int, list[Observation]]:
    """Merge short track fragments that are close in time and space.

    Sparse sampling can split one stationary/slow-moving person into several
    tracks. This conservative pass only joins fragments that do not overlap in
    time, are at most a few samples apart, and have compatible box sizes.
    """
    order = sorted(track_obs, key=lambda tid: min(o.t for o in track_obs[tid]))
    merged: set[int] = set()
    result: dict[int, list[Observation]] = {}
    max_gap = max(interval * 3.0, 6.0)
    for tid in order:
        if tid in merged:
            continue
        observations = list(track_obs[tid])
        changed = True
        while changed:
            changed = False
            tail = max(observations, key=lambda o: o.t)
            for other in order:
                if other in merged or other == tid:
                    continue
                other_obs = track_obs[other]
                head = min(other_obs, key=lambda o: o.t)
                gap = head.t - tail.t
                if gap < 0 or gap > max_gap:
                    continue
                if not _size_compatible(tail.bbox, head.bbox):
                    continue
                distance = math.dist(_bbox_center(tail.bbox), _bbox_center(head.bbox))
                if distance <= 1.8 * (_bbox_diag(tail.bbox) + _bbox_diag(head.bbox)) / 2.0:
                    observations.extend(other_obs)
                    observations.sort(key=lambda o: o.t)
                    merged.add(other)
                    changed = True
                    break
        result[tid] = observations
    return result


def _summarize_track(
    tid: int, observations: list[Observation], interval: float, duration: float
) -> TrackResult:
    observations = sorted(observations, key=lambda o: o.t)
    total = len(observations)
    head_counts = {"center": 0, "left": 0, "right": 0, "down": 0, "unknown": 0}
    for obs in observations:
        head_counts[obs.head] = head_counts.get(obs.head, 0) + 1
    movements = [o.movement_norm for o in observations[1:]]
    movement_index = float(np.clip(np.mean(movements) * 20, 0.0, 1.0)) if movements else 0.0

    inactive_sec = 0.0
    current_run = 0
    for obs in observations:
        if obs.inactive:
            current_run += 1
            inactive_sec = max(inactive_sec, current_run * interval)
        else:
            current_run = 0

    first_seen = observations[0].t
    last_seen = observations[-1].t
    duration_track = max(0.0, last_seen - first_seen)
    if total > 1:
        duration_track = min(duration_track + interval, duration or duration_track + interval)

    confidence_avg = float(np.mean([o.confidence for o in observations]))
    return TrackResult(
        index=tid,
        display_label=f"Participant {tid}",
        observations=observations,
        first_seen=round(first_seen, 3),
        last_seen=round(last_seen, 3),
        duration_sec=round(duration_track, 3),
        samples_seen=total,
        confidence_avg=round(confidence_avg, 4),
        movement_index=round(movement_index, 4),
        inactive_sec=round(inactive_sec, 3),
        head_center_ratio=round(head_counts["center"] / total, 4),
        head_left_ratio=round(head_counts["left"] / total, 4),
        head_right_ratio=round(head_counts["right"] / total, 4),
        head_unknown_ratio=round(head_counts["unknown"] / total, 4),
        face_visible_ratio=round(sum(1 for o in observations if o.face_visible) / total, 4),
        uncertain=total < 3 or confidence_avg < 0.4,
    )


def analyze_video(
    video_path: Path,
    *,
    sample_interval: float = 2.0,
    max_frames: int = 900,
    max_width: int = 640,
    detector: BaseDetector | None = None,
    progress_cb=None,
) -> VisionResult:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError("OpenCV could not open the video file")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    frame_count = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frame_count / fps if frame_count and fps else 0.0

    detector = detector or build_detector()
    tracker = IouTracker()
    head_pose = HeadPoseEstimator()
    track_obs: dict[int, list[Observation]] = {}
    prev_small: np.ndarray | None = None
    brightness_values: list[float] = []
    motion_values: list[float] = []
    decode_failures = 0
    sampled = 0

    interval = _scaled_interval(duration, sample_interval, max_frames)
    if duration <= 0:
        # Unknown duration: decode sequentially with a bounded frame budget.
        duration = 0.0
    timestamps = []
    if duration > 0:
        t = 0.0
        while t <= duration + 1e-6 and len(timestamps) < max_frames:
            timestamps.append(round(t, 3))
            t += interval
    else:
        timestamps = [i * interval for i in range(max_frames)]

    for requested_t in timestamps:
        if duration > 0:
            cap.set(cv2.CAP_PROP_POS_MSEC, requested_t * 1000)
        ok, frame = cap.read()
        if progress_cb is not None and (sampled % 5 == 0 or sampled == len(timestamps)):
            try:
                progress_cb(sampled, len(timestamps))
            except Exception:  # pragma: no cover - progress reporting must never break analysis
                logger.debug("progress callback failed", exc_info=True)
        if not ok or frame is None:
            decode_failures += 1
            continue
        sampled += 1
        if duration <= 0:
            duration = sampled * interval

        actual_t = requested_t
        if duration > 0:
            pos_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
            if pos_ms and abs(pos_ms / 1000.0 - requested_t) < max(interval * 1.5, 1.0):
                actual_t = pos_ms / 1000.0

        if width <= 0 or height <= 0:
            height, width = frame.shape[:2]
        if width > max_width:
            scale = max_width / width
            frame = cv2.resize(frame, (max_width, int(height * scale)), interpolation=cv2.INTER_AREA)
            width, height = frame.shape[1], frame.shape[0]

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness_values.append(float(gray.mean()))
        small = cv2.resize(gray, (64, 36), interpolation=cv2.INTER_AREA)
        if prev_small is not None:
            motion_values.append(float(np.mean(cv2.absdiff(prev_small, small))))
        prev_small = small

        detections = detector.detect(frame)
        matches = tracker.update(detections, actual_t)
        for tid, det, _score in matches:
            observations = track_obs.setdefault(tid, [])
            movement = 0.0
            inactive = True
            if observations:
                px1, py1, px2, py2 = observations[-1].bbox
                cx_prev, cy_prev = (px1 + px2) / 2, (py1 + py2) / 2
                cx, cy = (det.bbox[0] + det.bbox[2]) / 2, (det.bbox[1] + det.bbox[3]) / 2
                movement = math.dist((cx, cy), (cx_prev, cy_prev)) / max(1.0, width)
                inactive = movement < 0.002
            head, face_visible = head_pose.estimate(frame, det.bbox)
            observations.append(
                Observation(
                    t=actual_t,
                    bbox=det.bbox,
                    confidence=det.confidence,
                    movement_norm=movement,
                    inactive=inactive,
                    head=head,
                    face_visible=face_visible,
                )
            )

    cap.release()

    stitched = _stitch_fragments(track_obs, interval)
    tracks: list[TrackResult] = [
        _summarize_track(tid, observations, interval, duration)
        for tid, observations in sorted(stitched.items())
        if observations
    ]

    warnings: list[str] = []
    if sampled == 0:
        warnings.append("No frames could be decoded from the video.")
    if decode_failures > max(2, sampled // 5):
        warnings.append(
            f"{decode_failures} sampled frames could not be decoded; results may be incomplete."
        )
    brightness = float(np.mean(brightness_values)) if brightness_values else 0.0
    if brightness_values and brightness < 50:
        warnings.append("Low average frame brightness; detection confidence may be reduced.")
    camera_motion = float(np.mean(motion_values)) if motion_values else 0.0
    if camera_motion > 12:
        warnings.append("High global frame difference detected; camera movement may affect tracking.")
    if not tracks:
        warnings.append(
            "No people were detected. The camera angle, lighting, resolution or detector "
            "settings may be unsuitable. No attendance is inferred."
        )
    if len(tracks) > max(1, tracker.max_simultaneous) * 2.2 and duration > 60:
        warnings.append(
            "High track fragmentation: one person may be counted more than once. "
            "Treat participant counts as approximate."
        )

    return VisionResult(
        duration_sec=round(duration, 3),
        fps=round(fps, 3),
        width=width,
        height=height,
        sampled_frames=sampled,
        decode_failures=decode_failures,
        effective_interval=round(interval, 3),
        brightness_mean=round(brightness, 2),
        camera_motion=round(camera_motion, 3),
        detector_name=detector.name,
        tracks=tracks,
        max_simultaneous=tracker.max_simultaneous,
        warnings=warnings,
    )
