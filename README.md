# Workplace Safety Monitor

Flask backend (helmet/person detection, SQLite, MJPEG streams) and a React + TypeScript + Vite + Tailwind dashboard. Run **both** for full functionality.

## Quick start

1. **Backend** (from the project root — the folder that contains `backend/`, `frontend/`, and `requirements.txt`):

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python backend\server.py
   ```

   API: **http://localhost:5000** (`0.0.0.0:5000`).

2. **Frontend** (new terminal, project root):

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   UI: **http://localhost:3000** (also on `0.0.0.0` for LAN access). In development, `/api` and `/stream` are proxied to the backend (`frontend/vite.config.ts`).

---

## Backend (`backend/`)

Python 3 with Flask, OpenCV, Ultralytics (YOLO), SQLite. Main entry point: `backend/server.py`.

### Dependencies

Install from the **project root**:

```bash
pip install -r requirements.txt
```

### Database

`accounts.db` is created at the **project root** (same level as `backend/`) on first run.

### Configuration (in code)

Camera zones, RTSP URL, detection flags, and model resolution are set near the top of `backend/server.py` (e.g. `ZONE1_CAMERA_INDEX`, `AXIS_CAMERA_2_URL`, `DETECTION_ENABLED`, `HELMET_MODEL_PATH` resolution). Prefer a trained helmet model under `runs/detect/.../weights/best.pt` or `helmet_detection_yolov11.pt` at project root; otherwise the server falls back to `backend/yolov8n.pt` if present.

### Run

From **project root**:

```bash
python backend\server.py
```

On Linux/macOS:

```bash
python backend/server.py
```

### API overview

- **Auth:** `POST /api/login`, `POST /api/register`
- **Health:** `GET /api/health`
- **Cameras:** `GET /api/users/:id/cameras`, `POST /api/cameras`, `PUT /api/cameras/:id`, `DELETE /api/cameras/:id`, `POST /api/users/:id/cameras`
- **Stats:** `GET /api/stats` (optional `user_id`)
- **Violations:** `GET /api/violations`, `POST /api/violations/delete-all`
- **User settings:** `GET /api/users/:id/settings`, `PUT /api/users/:id/settings`
- **Analytics:** `GET /api/analytics/heatmap`, `GET /api/analytics/trends`
- **Video:** `GET /stream/:cameraId` (MJPEG)

`GET /` returns a short JSON pointer to the API and frontend URL.

---

## Frontend (`frontend/`)

React 18, TypeScript, Vite 5, Tailwind CSS, React Router, Recharts.

### Scripts

| Command           | Description                              |
| ----------------- | ---------------------------------------- |
| `npm run dev`     | Vite dev server with HMR                 |
| `npm run build`   | Typecheck (`tsc -b`) + production build  |
| `npm run preview` | Serve `dist/` locally                    |
| `npm run lint`    | ESLint                                   |

### Build

```bash
cd frontend
npm run build
```

Output: `frontend/dist/`. Can be served statically or behind the Python app.

### App routes

| Path                  | Page                    |
| --------------------- | ----------------------- |
| `/login`              | Login / register        |
| `/`                   | Dashboard               |
| `/camera/:cameraId`   | Camera detail + stream  |
| `/cameras`            | Manage cameras          |
| `/incidents`          | Incidents / violations  |
| `/analytics`          | Analytics charts        |

Unknown paths redirect to `/`.

### Source layout

- `src/App.tsx` — routes and auth guard
- `src/pages/` — main screens
- `src/components/` — layout, sidebar, cards, modals
- `src/hooks/useAuth.tsx` — auth and camera list (`sessionStorage`)

---

## Other folders

- `Safetyhelmet-detection.*` — YOLO / dataset assets (see included dataset READMEs).
