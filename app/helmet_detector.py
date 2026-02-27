"""
Helmet & Person Detection Module – Dual-Model Approach
Uses TWO YOLO models simultaneously:
  1. COCO model (yolo11n.pt)  → detects 'person'
  2. Trained model (best.pt)  → detects 'safetyhelmet'
This avoids catastrophic forgetting because person detection
comes from a model that was never fine-tuned on helmet data.
"""

import cv2
import numpy as np
from ultralytics import YOLO
import os

_DIR = os.path.dirname(os.path.abspath(__file__))


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
        self.model_loaded = False

        # --- Load helmet model (trained) ---
        if model_path and os.path.exists(model_path):
            try:
                self.helmet_model = YOLO(model_path)
                print(f"✅ [Helmet model] Loaded: {model_path}")
                # Show class names in model
                names = self.helmet_model.names if hasattr(self.helmet_model, 'names') else {}
                print(f"   Classes: {names}")
            except Exception as e:
                print(f"❌ [Helmet model] Error loading {model_path}: {e}")
        else:
            print(f"⚠️  [Helmet model] File not found: {model_path}")

        # --- Load person model (COCO pre-trained) ---
        try:
            self.person_model = YOLO("yolo11n.pt")  # Downloads if needed
            print("✅ [Person model] Loaded COCO yolo11n.pt (detects 'person')")
        except Exception:
            try:
                self.person_model = YOLO("yolov8n.pt")
                print("✅ [Person model] Loaded COCO yolov8n.pt fallback")
            except Exception as e2:
                print(f"❌ [Person model] Failed to load any COCO model: {e2}")

        self.model_loaded = (self.helmet_model is not None) or (self.person_model is not None)
        if self.model_loaded:
            has_h = "YES" if self.helmet_model else "NO"
            has_p = "YES" if self.person_model else "NO"
            print(f"📊 Detection ready – helmet model: {has_h}, person model: {has_p}")
            print(f"   Thresholds: person >= {self.person_threshold:.2f}, helmet >= {self.helmet_threshold:.2f}")
        else:
            print("❌ No models loaded – detection disabled")

    # -----------------------------------------------------------------
    # Main detection method
    # -----------------------------------------------------------------
    def detect(self, frame):
        """
        Run both models on the frame and merge results.

        Returns:
            (annotated_frame, detections_list, violation_count)
        """
        if not self.model_loaded:
            return frame, [], 0

        annotated = frame.copy()
        detections = []
        person_count = 0
        helmet_count = 0

        # --- 1. Person detection (COCO model) ---
        if self.person_model is not None:
            try:
                results = self.person_model(frame, conf=self.person_threshold, verbose=False)
                for result in results:
                    for box in result.boxes:
                        cls_id = int(box.cls[0].cpu().numpy())
                        cls_name = result.names.get(cls_id, "")
                        if cls_name.lower() != "person":
                            continue
                        conf = float(box.conf[0].cpu().numpy())
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        person_count += 1
                        detections.append({
                            "bbox": [int(x1), int(y1), int(x2), int(y2)],
                            "confidence": conf,
                            "class": "person",
                            "class_id": cls_id,
                        })
                        # Draw blue box for person
                        color = (255, 100, 0)
                        cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                        label = f"person {conf:.2f}"
                        self._draw_label(annotated, label, int(x1), int(y1), color)
            except Exception as e:
                print(f"Person detection error: {e}")

        # --- 2. Helmet detection (trained model) ---
        if self.helmet_model is not None:
            try:
                results = self.helmet_model(frame, conf=self.helmet_threshold, verbose=False)
                for result in results:
                    for box in result.boxes:
                        cls_id = int(box.cls[0].cpu().numpy())
                        cls_name = result.names.get(cls_id, "")
                        conf = float(box.conf[0].cpu().numpy())
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                        # Accept any helmet-like class
                        if cls_name.lower() in ["hardhat", "helmet", "safetyhelmet"]:
                            helmet_count += 1
                            detections.append({
                                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                                "confidence": conf,
                                "class": cls_name,
                                "class_id": cls_id,
                            })
                            # Draw green box for helmet
                            color = (0, 255, 0)
                            cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                            label = f"{cls_name} {conf:.2f}"
                            self._draw_label(annotated, label, int(x1), int(y1), color)
            except Exception as e:
                print(f"Helmet detection error: {e}")

        # --- 3. Violation count ---
        violation_count = max(0, person_count - helmet_count)

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
            results = self.helmet_model(frame, conf=self.helmet_threshold, verbose=False)
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
