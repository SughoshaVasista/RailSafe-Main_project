# AMRIN FastAPI backend

Phase 1 foundation for the AMRIN REST API. The existing `mock-server/server.py` remains available as a separate, in-memory demo while the API is implemented. The real backend currently exposes only `GET /api/health`; domain records and authentication are added in later phases.

## Windows PowerShell setup

From the repository root:

```powershell
Set-Location .\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If PowerShell blocks virtual-environment activation, use `Set-ExecutionPolicy -Scope Process Bypass` for that terminal and activate again. The development API listens on `http://127.0.0.1:8000`; its health check is `http://127.0.0.1:8000/api/health`.

The default database is a persistent SQLite file under `backend/instance/`. `DATABASE_URL` can point to a PostgreSQL SQLAlchemy URL for a later deployment. `JWT_SECRET_KEY`, `CORS_ORIGINS`, `UPLOAD_FOLDER`, `MAX_CONTENT_LENGTH`, and `ENVIRONMENT` are read from this directory's `.env` or the process environment. Keep backend secrets in `backend/.env`; never put them in a `VITE_` variable.

## Tests

```powershell
Set-Location .\backend
py -m pytest
```

The test suite uses an isolated temporary SQLite database. Run the existing frontend production build from the repository root with `npm run build`.
