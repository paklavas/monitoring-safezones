"""
Helmet & Person Detection Module - Dual-Model Approach
Uses TWO YOLO models simultaneously:
  1. COCO model (yolo11n.pt)  → detects 'person'
  2. Trained model (best.pt)  → detects 'safetyhelmet'
This avoids catastrophic forgetting because person detection
comes from a model that was never fine-tuned on helmet data.

Uses SmartViolationDedup (IoU + perceptual hash) for violators: no tracker.
Same violator is recognized by spatial overlap (IoU) or appearance (phash).
When OpenVINO-exported models are present, inference uses Intel OpenVINO.
"""

import cv2
import numpy as np
from ultralytics import YOLO
import os
import threading
import time

try:
    import imagehash
    from PIL import Image
    _HAS_IMAGEHASH = True
except ImportError:
    _HAS_IMAGEHASH = False

_DIR = os.path.dirname(os.path.abspath(__file__))

# Prefer OpenVINO for inference when available (Intel CPU)
_OPENVINO_DEVICE = "intel:cpu"

# SmartViolationDedup params
_DEDUP_COOLDOWN = 30.0       # seconds; prune older records
_DEDUP_IOU_THRESH = 0.4      # IoU >= this => same location
_DEDUP_HASH_THRESH = 10      # Hamming distance <= this => same appearance
_DEDUP_STORE_MAX = 50        # max records per camera


class SmartViolationDedup:
    """IoU + perceptual hash dedup: same violator by overlap or appearance, no tracker."""

    def __init__(self, cooldown=30.0, iou_thresh=0.4, hash_thresh=10, store_max=50):
        self._records = {}   # {camera_id: [(violator_id, bbox, phash, timestamp), ...]}
        self._next_id = 0
        self._lock = threading.Lock()
        self.cooldown = cooldown
        self.iou_thresh = iou_thresh
        self.hash_thresh = hash_thresh
        self.store_max = store_max

    @staticmethod
    def _compute_iou(bbox_a, bbox_b):
        """IoU of two boxes [x1,y1,x2,y2]. Returns 0 if no overlap."""
        ax1, ay1, ax2, ay2 = bbox_a[0], bbox_a[1], bbox_a[2], bbox_a[3]
        bx1, by1, bx2, by2 = bbox_b[0], bbox_b[1], bbox_b[2], bbox_b[3]
        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0
        inter = (ix2 - ix1) * (iy2 - iy1)
        area_a = (ax2 - ax1) * (ay2 - ay1)
        area_b = (bx2 - bx1) * (by2 - by1)
        union = area_a + area_b - inter
        return inter / union if union > 0 else 0.0

    @staticmethod
    def _phash(crop):
        """Perceptual hash of person crop. Returns None if invalid."""
        if crop is None or crop.size == 0:
            return None
        try:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            pil = Image.fromarray(gray)
            return imagehash.phash(pil)
        except Exception:
            return None

    @staticmethod
    def _hamming(h1, h2):
        """Hamming distance between two imagehash ImageHash values."""
        if h1 is None or h2 is None:
            return 999
        return h1 - h2

    def get_violator_id(self, camera_id, bbox, crop):
        """Match by IoU or phash; return existing violator_id or create new one."""
        if not _HAS_IMAGEHASH:
            with self._lock:
                self._next_id += 1
                return self._next_id - 1
        h = self._phash(crop)
        now = time.time()
        with self._lock:
            store = self._records.setdefault(camera_id, [])
            cutoff = now - self.cooldown
            store[:] = [r for r in store if r[3] > cutoff]
            for i, (vid, prev_bbox, prev_hash, _) in enumerate(store):
                iou_match = self._compute_iou(bbox, prev_bbox) >= self.iou_thresh
                hash_match = h is not None and prev_hash is not None and self._hamming(h, prev_hash) <= self.hash_thresh
                if iou_match or hash_match:
                    store[i] = (vid, bbox, h if h is not None else prev_hash, now)
                    return vid
            self._next_id += 1
            vid = self._next_id - 1
            store.append((vid, bbox, h, now))
            if len(store) > self.store_max:
                store.sort(key=lambda x: x[3])
                del store[: -self.store_max]
            return vid


class HelmetDetector:
    def __init__(self, model_path=None, confidence_threshold=0.5):
        """
        Initialise dual-model detector.

        Args:
            model_path: Path to the *helmet* model (.pt trained on safetyhelmet data).
            confidence_threshold: Base confidence (helmet uses this, person uses 0.35).
        """
        self.helmet_threshold = confidence_threshold
        self.person_threshold = 0.35  # COCO person detection threshold

        self.helmet_model = None
        self.person_model = None
        self._person_use_openvino = False
        self._helmet_use_openvino = False
        self._smart_dedup = SmartViolationDedup(
            cooldown=_DEDUP_COOLDOWN,
            iou_thresh=_DEDUP_IOU_THRESH,
            hash_thresh=_DEDUP_HASH_THRESH,
            store_max=_DEDUP_STORE_MAX,
        )
        self.model_loaded = False

        # --- Load helmet model (trained); prefer OpenVINO if exported ---
        if model_path and os.path.exists(model_path):
            try:
                helmet_dir = os.path.dirname(model_path)
                stem = os.path.splitext(os.path.basename(model_path))[0]
                openvino_dir = os.path.join(helmet_dir, f"{stem}_openvino_model_fp16")
                if not os.path.isdir(openvino_dir):
                    openvino_dir = os.path.join(helmet_dir, f"{stem}_openvino_model")
                if os.path.isdir(openvino_dir):
                    self.helmet_model = YOLO(openvino_dir)
                    self._helmet_use_openvino = True
                    print(f"✅ [Helmet model] Loaded OpenVINO: {openvino_dir}")
                else:
                    self.helmet_model = YOLO(model_path)
                    print(f"✅ [Helmet model] Loaded: {model_path}")
                names = self.helmet_model.names if hasattr(self.helmet_model, 'names') else {}
                print(f"   Classes: {names}")
            except Exception as e:
                print(f"❌ [Helmet model] Error loading {model_path}: {e}")
        else:
            print(f"⚠️  [Helmet model] File not found: {model_path}")

        # --- Load person model (COCO); prefer OpenVINO if exported ---
        person_openvino = os.path.join(_DIR, "yolo11n_openvino_model_416")
        if not os.path.isdir(person_openvino):
            person_openvino = os.path.join(_DIR, "yolo11n_openvino_model_fp16")
        if not os.path.isdir(person_openvino):
            person_openvino = os.path.join(_DIR, "yolo11n_openvino_model")
        try:
            if os.path.isdir(person_openvino):
                self.person_model = YOLO(person_openvino)
                self._person_use_openvino = True
                print("✅ [Person model] Loaded OpenVINO yolo11n (detects 'person')")
            else:
                self.person_model = YOLO("yolo11n.pt")
                print("✅ [Person model] Loaded COCO yolo11n.pt (detects 'person')")
        except Exception:
            try:
                if os.path.isdir(person_openvino):
                    self.person_model = YOLO(person_openvino)
                    self._person_use_openvino = True
                else:
                    self.person_model = YOLO("yolov8n.pt")
                    self._person_use_openvino = False
                print("✅ [Person model] Loaded COCO yolov8n.pt fallback")
            except Exception as e2:
                print(f"❌ [Person model] Failed to load any COCO model: {e2}")

        self.model_loaded = (self.helmet_model is not None) or (self.person_model is not None)
        if self.model_loaded:
            has_h = "YES" if self.helmet_model else "NO"
            has_p = "YES" if self.person_model else "NO"
            print(f"📊 Detection ready - helmet model: {has_h}, person model: {has_p}")
            print(f"   Thresholds: person >= {self.person_threshold:.2f}, helmet >= {self.helmet_threshold:.2f}")
        else:
            print("❌ No models loaded - detection disabled")

    @staticmethod
    def _crop_person(frame, bbox, padding=0.1):
        """Crop person roi with optional padding. Returns BGR patch or None if invalid."""
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = [int(round(x)) for x in bbox]
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)
        pad_w = int(bw * padding)
        pad_h = int(bh * padding)
        x1 = max(0, x1 - pad_w)
        y1 = max(0, y1 - pad_h)
        x2 = min(w, x2 + pad_w)
        y2 = min(h, y2 + pad_h)
        if x2 <= x1 or y2 <= y1:
            return None
        return frame[y1:y2, x1:x2]

    @staticmethod
    def _bbox_overlaps(box_a, box_b):
        """True if box_a and box_b have any intersection."""
        x1 = max(box_a[0], box_b[0])
        y1 = max(box_a[1], box_b[1])
        x2 = min(box_a[2], box_b[2])
        y2 = min(box_a[3], box_b[3])
        return x2 > x1 and y2 > y1

    # -----------------------------------------------------------------
    # Main detection method
    # -----------------------------------------------------------------
    def detect(self, frame, camera_id=1):
        """
        Run both models on the frame and merge results. Uses ReID-style appearance
        Uses SmartViolationDedup (IoU + phash) .

        Returns:
            (annotated_frame, detections_list, violation_count)
        """
        if not self.model_loaded:
            return frame, [], 0

        annotated = frame.copy()
        detections = []
        person_dets = []
        helmet_bboxes = []

        # --- 1. Helmet detection first (needed for overlap check) ---
        if self.helmet_model is not None:
            try:
                kwargs = {"conf": self.helmet_threshold, "verbose": False, "imgsz": 416}
                if self._helmet_use_openvino:
                    kwargs["device"] = _OPENVINO_DEVICE
                results = self.helmet_model(frame, **kwargs)
                for result in results:
                    for box in result.boxes:
                        cls_id = int(box.cls[0].cpu().numpy())
                        cls_name = result.names.get(cls_id, "")
                        conf = float(box.conf[0].cpu().numpy())
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        if cls_name.lower() in ["hardhat", "helmet", "safetyhelmet"]:
                            bbox = [int(x1), int(y1), int(x2), int(y2)]
                            helmet_bboxes.append(bbox)
                            detections.append({
                                "bbox": bbox,
                                "confidence": conf,
                                "class": cls_name,
                                "class_id": cls_id,
                            })
                            color = (0, 255, 0)
                            cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                            self._draw_label(annotated, f"{cls_name} {conf:.2f}", int(x1), int(y1), color)
            except Exception as e:
                print(f"Helmet detection error: {e}")

        # --- 2. Person detection (YOLO only) + ReID-style violator_id for dedup ---
        if self.person_model is not None:
            try:
                kwargs = {"conf": self.person_threshold, "verbose": False, "imgsz": 416, "classes": [0]}
                if self._person_use_openvino:
                    kwargs["device"] = _OPENVINO_DEVICE
                results = self.person_model(frame, **kwargs)
                if results:
                    result = results[0]
                    now = time.time()
                    for box in result.boxes:
                        xyxy = box.xyxy[0]
                        if hasattr(xyxy, "cpu"):
                            xyxy = xyxy.cpu().numpy()
                        bbox_list = [int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])]
                        conf = float(box.conf[0].cpu().numpy() if hasattr(box.conf[0], "cpu") else box.conf[0])
                        has_helmet = any(self._bbox_overlaps(bbox_list, h) for h in helmet_bboxes)
                        is_violator = not has_helmet
                        track_id = None
                        if is_violator:
                            crop = self._crop_person(frame, bbox_list)
                            track_id = self._smart_dedup.get_violator_id(camera_id, bbox_list, crop)
                        person_dets.append({
                            "bbox": bbox_list,
                            "confidence": conf,
                            "class": "person",
                            "class_id": 0,
                            "track_id": track_id,
                            "is_violator": is_violator,
                        })
                        color = (255, 100, 0)
                        cv2.rectangle(annotated, (bbox_list[0], bbox_list[1]), (bbox_list[2], bbox_list[3]), color, 2)
                        label = f"person {conf:.2f}" + (f" #{track_id}" if track_id is not None else "")
                        self._draw_label(annotated, label, bbox_list[0], bbox_list[1], color)
            except Exception as e:
                print(f"Person detection error: {e}")

        for pd in person_dets:
            d = {"bbox": pd["bbox"], "confidence": pd["confidence"], "class": "person", "class_id": pd["class_id"]}
            if pd.get("track_id") is not None:
                d["track_id"] = pd["track_id"]
            if pd.get("is_violator"):
                d["is_violator"] = True
            detections.append(d)

        person_count = len(person_dets)
        helmet_count = len(helmet_bboxes)
        violation_count = sum(1 for p in person_dets if p.get("is_violator"))

        return annotated, detections, violation_count

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    @staticmethod
    def _draw_label(frame, label, x, y, color):
        """Draw a label with background at (x, y-offset)."""
        sz, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.rectangle(frame, (x, y - sz[1] - 10), (x + sz[0], y), color, -1)
        cv2.putText(frame, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

    def detect_helmets_only(self, frame):
        """Simplified: only run the helmet model. Returns (annotated, helmet_count, 0)."""
        if self.helmet_model is None:
            return frame, 0, 0
        try:
            kwargs = {"conf": self.helmet_threshold, "verbose": False, "imgsz": 416}
            if self._helmet_use_openvino:
                kwargs["device"] = _OPENVINO_DEVICE
            results = self.helmet_model(frame, **kwargs)
            annotated = frame.copy()
            count = 0
            for result in results:
                for box in result.boxes:
                    cls_name = result.names.get(int(box.cls[0].cpu().numpy()), "")
                    if cls_name.lower() not in ["hardhat", "helmet", "safetyhelmet"]:
                        continue
                    conf = float(box.conf[0].cpu().numpy())
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    count += 1
                    cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    cv2.putText(annotated, f"Helmet {conf:.2f}", (int(x1), int(y1) - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            return annotated, count, 0
        except Exception as e:
            print(f"Helmet-only detection error: {e}")
            return frame, 0, 0
