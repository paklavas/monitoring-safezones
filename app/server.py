"""
Flask backend server for Workplace Safety Monitoring System
Serves camera streams with helmet/person detection and handles authentication
"""
import cv2
import sqlite3
import os
import threading
import numpy as np
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import time
from datetime import datetime

# ---------------------------------------------------------------------------
# Zone 1: local webcam. Try 0, 1, or 2 if your webcam is not on 0
# ---------------------------------------------------------------------------
ZONE1_CAMERA_INDEX = 0  # Change to 1 or 2 if no camera found on 0

# ---------------------------------------------------------------------------
# Axis camera for Zone 2 (Safe Zone 2) – set your URL or None to disable
# ---------------------------------------------------------------------------
AXIS_CAMERA_2_URL = "rtsp://root:password@192.168.0.90:554/axis-media/media.amp"

# ---------------------------------------------------------------------------
# Helmet detection: use trained model if present, else default yolov8n
# ---------------------------------------------------------------------------
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_APP_DIR)
# Prefer: (1) runs/detect/helmet_detection2/weights/best.pt  (2) helmet_detection_yolov11.pt  (3) app/yolov8n.pt
_trained_best = os.path.join(_PROJECT_ROOT, "runs", "detect", "helmet_detection2", "weights", "best.pt")
_trained_named = os.path.join(_PROJECT_ROOT, "helmet_detection_yolov11.pt")
_default_coco = os.path.join(_APP_DIR, "yolov8n.pt")

def _resolve_model_path():
    """Resolve which model file to use; prefer latest trained run, then named copy, then default."""
    candidates = []
    if os.path.exists(_trained_best):
        candidates.append((os.path.getmtime(_trained_best), os.path.abspath(_trained_best)))
    if os.path.exists(_trained_named):
        candidates.append((os.path.getmtime(_trained_named), os.path.abspath(_trained_named)))
    # Latest run in runs/detect/*/weights/best.pt (so new training is picked up)
    _runs_dir = os.path.join(_PROJECT_ROOT, "runs", "detect")
    if os.path.isdir(_runs_dir):
        for name in os.listdir(_runs_dir):
            best = os.path.join(_runs_dir, name, "weights", "best.pt")
            if os.path.exists(best):
                candidates.append((os.path.getmtime(best), os.path.abspath(best)))
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    for rel in ["runs/detect/helmet_detection2/weights/best.pt", "helmet_detection_yolov11.pt"]:
        p = os.path.abspath(os.path.join(_PROJECT_ROOT, rel)) if not os.path.isabs(rel) else rel
        if os.path.exists(p):
            return p
    return os.path.abspath(_default_coco)

HELMET_MODEL_PATH = _resolve_model_path()
DETECTION_ENABLED = True  # Set False to stream raw video only
DETECTION_CONFIDENCE = 0.35  # Lower = more detections (0.35 helps trained models)

# Stream tuning
DETECT_EVERY_N_FRAMES = 2  # Submit frame for detection every Nth frame (async, so no blocking)
STREAM_JPEG_QUALITY = 72   # Lower = smaller frames, less lag (70-80 is a good range)
STREAM_SIZE = (640, 480)   # (width, height); smaller = less data, e.g. (480, 360)
RTSP_GRAB_SKIP = 3         # Zone 2: skip this many RTSP buffer frames (lower = fresher, 2-5)
TARGET_STREAM_FPS = 20     # Cap stream frame rate (20fps is smooth, saves CPU)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Database setup
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "accounts.db")
if not os.path.exists(DB_PATH):
    open(DB_PATH, "w").close()

# Initialize database
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# ---------------------------------------------------------------------------
# Migration: if old schema exists (username TEXT PRIMARY KEY, no id column),
# recreate the users table with the new schema and migrate existing data.
# ---------------------------------------------------------------------------
cursor.execute("PRAGMA table_info(users)")
cols = {row[1] for row in cursor.fetchall()}
if cols and 'id' not in cols:
    print("⚙️  Migrating users table to new schema (adding id column)...")
    cursor.execute("ALTER TABLE users RENAME TO _users_old")
    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
        INSERT INTO users (username, password, email)
        SELECT username, password, email FROM _users_old
    """)
    cursor.execute("DROP TABLE _users_old")
    conn.commit()
    print("✅ Users table migrated successfully")
else:
    # Create users table (new installations)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

# Create cameras table (defines available cameras in the system)
cursor.execute("""
CREATE TABLE IF NOT EXISTS cameras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id INTEGER UNIQUE NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    url TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Create user_cameras table (links users to cameras they can access)
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_cameras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    camera_id INTEGER NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE,
    UNIQUE(user_id, camera_id)
)
""")

# Insert default cameras if they don't exist
cursor.execute("SELECT COUNT(*) FROM cameras")
if cursor.fetchone()[0] == 0:
    cursor.executemany("""
        INSERT INTO cameras (zone_id, name, type, url, is_active) 
        VALUES (?, ?, ?, ?, ?)
    """, [
        (1, 'Safe Zone 1 - Webcam', 'webcam', None, 1),
        (2, 'Safe Zone 2 - Axis Camera', 'rtsp', AXIS_CAMERA_2_URL, 1),
        (3, 'Safe Zone 3 - Reserved', 'none', None, 0),
        (4, 'Safe Zone 4 - Reserved', 'none', None, 0),
    ])
    print("✅ Default cameras initialized in database")

conn.commit()

# ---------------------------------------------------------------------------
# Seed: Make sure user 'ah' has both cameras assigned (webcam + Axis)
# ---------------------------------------------------------------------------
cursor.execute("SELECT id FROM users WHERE username='ah'")
_ah_row = cursor.fetchone()
if _ah_row:
    _ah_id = _ah_row[0]
    cursor.execute("SELECT COUNT(*) FROM user_cameras WHERE user_id=?", (_ah_id,))
    if cursor.fetchone()[0] == 0:
        # Assign all active cameras to 'ah'
        cursor.execute("SELECT id FROM cameras WHERE is_active=1")
        for (cam_id,) in cursor.fetchall():
            try:
                cursor.execute("INSERT INTO user_cameras (user_id, camera_id) VALUES (?, ?)", (_ah_id, cam_id))
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        print("✅ Assigned cameras to existing user 'ah'")

# Global camera objects
camera1 = None
camera2 = None
camera1_running = False
camera2_running = False

# Helmet detector (lazy-loaded so server starts even if model fails)
_helmet_detector = None

def _get_helmet_detector():
    """Create or return the shared helmet detector."""
    global _helmet_detector
    if _helmet_detector is not None:
        return _helmet_detector
    if not DETECTION_ENABLED:
        return None
    try:
        try:
            from .helmet_detector import HelmetDetector
        except ImportError:
            # When run as __main__ (python -m app.server), same-dir import may need app on path
            import sys
            if _APP_DIR not in sys.path:
                sys.path.insert(0, _APP_DIR)
            from helmet_detector import HelmetDetector
        path = HELMET_MODEL_PATH if os.path.exists(HELMET_MODEL_PATH) else None
        if path:
            print(f"[Detection] Loading model: {path}")
        else:
            print(f"[Detection] Model path not found: {HELMET_MODEL_PATH}, using default")
        _helmet_detector = HelmetDetector(model_path=path, confidence_threshold=DETECTION_CONFIDENCE)
        if _helmet_detector.model_loaded:
            print("[Detection] Model loaded successfully (conf >= %.2f)" % DETECTION_CONFIDENCE)
        else:
            print("[Detection] Model failed to load - streams will show raw video")
            _helmet_detector = None
    except Exception as e:
        print(f"[Detection] Error: {e}")
        import traceback
        traceback.print_exc()
        _helmet_detector = None
    return _helmet_detector


def _run_detection_and_annotate(frame):
    """Run helmet/person detection and return (annotated_frame, person_count, helmet_count, violation_count)."""
    detector = _get_helmet_detector()
    if detector is None:
        return frame, 0, 0, 0
    try:
        annotated, detections, violation_count = detector.detect(frame)
        person_count = sum(1 for d in detections if d.get("class", "").lower() == "person")
        helmet_count = sum(1 for d in detections if d.get("class", "").lower() in ["hardhat", "helmet", "safetyhelmet"])
        return annotated, person_count, helmet_count, violation_count
    except Exception as e:
        print(f"Detection error: {e}")
        return frame, 0, 0, 0

# ---------------------------------------------------------------------------
# Async detection: YOLO runs in background so video streaming never blocks
# ---------------------------------------------------------------------------
_detection_lock = threading.Lock()


class _AsyncDetector:
    """Run YOLO in a persistent background thread. Streaming never waits for inference."""

    def __init__(self):
        self._lock = threading.Lock()
        self._frame = None
        self._new_frame = threading.Event()
        self._detections = []
        self._person = 0
        self._helmet = 0
        self._violation = 0
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def submit(self, frame):
        """Hand off the latest frame. Non-blocking; overwrites any queued frame."""
        with self._lock:
            self._frame = frame.copy()
        self._new_frame.set()

    def _worker(self):
        while True:
            self._new_frame.wait()
            self._new_frame.clear()
            with self._lock:
                frame = self._frame
            if frame is None:
                continue
            detector = _get_helmet_detector()
            if not detector:
                continue
            try:
                with _detection_lock:
                    _, detections, violation = detector.detect(frame)
                p = sum(1 for d in detections if d.get("class", "").lower() == "person")
                h = sum(1 for d in detections if d.get("class", "").lower() in ["hardhat", "helmet", "safetyhelmet"])
                with self._lock:
                    self._detections = detections
                    self._person = p
                    self._helmet = h
                    self._violation = violation
            except Exception as e:
                print(f"Detection thread error: {e}")

    @property
    def results(self):
        """Return latest results instantly (never blocks)."""
        with self._lock:
            return list(self._detections), self._person, self._helmet, self._violation


def _draw_detections_on_frame(frame, detections):
    """Draw bounding boxes + labels from a detections list."""
    for det in detections:
        bbox = det["bbox"]
        conf = det["confidence"]
        cls = det["class"]
        color = (255, 100, 0) if cls.lower() == "person" else (0, 255, 0)
        cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
        label = f"{cls} {conf:.2f}"
        sz, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.rectangle(frame, (bbox[0], bbox[1] - sz[1] - 10), (bbox[0] + sz[0], bbox[1]), color, -1)
        cv2.putText(frame, label, (bbox[0], bbox[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)


def init_cameras():
    """Initialize cameras for Zone 1 and Zone 2"""
    global camera1, camera2, camera1_running, camera2_running
    
    # Initialize Zone 1 camera (local webcam) – try indices 0, 1, 2
    indices_to_try = [ZONE1_CAMERA_INDEX] + [i for i in [0, 1, 2] if i != ZONE1_CAMERA_INDEX]
    for idx in indices_to_try:
        if camera1_running:
            break
        try:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    camera1 = cap
                    camera1_running = True
                    print(f"Zone 1 camera initialized successfully (index {idx})")
                    break
                else:
                    cap.release()
            else:
                cap.release()
        except Exception as e:
            print(f"Zone 1 camera index {idx} error: {e}")
    if not camera1_running:
        print("Zone 1: no local webcam found on indices 0, 1, or 2")
    
    # Initialize Zone 2 camera (Axis RTSP)
    if AXIS_CAMERA_2_URL:
        try:
            camera2 = cv2.VideoCapture(AXIS_CAMERA_2_URL, cv2.CAP_FFMPEG)
            if camera2.isOpened():
                try:
                    camera2.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except:
                    pass
                ret, frame = camera2.read()
                if ret and frame is not None:
                    camera2_running = True
                    print("Zone 2 camera (Axis) initialized successfully")
                else:
                    camera2.release()
                    camera2 = None
                    print("Zone 2 camera opened but cannot read frames")
            else:
                camera2 = None
                print("Zone 2 camera not available")
        except Exception as e:
            print(f"Zone 2 camera initialization error: {e}")
            camera2 = None
    else:
        print("Zone 2 camera URL not configured")

def _open_webcam():
    """Try to open local webcam on indices 0, 1, 2. Returns VideoCapture or None."""
    indices = [ZONE1_CAMERA_INDEX] + [i for i in [0, 1, 2] if i != ZONE1_CAMERA_INDEX]
    for idx in indices:
        idx = int(idx)
        try:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    return cap
                cap.release()
        except Exception:
            pass
    return None


def generate_frames(zone_id):
    """Generate MJPEG frames. Detection runs in a background thread so streaming never blocks."""
    global camera1, camera1_running

    frame_interval = 1.0 / TARGET_STREAM_FPS

    # ---- Zone 2 (Axis RTSP) ----
    if zone_id == 2:
        cap = None
        try:
            if not AXIS_CAMERA_2_URL:
                raise RuntimeError("Zone 2 URL not configured")
            cap = cv2.VideoCapture(AXIS_CAMERA_2_URL, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                raise RuntimeError("Axis camera not opened")
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass

            async_det = _AsyncDetector()
            frame_count = 0

            while True:
                t0 = time.time()
                try:
                    for _ in range(RTSP_GRAB_SKIP):
                        cap.grab()
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        time.sleep(0.05)
                        continue
                    frame = cv2.resize(frame, STREAM_SIZE)

                    if frame_count % DETECT_EVERY_N_FRAMES == 0:
                        async_det.submit(frame)

                    detections, p, h, v = async_det.results
                    _draw_detections_on_frame(frame, detections)

                    ts = datetime.now().strftime("%H:%M:%S")
                    cv2.putText(frame, f"LIVE {ts}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    status = f"Person: {p}  Helmet: {h}  Violations: {v}"
                    cv2.putText(frame, status, (10, frame.shape[0] - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                (0, 255, 0) if v == 0 else (0, 0, 255), 2)

                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, STREAM_JPEG_QUALITY])
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                    frame_count += 1

                    elapsed = time.time() - t0
                    if elapsed < frame_interval:
                        time.sleep(frame_interval - elapsed)
                except Exception as e:
                    print(f"Zone 2 stream error: {e}")
                    time.sleep(0.5)
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
        return

    # ---- Zone 1 (Webcam) ----
    if zone_id == 1:
        cap = camera1
        if not cap or not camera1_running:
            cap = _open_webcam()
            if cap is None:
                while True:
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(frame, "Zone 1: No webcam found", (80, 220),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
                    cv2.putText(frame, "Try indices 0,1,2 in server.py", (60, 260),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                    _, buffer = cv2.imencode('.jpg', frame)
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                    time.sleep(0.5)
                return

        async_det = _AsyncDetector()
        frame_count = 0

        while True:
            t0 = time.time()
            try:
                ret, frame = cap.read()
                if not ret or frame is None:
                    time.sleep(0.03)
                    continue
                frame = cv2.resize(frame, STREAM_SIZE)

                if frame_count % DETECT_EVERY_N_FRAMES == 0:
                    async_det.submit(frame)

                detections, p, h, v = async_det.results
                _draw_detections_on_frame(frame, detections)

                ts = datetime.now().strftime("%H:%M:%S")
                cv2.putText(frame, f"LIVE {ts}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                status = f"Person: {p}  Helmet: {h}  Violations: {v}"
                cv2.putText(frame, status, (10, frame.shape[0] - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                            (0, 255, 0) if v == 0 else (0, 0, 255), 2)

                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, STREAM_JPEG_QUALITY])
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                frame_count += 1

                elapsed = time.time() - t0
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)
            except Exception as e:
                print(f"Zone 1 stream error: {e}")
                time.sleep(0.5)
        return

    # ---- Invalid zone: placeholder ----
    while True:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, f"Camera Zone {zone_id} not available", (50, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.1)

@app.route('/stream/<int:zone_id>')
def video_stream(zone_id):
    """Serve MJPEG stream for specified zone"""
    if zone_id not in [1, 2]:
        return jsonify({"error": "Invalid zone ID"}), 400
    
    return Response(
        generate_frames(zone_id),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/login', methods=['POST'])
def login():
    """Handle user login and return user's assigned cameras"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400
        
        cursor.execute("SELECT id, username, email FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        
        if user:
            user_id, username, email = user
            
            # Get user's assigned cameras
            cursor.execute("""
                SELECT c.id, c.zone_id, c.name, c.type, c.is_active
                FROM cameras c
                INNER JOIN user_cameras uc ON c.id = uc.camera_id
                WHERE uc.user_id = ?
                ORDER BY c.zone_id
            """, (user_id,))
            cameras = cursor.fetchall()
            
            camera_list = [{
                'id': cam[0],
                'zone_id': cam[1],
                'name': cam[2],
                'type': cam[3],
                'is_active': bool(cam[4])
            } for cam in cameras]
            
            return jsonify({
                "success": True,
                "user": {
                    "id": user_id,
                    "username": username,
                    "email": email
                },
                "cameras": camera_list
            }), 200
        else:
            return jsonify({"error": "Invalid username or password"}), 401
    except Exception as e:
        print(f"Login error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Server error"}), 500

@app.route('/api/register', methods=['POST'])
def register():
    """Handle user registration and optionally assign default cameras"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        email = data.get('email', '').strip()
        assign_all_cameras = data.get('assign_all_cameras', True)  # Default: give access to all cameras
        
        if not username or not password or not email:
            return jsonify({"error": "All fields required"}), 400
        
        try:
            cursor.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                         (username, password, email))
            conn.commit()
            
            # Get the new user's ID
            cursor.execute("SELECT id FROM users WHERE username=?", (username,))
            user_id = cursor.fetchone()[0]
            
            # Optionally assign cameras to new user
            if assign_all_cameras:
                cursor.execute("SELECT id FROM cameras WHERE is_active = 1")
                active_cameras = cursor.fetchall()
                for (camera_id,) in active_cameras:
                    cursor.execute("INSERT INTO user_cameras (user_id, camera_id) VALUES (?, ?)",
                                 (user_id, camera_id))
                conn.commit()
                print(f"✅ Assigned {len(active_cameras)} cameras to new user: {username}")
            
            return jsonify({
                "success": True,
                "user": {
                    "id": user_id,
                    "username": username,
                    "email": email
                },
                "message": f"Account created successfully{' with access to all cameras' if assign_all_cameras else ''}"
            }), 200
        except sqlite3.IntegrityError:
            return jsonify({"error": "Username already exists"}), 409
    except Exception as e:
        print(f"Register error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Server error"}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "camera1": camera1_running,
        "camera2": camera2_running
    }), 200

# ---------------------------------------------------------------------------
# Camera Management API
# ---------------------------------------------------------------------------

@app.route('/api/cameras', methods=['GET'])
def get_all_cameras():
    """Get all cameras in the system"""
    try:
        cursor.execute("SELECT id, zone_id, name, type, url, is_active FROM cameras ORDER BY zone_id")
        cameras = cursor.fetchall()
        
        camera_list = [{
            'id': cam[0],
            'zone_id': cam[1],
            'name': cam[2],
            'type': cam[3],
            'url': cam[4],
            'is_active': bool(cam[5])
        } for cam in cameras]
        
        return jsonify({"cameras": camera_list}), 200
    except Exception as e:
        print(f"Get cameras error: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/api/users/<int:user_id>/cameras', methods=['GET'])
def get_user_cameras(user_id):
    """Get cameras assigned to a specific user"""
    try:
        cursor.execute("""
            SELECT c.id, c.zone_id, c.name, c.type, c.is_active
            FROM cameras c
            INNER JOIN user_cameras uc ON c.id = uc.camera_id
            WHERE uc.user_id = ?
            ORDER BY c.zone_id
        """, (user_id,))
        cameras = cursor.fetchall()
        
        camera_list = [{
            'id': cam[0],
            'zone_id': cam[1],
            'name': cam[2],
            'type': cam[3],
            'is_active': bool(cam[4])
        } for cam in cameras]
        
        return jsonify({"user_id": user_id, "cameras": camera_list}), 200
    except Exception as e:
        print(f"Get user cameras error: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/api/users/<int:user_id>/cameras', methods=['POST'])
def assign_camera_to_user(user_id):
    """Assign a camera to a user"""
    try:
        data = request.get_json()
        camera_id = data.get('camera_id')
        
        if not camera_id:
            return jsonify({"error": "camera_id required"}), 400
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id=?", (user_id,))
        if not cursor.fetchone():
            return jsonify({"error": "User not found"}), 404
        
        # Check if camera exists
        cursor.execute("SELECT id FROM cameras WHERE id=?", (camera_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Camera not found"}), 404
        
        try:
            cursor.execute("INSERT INTO user_cameras (user_id, camera_id) VALUES (?, ?)",
                         (user_id, camera_id))
            conn.commit()
            return jsonify({"success": True, "message": "Camera assigned to user"}), 200
        except sqlite3.IntegrityError:
            return jsonify({"error": "Camera already assigned to this user"}), 409
    except Exception as e:
        print(f"Assign camera error: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/api/users/<int:user_id>/cameras/<int:camera_id>', methods=['DELETE'])
def remove_camera_from_user(user_id, camera_id):
    """Remove a camera from a user's access"""
    try:
        cursor.execute("DELETE FROM user_cameras WHERE user_id=? AND camera_id=?",
                     (user_id, camera_id))
        conn.commit()
        
        if cursor.rowcount > 0:
            return jsonify({"success": True, "message": "Camera removed from user"}), 200
        else:
            return jsonify({"error": "Assignment not found"}), 404
    except Exception as e:
        print(f"Remove camera error: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/api/users', methods=['GET'])
def get_all_users():
    """Get all users with their assigned cameras"""
    try:
        cursor.execute("SELECT id, username, email, created_at FROM users")
        users = cursor.fetchall()
        
        user_list = []
        for user in users:
            user_id, username, email, created_at = user
            
            # Get cameras for this user
            cursor.execute("""
                SELECT c.id, c.zone_id, c.name
                FROM cameras c
                INNER JOIN user_cameras uc ON c.id = uc.camera_id
                WHERE uc.user_id = ?
                ORDER BY c.zone_id
            """, (user_id,))
            cameras = cursor.fetchall()
            
            user_list.append({
                'id': user_id,
                'username': username,
                'email': email,
                'created_at': created_at,
                'cameras': [{'id': c[0], 'zone_id': c[1], 'name': c[2]} for c in cameras]
            })
        
        return jsonify({"users": user_list}), 200
    except Exception as e:
        print(f"Get users error: {e}")
        return jsonify({"error": "Server error"}), 500


@app.route('/')
def index():
    """Root route – frontend runs on port 3000."""
    return jsonify({
        "message": "Workplace Safety Monitor API",
        "docs": "Use /api/health, /api/login, /stream/1, /stream/2. Frontend: http://localhost:3000"
    }), 200


if __name__ == '__main__':
    print("Initializing cameras...")
    init_cameras()
    print(f"Camera 1 (Zone 1): {'Running' if camera1_running else 'Not available'}")
    print(f"Camera 2 (Zone 2): {'Running' if camera2_running else 'Not available'}")
    if DETECTION_ENABLED:
        print(f"Detection model path: {HELMET_MODEL_PATH}")
        print(f"Model file exists: {os.path.exists(HELMET_MODEL_PATH)}")
        d = _get_helmet_detector()
        print(f"Helmet/person detection: {'Enabled' if d and d.model_loaded else 'Disabled (streams will show raw video)'}")
    print("Starting Flask server on http://localhost:5000")
    # use_reloader=False so the webcam is only opened once (avoids Zone 1 failing after restart on Windows)
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True, use_reloader=False)
