"""
Helmet Detection Module using YOLOv8
This module handles helmet detection using YOLO (You Only Look Once) model.
"""

import cv2
import numpy as np
from ultralytics import YOLO
import os

class HelmetDetector:
    def __init__(self, model_path=None, confidence_threshold=0.5):
        """
        Initialize the helmet detector.
        
        Args:
            model_path: Path to YOLO model file (.pt). If None, uses default YOLOv8 model.
            confidence_threshold: Minimum confidence score for detections (0.0 to 1.0)
        """
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.model_loaded = False
        
        # Try to load model
        if model_path and os.path.exists(model_path):
            try:
                self.model = YOLO(model_path)
                self.model_loaded = True
                print(f"Loaded custom YOLO model from {model_path}")
            except Exception as e:
                print(f"Error loading custom model: {e}")
                self._load_default_model()
        else:
            self._load_default_model()
    
    def _load_default_model(self):
        """Load default YOLOv8 model (will detect general objects, can be fine-tuned for helmets)"""
        try:
            # Try to load a helmet-specific model if available
            # Otherwise, use YOLOv8n (nano) for general object detection
            # You can replace 'yolov8n.pt' with a custom trained helmet detection model
            self.model = YOLO('yolov8n.pt')  # Downloads automatically if not present
            self.model_loaded = True
            print("Loaded default YOLOv8 model")
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            print("Note: Install ultralytics with: pip install ultralytics")
            self.model_loaded = False
    
    def detect(self, frame):
        """
        Detect helmets in a frame.
        
        Args:
            frame: Input frame (numpy array, BGR format from OpenCV)
        
        Returns:
            tuple: (annotated_frame, detections, violation_count)
                - annotated_frame: Frame with bounding boxes drawn
                - detections: List of detection dictionaries
                - violation_count: Number of people without helmets
        """
        if not self.model_loaded or self.model is None:
            return frame, [], 0
        
        try:
            # Run YOLO inference
            # Note: YOLO expects RGB, but we'll pass BGR and let it handle it
            results = self.model(frame, conf=self.confidence_threshold, verbose=False)
            
            annotated_frame = frame.copy()
            detections = []
            helmet_count = 0
            person_count = 0
            
            # Process results
            for result in results:
                boxes = result.boxes
                
                for box in boxes:
                    # Get box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())
                    class_name = result.names[class_id]
                    
                    # Check if detection meets confidence threshold
                    if confidence < self.confidence_threshold:
                        continue
                    
                    # For helmet detection, we typically look for:
                    # - 'person' class (class_id 0 in COCO dataset)
                    # - 'hardhat', 'helmet', 'safetyhelmet' or custom helmet class if you have a trained model
                    
                    # If using default YOLOv8, we detect persons
                    # With custom trained model, detect helmets directly
                    # Common class names: 'safetyhelmet', 'helmet', 'hardhat', 'person'
                    
                    if class_name.lower() in ['person', 'hardhat', 'helmet', 'safetyhelmet']:
                        detection = {
                            'bbox': [int(x1), int(y1), int(x2), int(y2)],
                            'confidence': confidence,
                            'class': class_name,
                            'class_id': class_id
                        }
                        detections.append(detection)
                        
                        # Draw bounding box
                        color = (0, 255, 0)  # Green for helmet/person
                        label = f"{class_name} {confidence:.2f}"
                        
                        # Draw rectangle
                        cv2.rectangle(annotated_frame, 
                                    (int(x1), int(y1)), 
                                    (int(x2), int(y2)), 
                                    color, 2)
                        
                        # Draw label background
                        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                        cv2.rectangle(annotated_frame,
                                    (int(x1), int(y1) - label_size[1] - 10),
                                    (int(x1) + label_size[0], int(y1)),
                                    color, -1)
                        
                        # Draw label text
                        cv2.putText(annotated_frame, label,
                                  (int(x1), int(y1) - 5),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                  (0, 0, 0), 2)
                        
                        if class_name.lower() == 'person':
                            person_count += 1
                        elif class_name.lower() in ['hardhat', 'helmet']:
                            helmet_count += 1
            
            # Calculate violations (people without helmets)
            # This is a simplified logic - in reality, you'd need to:
            # 1. Track which persons have helmets nearby
            # 2. Use a custom model that detects both person and helmet together
            # 3. Use object tracking to associate helmets with people
            
            # For now, we'll use a simple heuristic:
            # If we detect persons but no helmets, it's a violation
            # If you have a custom model that detects "person_with_helmet" and "person_without_helmet",
            # use that instead
            
            violation_count = max(0, person_count - helmet_count)
            
            return annotated_frame, detections, violation_count
            
        except Exception as e:
            print(f"Error in helmet detection: {e}")
            return frame, [], 0
    
    def detect_helmets_only(self, frame):
        """
        Simplified detection that only looks for helmet objects.
        Use this if you have a custom trained model for helmet detection.
        
        Args:
            frame: Input frame (numpy array, BGR format)
        
        Returns:
            tuple: (annotated_frame, helmet_count, violation_count)
        """
        if not self.model_loaded or self.model is None:
            return frame, 0, 0
        
        try:
            results = self.model(frame, conf=self.confidence_threshold, verbose=False)
            
            annotated_frame = frame.copy()
            helmet_count = 0
            
            for result in results:
                boxes = result.boxes
                
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())
                    class_name = result.names[class_id]
                    
                    # Only process helmet detections
                    if class_name.lower() in ['hardhat', 'helmet', 'safetyhelmet'] and confidence >= self.confidence_threshold:
                        helmet_count += 1
                        
                        # Draw green box for helmet
                        cv2.rectangle(annotated_frame,
                                    (int(x1), int(y1)),
                                    (int(x2), int(y2)),
                                    (0, 255, 0), 2)
                        
                        label = f"Helmet {confidence:.2f}"
                        cv2.putText(annotated_frame, label,
                                  (int(x1), int(y1) - 10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                  (0, 255, 0), 2)
            
            # For this simplified version, we assume violations if no helmets detected
            # In a real system, you'd compare person count vs helmet count
            violation_count = 0  # Would need person detection to calculate this
            
            return annotated_frame, helmet_count, violation_count
            
        except Exception as e:
            print(f"Error in helmet-only detection: {e}")
            return frame, 0, 0

