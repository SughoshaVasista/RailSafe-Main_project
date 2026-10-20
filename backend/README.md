# AMRIN FastAPI backend

Persistent SQLAlchemy records and an idempotent demo seed now sit on the Phase 1 FastAPI foundation. The existing `mock-server/server.py` remains available as a separate, in-memory demo while API routes and authentication are added in later phases. The production-style backend currently exposes only `GET /api/health`.

## Windows PowerShell setup

From the repository root:

```powershell
Set-Location .\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
alembic upgrade head
python -m app.cli seed-demo
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If PowerShell blocks virtual-environment activation, use `Set-ExecutionPolicy -Scope Process Bypass` for that terminal and activate again. The development API listens on `http://127.0.0.1:8000`; its health check is `http://127.0.0.1:8000/api/health`.

The default database is a persistent SQLite file under `backend/instance/`. `DATABASE_URL` can point to a PostgreSQL SQLAlchemy URL for a later deployment. `JWT_SECRET_KEY`, `CORS_ORIGINS`, `UPLOAD_FOLDER`, `MAX_CONTENT_LENGTH`, and `ENVIRONMENT` are read from this directory's `.env` or the process environment. Keep backend secrets in `backend/.env`; never put them in a `VITE_` variable.

## Tests

```powershell
Set-Location .\backend
py -m pytest
```

`python -m app.cli seed-demo` inserts clearly marked development records with stable IDs. It can be run repeatedly without duplicating them. The seeded worker has no password hash and is not a login account; create real accounts in the authentication phase. No model is loaded or inference simulated by the seed.

The test suite uses an isolated temporary SQLite database. Run the existing frontend production build from the repository root with `npm run build`.
