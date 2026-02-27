# Workplace Safety Monitor – Frontend

React + TypeScript + Vite + Tailwind. Modern, minimal UI for the safety monitoring dashboard.

## Setup

```bash
cd frontend
npm install
npm run dev
```

Runs at **http://localhost:3000**.

## Build

```bash
npm run build
```

Output in `dist/`. Serve with any static host or the Python backend.

## Backend

The app expects a backend at **http://localhost:5000** (see `vite.config.ts` proxy):

- `POST /api/login` – login
- `POST /api/register` – create account
- `GET /stream/1`, `GET /stream/2` – MJPEG camera streams

Without the backend, video placeholders will show "No feed" until those endpoints exist.

## Structure

- `src/pages/` – Login, Dashboard, CameraDetail
- `src/components/` – Header, StatCard, CameraCard, AlertList
- `src/hooks/useAuth.tsx` – auth state (sessionStorage for now)
