# RailSafe

React/Vite operations console for railway condition monitoring, inspection, maintenance, and decision support.

## Setup

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

Run the development API separately with `python mock-server/server.py`. It listens on `http://localhost:8000`; demo credentials are `admin/admin` and `worker/worker`. The mock server includes a temporary in-memory demo database with seeded alerts, tracks, train telemetry, sensor readings, diagnostics, model status, and switch decisions. It resets when the server restarts and must not be used for railway operations.

## Environment

`.env.example` documents every client-side `VITE_` variable: `VITE_API_BASE_URL`, `VITE_MAP_LAT`, `VITE_MAP_LNG`, `VITE_MAPTILER_KEY`, and the seven `VITE_FIREBASE_*` settings. To use the real backend, set `VITE_API_BASE_URL` in `.env` to its `/api` URL and restart Vite. Axios attaches the persisted auth token; the backend must re-check role authorization on every endpoint.

## Firebase rules

`database.rules.json` permits public reads for the development listener and denies client writes. Production writes must go through the authenticated backend, which should deploy stricter rules and validate roles server-side.

## Routes

Admin routes include Command Center, Alerts, Live Map, Tasks, Workers, Hardware, AI Detection, Track Switching, Repair History, Sensor History, Simulation, Model, and Settings. Workers can access Tasks and the Map only.

## Demo walkthrough

With the mock server and Vite running, execute:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/demo-walkthrough.ps1
```

The script walks through hardware online, an S3 crack alert, switch recommendation, worker assignment, repair status transitions, evidence upload, and alert resolution.
# RailSafe-Main_project
