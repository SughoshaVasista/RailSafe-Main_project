# AMRIN

AMRIN is a React/Vite railway condition monitoring and maintenance console. The FastAPI backend provides persistent local development data, authentication, alerts, maintenance workflows, telemetry, and a protected future ML event ingestion contract. It does not control railway signalling or hardware.

## Windows development

Use two PowerShell terminals from the repository root. Keep local `.env` files private; do not overwrite an existing one.

### Terminal 1 — FastAPI backend

```powershell
Set-Location .\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Edit backend\.env and set a private JWT_SECRET_KEY before enabling authentication.
alembic upgrade head
python -m app.cli create-admin
python -m app.cli seed-demo
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`create-admin` prompts for the first administrator; the password is hidden. Demo records use source `demo`. The seeded demo worker has no password. For the optional ML ingestion API, set a separate high-entropy `ML_INGEST_TOKEN` in `backend/.env`; see [the ML contract](docs/ml-integration-contract.md).

### Terminal 2 — React/Vite frontend

```powershell
# Run these commands from the repository root.
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# In root .env, set VITE_API_BASE_URL=http://localhost:8000/api and VITE_DEMO_AUTH=false.
npm install
npm run dev
```

Restart Vite after changing `.env`. Keep `ML_INGEST_TOKEN`, JWT secrets, and all backend-only values out of root `.env` and every `VITE_` variable.

## Local demo mode

`mock-server/server.py` is a separate in-memory UI demo server. Run it instead of FastAPI when intentionally using the mock-data workflow and demo auth. Its seed resets on restart; it is not persistent or suitable for railway operations. `/simulation/simulator` is a standalone decision-support simulation and does not require a live ML service or railway connection. `/simulator` and `/simulation` redirect to that standalone page.

## Tests and build

```powershell
Set-Location .\backend
python -m pytest
Set-Location ..
npm test
npm run build
```

SQLite is the local persistent default in `backend/instance/`; set backend `DATABASE_URL` to a PostgreSQL SQLAlchemy URL to prepare a PostgreSQL deployment. Run Alembic migrations before starting the API. Never commit `.env`, databases, uploaded evidence, virtual environments, or generated build outputs.

## Main routes

The public site is available at `/`, `/about`, `/how-it-works`, `/technology`, and `/contact`. These pages use a separate public layout and do not require authentication. The existing operational app includes Command Center, Alerts, Live Map, Tasks, Hardware, AI Detection, and the administrator-only Manage Users page at `/users`; access is role-gated by the API and UI. The simulator remains at `/simulation/simulator` (with `/simulator` and `/simulation` redirecting to it).

The public site describes the verified project stack and current integration boundaries. Team phone and email contacts are listed on the Contact page; institution details and a message submission endpoint are not configured. Physical device feeds and model inference still require configuration or a separate service. See [backend setup and API behavior](backend/README.md) and the [implementation handoff](docs/implementation-handoff.md).
