"""
Flask backend server for Workplace Safety Monitoring System
Serves camera streams with helmet/person detection and handles authentication
"""
import cv2
import sqlite3
import os
import threading
import numpy as np
from flask import Flask, Response, jsonify, request, send_file
from flask_cors import CORS
import time
import json
from datetime import datetime
from urllib.parse import urlparse

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
# Prefer: (1) runs/detect/helmet_detection2/weights/best.pt  (2) helmet_detection_yolov11.pt  (3) backend/yolov8n.pt
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

# Create cameras table with config JSON column for type-specific settings
cursor.execute("""
CREATE TABLE IF NOT EXISTS cameras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id INTEGER UNIQUE NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    url TEXT,
    config TEXT DEFAULT '{}',
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Migration: add config column to existing databases that don't have it
cursor.execute("PRAGMA table_info(cameras)")
_cam_cols = {row[1] for row in cursor.fetchall()}
if 'config' not in _cam_cols:
    cursor.execute("ALTER TABLE cameras ADD COLUMN config TEXT DEFAULT '{}'")
    cursor.execute("SELECT id, type, url FROM cameras")
    for _cid, _ctype, _curl in cursor.fetchall():
        if _ctype == 'webcam':
            _cfg = json.dumps({"device_index": 0})
        elif _ctype == 'rtsp' and _curl:
            try:
                _p = urlparse(_curl)
                _cfg = json.dumps({"host": _p.hostname or "", "port": _p.port or 554,
                                   "username": _p.username or "", "password": _p.password or "",
                                   "path": _p.path or ""})
            except Exception:
                _cfg = json.dumps({"url": _curl})
        else:
            _cfg = '{}'
        cursor.execute("UPDATE cameras SET config=? WHERE id=?", (_cfg, _cid))
    conn.commit()
    print("✅ Migrated cameras table: added config column")

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

# Create violations table for storing snapshot incidents
cursor.execute("""
CREATE TABLE IF NOT EXISTS violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id INTEGER NOT NULL,
    person_count INTEGER DEFAULT 0,
    helmet_count INTEGER DEFAULT 0,
    violation_count INTEGER DEFAULT 0,
    max_person_confidence REAL DEFAULT 0,
    snapshot_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE
)
""")

# User settings: violation_auto_delete = 'none'|'day'|'week'|'month'|'year'
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER PRIMARY KEY,
    violation_auto_delete TEXT DEFAULT 'none',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
""")

# Snapshot directory for violation images
VIOLATIONS_DIR = os.path.join(_PROJECT_ROOT, "violations")
os.makedirs(VIOLATIONS_DIR, exist_ok=True)

SNAPSHOT_CONFIDENCE = 0.80
SNAPSHOT_COOLDOWN = 60  # seconds between snapshots per camera (1 minute)

# Seed default cameras on first run
def _build_axis_config():
    if not AXIS_CAMERA_2_URL:
        return '{}'
    try:
        _p = urlparse(AXIS_CAMERA_2_URL)
        return json.dumps({"host": _p.hostname or "", "port": _p.port or 554,
                           "username": _p.username or "", "password": _p.password or "",
                           "path": _p.path or ""})
    except Exception:
        return json.dumps({"url": AXIS_CAMERA_2_URL})

cursor.execute("SELECT COUNT(*) FROM cameras")
if cursor.fetchone()[0] == 0:
    cursor.executemany("""
        INSERT INTO cameras (zone_id, name, type, url, config, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        (1, 'Safe Zone 1 - Webcam', 'webcam', None, json.dumps({"device_index": 0}), 1),
        (2, 'Safe Zone 2 - Axis Camera', 'rtsp', AXIS_CAMERA_2_URL, _build_axis_config(), 1),
    ])
    print("✅ Default cameras seeded")

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

conn.close()

_thread_local = threading.local()

def get_db():
    """Return a thread-local database connection."""
    if not hasattr(_thread_local, 'db') or _thread_local.db is None:
        _thread_local.db = sqlite3.connect(DB_PATH)
    return _thread_local.db

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
            # When run as __main__ (python -m backend.server), same-dir import may need backend on path
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
# Live stats: per-camera person/helmet/violation, aggregated for dashboard
# ---------------------------------------------------------------------------
_detection_lock = threading.Lock()
_live_stats_lock = threading.Lock()
_live_stats = {}  # {camera_id: {"person": int, "helmet": int, "violation": int}}
_snapshot_cooldown = {}  # {camera_id: last_snapshot_timestamp}
_snapshot_lock = threading.Lock()


def _should_save_snapshot(camera_id, detections, violation_count):
    """Check if we should save a violation snapshot (confidence >= 0.80 + cooldown)."""
    if violation_count <= 0:
        return False
    high_conf_persons = [
        d for d in detections
        if d.get("class", "").lower() == "person" and d.get("confidence", 0) >= SNAPSHOT_CONFIDENCE
    ]
    if not high_conf_persons:
        return False
    now = time.time()
    with _snapshot_lock:
        last = _snapshot_cooldown.get(camera_id, 0)
        if now - last < SNAPSHOT_COOLDOWN:
            return False
        _snapshot_cooldown[camera_id] = now
    return True


def _save_violation_snapshot(camera_id, frame, detections, person_count, helmet_count, violation_count):
    """Save annotated frame to disk and record in DB."""
    try:
        now = datetime.now()
        date_dir = os.path.join(VIOLATIONS_DIR, now.strftime("%Y-%m-%d"))
        os.makedirs(date_dir, exist_ok=True)
        filename = f"cam{camera_id}_{now.strftime('%H%M%S')}.jpg"
        filepath = os.path.join(date_dir, filename)
        cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        rel_path = f"violations/{now.strftime('%Y-%m-%d')}/{filename}"

        max_person_conf = max(
            (d["confidence"] for d in detections if d.get("class", "").lower() == "person"),
            default=0
        )

        db = get_db()
        c = db.cursor()
        c.execute("""
            INSERT INTO violations (camera_id, person_count, helmet_count, violation_count, max_person_confidence, snapshot_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (camera_id, person_count, helmet_count, violation_count, round(max_person_conf, 3), rel_path))
        db.commit()
        print(f"[Snapshot] Saved violation: {rel_path} (confidence {max_person_conf:.2f})")
    except Exception as e:
        print(f"[Snapshot] Error saving: {e}")


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


# ---------------------------------------------------------------------------
# Dynamic camera: open any camera type from DB config
# ---------------------------------------------------------------------------

def _get_camera_from_db(camera_id):
    """Look up camera type and config from the database."""
    db = get_db()
    c = db.cursor()
    c.execute("SELECT id, type, config, is_active, name FROM cameras WHERE id=?", (camera_id,))
    row = c.fetchone()
    if not row:
        return None
    return {"id": row[0], "type": row[1], "config": json.loads(row[2] or '{}'),
            "is_active": bool(row[3]), "name": row[4]}


def _open_camera_by_type(cam_type, config):
    """Open a cv2.VideoCapture based on camera type and its stored config."""
    try:
        if cam_type == 'webcam':
            idx = int(config.get('device_index', 0))
            for try_idx in [idx] + [i for i in [0, 1, 2] if i != idx]:
                cap = cv2.VideoCapture(try_idx)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        print(f"[Camera] Webcam opened on index {try_idx}")
                        return cap
                    cap.release()
            return None

        elif cam_type == 'rtsp':
            host = config.get('host', '')
            if host:
                port = config.get('port', 554)
                user = config.get('username', '')
                pwd = config.get('password', '')
                path = config.get('path', '')
                if user:
                    url = f"rtsp://{user}:{pwd}@{host}:{port}{path}"
                else:
                    url = f"rtsp://{host}:{port}{path}"
            elif config.get('url'):
                url = config['url']
            else:
                print("[Camera] RTSP: no host or url in config")
                return None
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass
            if cap.isOpened():
                print(f"[Camera] RTSP opened: {host or url}")
                return cap
            print(f"[Camera] RTSP failed to open: {host or url}")
            return None

        elif cam_type == 'http':
            url = config.get('url', '')
            if not url:
                return None
            user = config.get('username', '')
            if user:
                p = urlparse(url)
                netloc = f"{user}:{config.get('password', '')}@{p.hostname}"
                if p.port:
                    netloc += f":{p.port}"
                url = p._replace(netloc=netloc).geturl()
            cap = cv2.VideoCapture(url)
            if cap.isOpened():
                print("[Camera] HTTP stream opened")
                return cap
            return None

        elif cam_type == 'hls':
            url = config.get('url', '')
            if not url:
                return None
            cap = cv2.VideoCapture(url)
            if cap.isOpened():
                print("[Camera] HLS stream opened")
                return cap
            return None
    except Exception as e:
        print(f"[Camera] Error opening {cam_type}: {e}")
    return None


def _placeholder_stream(msg):
    """Yield a static placeholder frame with a message."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, msg, (40, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    _, buf = cv2.imencode('.jpg', frame)
    data = buf.tobytes()
    while True:
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + data + b'\r\n')
        time.sleep(1)


def generate_frames(camera_id):
    """Generate MJPEG frames for any camera type. Detection runs in background thread."""
    cam_data = _get_camera_from_db(camera_id)
    if not cam_data:
        yield from _placeholder_stream("Camera not found")
        return
    if not cam_data['is_active']:
        yield from _placeholder_stream(f"{cam_data['name']}: Inactive")
        return

    cam_type = cam_data['type']
    config = cam_data['config']
    needs_grab_skip = cam_type == 'rtsp'
    frame_interval = 1.0 / TARGET_STREAM_FPS

    cap = _open_camera_by_type(cam_type, config)
    if cap is None:
        yield from _placeholder_stream(f"Cannot connect ({cam_type})")
        return

    try:
        async_det = _AsyncDetector()
        frame_count = 0

        while True:
            t0 = time.time()
            try:
                if needs_grab_skip:
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
                with _live_stats_lock:
                    _live_stats[camera_id] = {"person": p, "helmet": h, "violation": v}
                _draw_detections_on_frame(frame, detections)

                if _should_save_snapshot(camera_id, detections, v):
                    _save_violation_snapshot(camera_id, frame.copy(), detections, p, h, v)

                ts = datetime.now().strftime("%H:%M:%S")
                cv2.putText(frame, f"LIVE {ts}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                status = f"Person: {p}  Helmet: {h}  Violations: {v}"
                cv2.putText(frame, status, (10, frame.shape[0] - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                            (0, 255, 0) if v == 0 else (0, 0, 255), 2)

                _, buffer = cv2.imencode('.jpg', frame,
                                         [cv2.IMWRITE_JPEG_QUALITY, STREAM_JPEG_QUALITY])
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                       + buffer.tobytes() + b'\r\n')
                frame_count += 1

                elapsed = time.time() - t0
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)
            except Exception as e:
                print(f"[Stream {camera_id}] Error: {e}")
                time.sleep(0.5)
    finally:
        with _live_stats_lock:
            _live_stats.pop(camera_id, None)
        try:
            cap.release()
        except Exception:
            pass


@app.route('/stream/<int:camera_id>')
def video_stream(camera_id):
    """Serve MJPEG stream for any camera by its database ID."""
    return Response(
        generate_frames(camera_id),
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
        
        db = get_db()
        c = db.cursor()
        c.execute("SELECT id, username, email FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        
        if user:
            user_id, username, email = user
            
            c.execute("""
                SELECT c.id, c.zone_id, c.name, c.type, c.is_active
                FROM cameras c
                INNER JOIN user_cameras uc ON c.id = uc.camera_id
                WHERE uc.user_id = ?
                ORDER BY c.zone_id
            """, (user_id,))
            cameras = c.fetchall()
            
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
        assign_all_cameras = data.get('assign_all_cameras', True)
        
        if not username or not password or not email:
            return jsonify({"error": "All fields required"}), 400
        
        db = get_db()
        c = db.cursor()
        try:
            c.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                         (username, password, email))
            db.commit()
            
            c.execute("SELECT id FROM users WHERE username=?", (username,))
            user_id = c.fetchone()[0]
            
            if assign_all_cameras:
                c.execute("SELECT id FROM cameras WHERE is_active = 1")
                active_cameras = c.fetchall()
                for (camera_id,) in active_cameras:
                    c.execute("INSERT INTO user_cameras (user_id, camera_id) VALUES (?, ?)",
                                 (user_id, camera_id))
                db.commit()
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
    """Health check endpoint – reports active camera count from DB."""
    db = get_db()
    c = db.cursor()
    c.execute("SELECT COUNT(*) FROM cameras WHERE is_active=1")
    active = c.fetchone()[0]
    return jsonify({"status": "ok", "active_cameras": active}), 200


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Live compliance/violation stats. If user_id is provided, only include that user's assigned cameras."""
    user_id = request.args.get('user_id', type=int)
    with _live_stats_lock:
        data = dict(_live_stats)

    if user_id is not None:
        db = get_db()
        c = db.cursor()
        c.execute("SELECT camera_id FROM user_cameras WHERE user_id=?", (user_id,))
        allowed_camera_ids = {row[0] for row in c.fetchall()}
        data = {cid: s for cid, s in data.items() if cid in allowed_camera_ids}

    compliant = sum(s.get("helmet", 0) for s in data.values())
    violations = sum(s.get("violation", 0) for s in data.values())
    return jsonify({"compliant": compliant, "violations": violations}), 200


# ---------------------------------------------------------------------------
# Camera Management API
# ---------------------------------------------------------------------------

def _safe_config(config_str):
    """Parse config JSON and strip passwords before sending to frontend."""
    try:
        cfg = json.loads(config_str or '{}')
    except (json.JSONDecodeError, TypeError):
        cfg = {}
    safe = dict(cfg)
    if 'password' in safe:
        safe['password'] = '••••••' if safe['password'] else ''
    return safe


@app.route('/api/cameras', methods=['GET'])
def get_all_cameras():
    """Get all cameras in the system (credentials stripped)."""
    try:
        db = get_db()
        c = db.cursor()
        c.execute("SELECT id, zone_id, name, type, config, is_active FROM cameras ORDER BY zone_id")
        cameras = c.fetchall()
        camera_list = [{
            'id': cam[0], 'zone_id': cam[1], 'name': cam[2],
            'type': cam[3], 'config': _safe_config(cam[4]),
            'is_active': bool(cam[5])
        } for cam in cameras]
        return jsonify({"cameras": camera_list}), 200
    except Exception as e:
        print(f"Get cameras error: {e}")
        return jsonify({"error": "Server error"}), 500


@app.route('/api/cameras', methods=['POST'])
def create_camera():
    """Create a new camera. Accepts {name, type, config, is_active?}."""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        cam_type = data.get('type', '').strip()
        config = data.get('config', {})
        is_active = data.get('is_active', True)

        if not name or not cam_type:
            return jsonify({"error": "name and type are required"}), 400
        if cam_type not in ('webcam', 'rtsp', 'http', 'hls'):
            return jsonify({"error": f"Unsupported type: {cam_type}. Use webcam, rtsp, http, or hls"}), 400

        db = get_db()
        c = db.cursor()
        c.execute("SELECT COALESCE(MAX(zone_id), 0) + 1 FROM cameras")
        next_zone = c.fetchone()[0]

        config_json = json.dumps(config) if isinstance(config, dict) else config

        c.execute("""
            INSERT INTO cameras (zone_id, name, type, config, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, (next_zone, name, cam_type, config_json, 1 if is_active else 0))
        db.commit()
        cam_id = c.lastrowid

        return jsonify({
            "success": True,
            "camera": {"id": cam_id, "zone_id": next_zone, "name": name,
                       "type": cam_type, "is_active": bool(is_active)}
        }), 201
    except Exception as e:
        print(f"Create camera error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": "Server error"}), 500


@app.route('/api/cameras/<int:cam_id>', methods=['PUT'])
def update_camera(cam_id):
    """Update an existing camera's name, type, config, and/or is_active."""
    try:
        data = request.get_json()
        db = get_db()
        c = db.cursor()
        c.execute("SELECT id FROM cameras WHERE id=?", (cam_id,))
        if not c.fetchone():
            return jsonify({"error": "Camera not found"}), 404

        fields, values = [], []
        if 'name' in data:
            fields.append("name=?"); values.append(data['name'].strip())
        if 'type' in data:
            cam_type = data['type'].strip()
            if cam_type not in ('webcam', 'rtsp', 'http', 'hls'):
                return jsonify({"error": f"Unsupported type: {cam_type}"}), 400
            fields.append("type=?"); values.append(cam_type)
        if 'config' in data:
            cfg = data['config']
            if isinstance(cfg, dict) and cfg.get('password', '').startswith('••'):
                c.execute("SELECT config FROM cameras WHERE id=?", (cam_id,))
                old_cfg = json.loads(c.fetchone()[0] or '{}')
                cfg['password'] = old_cfg.get('password', '')
            fields.append("config=?")
            values.append(json.dumps(cfg) if isinstance(cfg, dict) else cfg)
        if 'is_active' in data:
            fields.append("is_active=?"); values.append(1 if data['is_active'] else 0)

        if not fields:
            return jsonify({"error": "No fields to update"}), 400

        values.append(cam_id)
        c.execute(f"UPDATE cameras SET {', '.join(fields)} WHERE id=?", values)
        db.commit()
        return jsonify({"success": True, "message": "Camera updated"}), 200
    except Exception as e:
        print(f"Update camera error: {e}")
        return jsonify({"error": "Server error"}), 500


@app.route('/api/cameras/<int:cam_id>', methods=['DELETE'])
def delete_camera(cam_id):
    """Delete a camera and its user assignments."""
    try:
        db = get_db()
        c = db.cursor()
        c.execute("DELETE FROM user_cameras WHERE camera_id=?", (cam_id,))
        c.execute("DELETE FROM cameras WHERE id=?", (cam_id,))
        db.commit()
        if c.rowcount > 0:
            return jsonify({"success": True, "message": "Camera deleted"}), 200
        return jsonify({"error": "Camera not found"}), 404
    except Exception as e:
        print(f"Delete camera error: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/api/users/<int:user_id>/cameras', methods=['GET'])
def get_user_cameras(user_id):
    """Get cameras assigned to a specific user (includes stripped config for editing)."""
    try:
        db = get_db()
        c = db.cursor()
        c.execute("""
            SELECT c.id, c.zone_id, c.name, c.type, c.config, c.is_active
            FROM cameras c
            INNER JOIN user_cameras uc ON c.id = uc.camera_id
            WHERE uc.user_id = ?
            ORDER BY c.zone_id
        """, (user_id,))
        cameras = c.fetchall()

        camera_list = [{
            'id': cam[0], 'zone_id': cam[1], 'name': cam[2],
            'type': cam[3], 'config': _safe_config(cam[4]),
            'is_active': bool(cam[5])
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
        
        db = get_db()
        c = db.cursor()
        c.execute("SELECT id FROM users WHERE id=?", (user_id,))
        if not c.fetchone():
            return jsonify({"error": "User not found"}), 404
        
        c.execute("SELECT id FROM cameras WHERE id=?", (camera_id,))
        if not c.fetchone():
            return jsonify({"error": "Camera not found"}), 404
        
        try:
            c.execute("INSERT INTO user_cameras (user_id, camera_id) VALUES (?, ?)",
                         (user_id, camera_id))
            db.commit()
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
        db = get_db()
        c = db.cursor()
        c.execute("DELETE FROM user_cameras WHERE user_id=? AND camera_id=?",
                     (user_id, camera_id))
        db.commit()
        
        if c.rowcount > 0:
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
        db = get_db()
        c = db.cursor()
        c.execute("SELECT id, username, email, created_at FROM users")
        users = c.fetchall()
        
        user_list = []
        for user in users:
            user_id, username, email, created_at = user
            
            c.execute("""
                SELECT c.id, c.zone_id, c.name
                FROM cameras c
                INNER JOIN user_cameras uc ON c.id = uc.camera_id
                WHERE uc.user_id = ?
                ORDER BY c.zone_id
            """, (user_id,))
            cameras = c.fetchall()
            
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


# ---------------------------------------------------------------------------
# Violations / Incident API
# ---------------------------------------------------------------------------

@app.route('/api/violations', methods=['GET'])
def get_violations():
    """Get violation incidents for a user. Requires user_id; only returns violations from cameras assigned to that user."""
    try:
        user_id = request.args.get('user_id', type=int)
        camera_id = request.args.get('camera_id', type=int)
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)

        if user_id is None:
            return jsonify({"error": "user_id required"}), 400

        db = get_db()
        c = db.cursor()

        query = """
            SELECT v.id, v.camera_id, cam.name, v.person_count, v.helmet_count,
                   v.violation_count, v.max_person_confidence, v.snapshot_path, v.created_at
            FROM violations v
            LEFT JOIN cameras cam ON v.camera_id = cam.id
            WHERE v.camera_id IN (SELECT camera_id FROM user_cameras WHERE user_id=?)
        """
        params = [user_id]
        if camera_id is not None:
            query += " AND v.camera_id=?"
            params.append(camera_id)

        query += " ORDER BY v.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        c.execute(query, params)
        rows = c.fetchall()

        violations = [{
            "id": r[0], "camera_id": r[1], "camera_name": r[2] or "Unknown",
            "person_count": r[3], "helmet_count": r[4], "violation_count": r[5],
            "confidence": r[6], "snapshot_url": f"/api/violations/{r[0]}/snapshot" if r[7] else None,
            "created_at": r[8],
        } for r in rows]

        count_params = [user_id]
        if camera_id is not None:
            count_params.append(camera_id)
        count_query = """
            SELECT COUNT(*) FROM violations v
            WHERE v.camera_id IN (SELECT camera_id FROM user_cameras WHERE user_id=?)
        """
        if camera_id is not None:
            count_query += " AND v.camera_id=?"
        c.execute(count_query, count_params)
        total = c.fetchone()[0]

        return jsonify({"violations": violations, "total": total}), 200
    except Exception as e:
        print(f"Get violations error: {e}")
        return jsonify({"error": "Server error"}), 500


@app.route('/api/violations/<int:violation_id>/snapshot', methods=['GET'])
def get_violation_snapshot(violation_id):
    """Serve the snapshot image for a specific violation."""
    try:
        db = get_db()
        c = db.cursor()
        c.execute("SELECT snapshot_path FROM violations WHERE id=?", (violation_id,))
        row = c.fetchone()
        if not row or not row[0]:
            return jsonify({"error": "Snapshot not found"}), 404
        full_path = os.path.join(_PROJECT_ROOT, row[0])
        if not os.path.exists(full_path):
            return jsonify({"error": "Snapshot file missing"}), 404
        return send_file(full_path, mimetype='image/jpeg')
    except Exception as e:
        print(f"Get snapshot error: {e}")
        return jsonify({"error": "Server error"}), 500


def _delete_violations_for_user(user_id, older_than_days=None):
    """Delete violations from cameras assigned to user. If older_than_days, only delete older ones.
    Returns (deleted_count, deleted_paths)."""
    db = get_db()
    c = db.cursor()
    c.execute("SELECT camera_id FROM user_cameras WHERE user_id=?", (user_id,))
    camera_ids = [r[0] for r in c.fetchall()]
    if not camera_ids:
        return 0, []
    placeholders = ','.join('?' * len(camera_ids))
    query = "SELECT id, snapshot_path FROM violations WHERE camera_id IN (%s)" % placeholders
    params = list(camera_ids)
    if older_than_days is not None:
        query += " AND datetime(created_at) < datetime('now', ?)"
        params.append(f'-{int(older_than_days)} days')
    c.execute(query, params)
    rows = c.fetchall()
    deleted_paths = []
    for vid, path in rows:
        if path:
            full = os.path.join(_PROJECT_ROOT, path)
            if os.path.exists(full):
                try:
                    os.remove(full)
                    deleted_paths.append(path)
                except OSError as e:
                    print(f"[Auto-delete] Could not remove {path}: {e}")
    ids = [r[0] for r in rows]
    if ids:
        c.execute("DELETE FROM violations WHERE id IN (" + ','.join('?' * len(ids)) + ")", ids)
        db.commit()
    return len(ids), deleted_paths


@app.route('/api/violations/delete-all', methods=['POST'])
def delete_all_violations():
    """Delete all violations from cameras assigned to the user. Requires user_id in JSON body."""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        if user_id is None:
            user_id = request.args.get('user_id', type=int)
        if user_id is None:
            return jsonify({"error": "user_id required"}), 400
        user_id = int(user_id)
        count, _ = _delete_violations_for_user(user_id, older_than_days=None)
        return jsonify({"success": True, "deleted": count}), 200
    except Exception as e:
        print(f"Delete violations error: {e}")
        return jsonify({"error": "Server error"}), 500


# ---------------------------------------------------------------------------
# User settings (violation auto-delete)
# ---------------------------------------------------------------------------

@app.route('/api/users/<int:user_id>/settings', methods=['GET'])
def get_user_settings(user_id):
    """Get user settings including violation_auto_delete."""
    try:
        db = get_db()
        c = db.cursor()
        c.execute("SELECT violation_auto_delete FROM user_settings WHERE user_id=?", (user_id,))
        row = c.fetchone()
        val = row[0] if row else 'none'
        return jsonify({"violation_auto_delete": val}), 200
    except Exception as e:
        print(f"Get settings error: {e}")
        return jsonify({"error": "Server error"}), 500


@app.route('/api/users/<int:user_id>/settings', methods=['PUT'])
def update_user_settings(user_id):
    """Update user settings. Accepts {violation_auto_delete: 'none'|'day'|'week'|'month'|'year'}."""
    try:
        data = request.get_json() or {}
        val = (data.get('violation_auto_delete') or 'none').strip().lower()
        if val not in ('none', 'day', 'week', 'month', 'year'):
            return jsonify({"error": "violation_auto_delete must be none, day, week, month, or year"}), 400
        db = get_db()
        c = db.cursor()
        c.execute(
            "INSERT INTO user_settings (user_id, violation_auto_delete) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET violation_auto_delete=?",
            (user_id, val, val)
        )
        db.commit()
        return jsonify({"success": True, "violation_auto_delete": val}), 200
    except Exception as e:
        print(f"Update settings error: {e}")
        return jsonify({"error": "Server error"}), 500


def _run_auto_delete_job():
    """Background job: delete old violations based on each user's violation_auto_delete setting."""
    db = get_db()
    c = db.cursor()
    c.execute("SELECT user_id, violation_auto_delete FROM user_settings WHERE violation_auto_delete != 'none'")
    for user_id, setting in c.fetchall():
        days_map = {'day': 1, 'week': 7, 'month': 30, 'year': 365}
        days = days_map.get(setting)
        if days:
            count, _ = _delete_violations_for_user(user_id, older_than_days=days)
            if count > 0:
                print(f"[Auto-delete] User {user_id}: removed {count} violation(s) older than {setting}")


def _auto_delete_worker():
    """Daemon thread that runs auto-delete every hour."""
    while True:
        time.sleep(3600)
        try:
            _run_auto_delete_job()
        except Exception as e:
            print(f"[Auto-delete] Error: {e}")


# Start auto-delete background thread
threading.Thread(target=_auto_delete_worker, daemon=True).start()


@app.route('/')
def index():
    """Root route – frontend runs on port 3000."""
    return jsonify({
        "message": "Workplace Safety Monitor API",
        "docs": "Use /api/health, /api/login, /stream/<camera_id>. Frontend: http://localhost:3000"
    }), 200


if __name__ == '__main__':
    _startup_db = get_db()
    _startup_c = _startup_db.cursor()
    _startup_c.execute("SELECT id, name, type, is_active FROM cameras")
    for row in _startup_c.fetchall():
        status = "active" if row[3] else "inactive"
        print(f"  Camera {row[0]}: {row[1]} ({row[2]}, {status})")
    if DETECTION_ENABLED:
        print(f"Detection model path: {HELMET_MODEL_PATH}")
        print(f"Model file exists: {os.path.exists(HELMET_MODEL_PATH)}")
        d = _get_helmet_detector()
        print(f"Helmet/person detection: {'Enabled' if d and d.model_loaded else 'Disabled'}")
    print("Starting Flask server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True, use_reloader=False)
