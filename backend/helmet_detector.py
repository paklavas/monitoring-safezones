"""
Helmet & Person Detection Module - Dual-Model Approach
Uses TWO YOLO models simultaneously:
  1. COCO model (yolo11n.pt)  → detects 'person'
  2. Trained model (best.pt)  → detects 'safetyhelmet'
This avoids catastrophic forgetting because person detection
comes from a model that was never fine-tuned on helmet data.

Uses lightweight centroid tracker (predict + distance matching) for person
track_id assignment. Per-person cooldown in server avoids duplicate
violation snapshots of the same worker.

When OpenVINO-exported models are present (yolo11n_openvino_model/ or *_openvino_model/, or *_fp16 variants),
inference uses Intel OpenVINO for faster CPU performance.
"""

import cv2
import numpy as np
from ultralytics import YOLO
import os
import threading

_DIR = os.path.dirname(os.path.abspath(__file__))

# Prefer OpenVINO for inference when available (Intel CPU)
_OPENVINO_DEVICE = "intel:cpu"


class CentroidTracker:
    """Lightweight tracker: match detections by centroid distance (no Kalman/Hungarian)."""

    def __init__(self, max_disappeared=30, max_distance=90):
        self.next_id = 0
        self.objects = {}  # {object_id: (cx, cy)}
        self.disappeared = {}  # {object_id: frames_since_seen}
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    def update(self, rects):
        """rects: list of (x1, y1, x2, y2). Returns list of (object_id, (x1, y1, x2, y2))."""
        if len(rects) == 0:
            for oid in list(self.disappeared.keys()):
                self.disappeared[oid] += 1
                if self.disappeared[oid] > self.max_disappeared:
                    del self.objects[oid]
                    del self.disappeared[oid]
            return []

        centroids = np.array([((r[0] + r[2]) / 2, (r[1] + r[3]) / 2) for r in rects])
        used_oids = set()

        result = []
        for i, rect in enumerate(rects):
            cx, cy = centroids[i]
            best_oid = None
            best_dist = self.max_distance
            for oid, (ocx, ocy) in list(self.objects.items()):
                if oid in used_oids:
                    continue
                dist = np.linalg.norm(np.array([cx - ocx, cy - ocy]))
                if dist < best_dist:
                    best_dist = dist
                    best_oid = oid
            if best_oid is not None:
                used_oids.add(best_oid)
                self.objects[best_oid] = (cx, cy)
                self.disappeared[best_oid] = 0
                result.append((best_oid, tuple(rect)))
            else:
                oid = self.next_id
                self.next_id += 1
                self.objects[oid] = (cx, cy)
                self.disappeared[oid] = 0
                result.append((oid, tuple(rect)))

        for oid in list(self.objects.keys()):
            if oid not in used_oids:
                self.disappeared[oid] += 1
                if self.disappeared[oid] > self.max_disappeared:
                    del self.objects[oid]
                    del self.disappeared[oid]

        return result


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
        self._person_trackers = {}  # {camera_id: CentroidTracker}
        self._trackers_lock = threading.Lock()
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

    def _get_tracker_for_camera(self, camera_id):
        """Get centroid tracker for this camera (separate state per camera)."""
        with self._trackers_lock:
            if camera_id not in self._person_trackers:
                self._person_trackers[camera_id] = CentroidTracker(max_disappeared=30, max_distance=90)
            return self._person_trackers[camera_id]

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
        Run both models on the frame and merge results. Uses tracking for persons
        to assign stable track_id (per-camera model for correct tracker state).

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
                kwargs = {"conf": self.helmet_threshold, "verbose": False}
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

        # --- 2. Person detection (predict) + centroid tracker ---
        if self.person_model is not None:
            try:
                kwargs = {"conf": self.person_threshold, "verbose": False}
                if self._person_use_openvino:
                    kwargs["device"] = _OPENVINO_DEVICE
                results = self.person_model(frame, **kwargs)
                raw_rects = []
                raw_confs = []
                raw_cls_ids = []
                for result in results:
                    for box in result.boxes:
                        cls_id = int(box.cls[0].cpu().numpy())
                        cls_name = result.names.get(cls_id, "")
                        if cls_name.lower() != "person":
                            continue
                        conf = float(box.conf[0].cpu().numpy())
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        raw_rects.append((int(x1), int(y1), int(x2), int(y2)))
                        raw_confs.append(conf)
                        raw_cls_ids.append(cls_id)
                tracker = self._get_tracker_for_camera(camera_id)
                tracked = tracker.update(raw_rects)
                for (track_id, bbox), conf, cls_id in zip(tracked, raw_confs, raw_cls_ids):
                    bbox_list = list(bbox)
                    has_helmet = any(self._bbox_overlaps(bbox_list, h) for h in helmet_bboxes)
                    person_dets.append({
                        "bbox": bbox_list,
                        "confidence": conf,
                        "class": "person",
                        "class_id": cls_id,
                        "track_id": track_id,
                        "is_violator": not has_helmet,
                    })
                    color = (255, 100, 0)
                    cv2.rectangle(annotated, (bbox_list[0], bbox_list[1]), (bbox_list[2], bbox_list[3]), color, 2)
                    label = f"person {conf:.2f} #{track_id}"
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
            kwargs = {"conf": self.helmet_threshold, "verbose": False}
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
