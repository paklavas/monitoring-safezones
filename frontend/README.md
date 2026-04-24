# Workplace Safety Monitor – Frontend

React + TypeScript + Vite + Tailwind CSS, with React Router and Recharts. UI for the safety monitoring dashboard.

## Setup

```bash
cd frontend
npm install
npm run dev
```

Dev server: **http://localhost:3000** (also bound to `0.0.0.0` in `vite.config.ts` for access from other devices on the LAN).

## Scripts

| Command           | Description                          |
| ----------------- | ------------------------------------ |
| `npm run dev`     | Start Vite dev server with HMR       |
| `npm run build`   | Typecheck (`tsc -b`) + production build |
| `npm run preview` | Serve the `dist/` build locally      |
| `npm run lint`    | Run ESLint                           |

## Build

```bash
npm run build
```

Output in `dist/`. Serve with any static host or behind the Python backend.

## Backend

The app proxies **`/api`** and **`/stream`** to **http://localhost:5000** (`vite.config.ts`). Without the backend, data calls fail and live video shows placeholders until streams are available.

Endpoints used by this frontend (all paths go through the proxy in dev):

- **Auth:** `POST /api/login`, `POST /api/register`
- **Health:** `GET /api/health`
- **Cameras:** `GET /api/users/:id/cameras`, `POST /api/cameras`, `PUT /api/cameras/:id`, `DELETE /api/cameras/:id`, `POST /api/users/:id/cameras` (link user to camera)
- **Dashboard / stats:** `GET /api/stats` (optional `user_id`)
- **Violations:** `GET /api/violations` (e.g. `user_id`, `camera_id`, `limit`, `offset`), `POST /api/violations/delete-all`
- **User settings:** `GET /api/users/:id/settings`, `PUT /api/users/:id/settings`
- **Analytics:** `GET /api/analytics/heatmap`, `GET /api/analytics/trends` (query params as in `Analytics.tsx`)
- **Video:** `GET /stream/:cameraId` — MJPEG stream

## Routes

| Path              | Page           |
| ----------------- | -------------- |
| `/login`          | Login / register |
| `/`               | Dashboard      |
| `/camera/:cameraId` | Camera detail + stream |
| `/cameras`        | Manage cameras |
| `/incidents`      | Incidents / violations |
| `/analytics`      | Analytics charts |

Unknown paths redirect to `/`.

## Structure

- `src/App.tsx` — routes and auth guard
- `src/pages/` — `Login`, `Dashboard`, `CameraDetail`, `ManageCameras`, `Incidents`, `Analytics`
- `src/components/` — `AppLayout`, `Sidebar`, `PageHeader`, `StatCard`, `CameraCard`, `AlertList`, `AddCameraModal`
- `src/hooks/useAuth.tsx` — auth and camera list in context (`sessionStorage`)
