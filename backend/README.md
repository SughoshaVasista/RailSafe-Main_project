# AMRIN FastAPI backend

This backend provides the persistent SQLAlchemy schema, demo seed, server-side authentication/account approval, and the alert/task maintenance workflow. `mock-server/server.py` remains a separate in-memory demo. Device, sensor, map, dashboard, switch-decision, model-status, and AI read APIs follow in later phases.

## Windows PowerShell setup

From the repository root:

```powershell
Set-Location .\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Set a private random `JWT_SECRET_KEY` in `backend/.env` before enabling authentication. Do not share it or put it in a `VITE_` variable. Then initialize the database, create the first administrator, optionally seed demo data, and start the API:

```powershell
alembic upgrade head
python -m app.cli create-admin
python -m app.cli seed-demo
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`create-admin` prompts for a name, email, username, and password. The password is entered with hidden terminal input and is never printed. It refuses to create an account if any administrator already exists. Do not use the seeded worker as a login account; it intentionally has no password hash.

The API listens on `http://127.0.0.1:8000`; health is available at `/api/health`. SQLite is the persistent local default under `backend/instance/`. `DATABASE_URL` can use a PostgreSQL SQLAlchemy URL later. `JWT_ACCESS_TOKEN_MINUTES`, `CORS_ORIGINS`, `UPLOAD_FOLDER`, `MAX_CONTENT_LENGTH`, and `ENVIRONMENT` are configurable through `backend/.env` or process environment.

## Authentication behavior

- `POST /api/auth/login` accepts `{ "username": "email-or-username", "password": "..." }` and returns a signed Bearer token plus the role/name/worker/city fields used by the frontend.
- `POST /api/auth/register` accepts the current signup shape. Every new account is a pending worker. Requests for `operator` or `admin` are recorded as requested roles for audit but never grant privileges.
- `GET /api/auth/me` validates the token and returns safe account fields.
- `GET /api/users/pending`, `POST /api/users/{user_id}/approve`, `POST /api/users/{user_id}/reject`, and `GET /api/workers` require an approved active admin account.
- Approval creates a stable worker ID. Rejected/pending users cannot sign in. API authorization checks the account's current database role and approval state for each request, so disabling or changing an account invalidates its access immediately.
- Public registration passwords require at least 10 characters; CLI administrator passwords require at least 12. Passwords use Argon2 hashes and are never included in API responses.

## Alerts, tasks, and evidence

Alert actions are administrator-only, validated against explicit lifecycle transitions, and written with `AlertHistory` and `EventLog` records. Task lists are limited to the authenticated worker; admins can list/filter all tasks. Task completion requires at least one repair evidence image. The database has a partial unique index preventing multiple open tasks for the same alert.

Evidence accepts JPEG, PNG, GIF, and WebP only. The upload is bounded by `MAX_CONTENT_LENGTH`, its file signature must match its declared MIME type, its stored name is randomized, and it is stored under `UPLOAD_FOLDER`. The private `GET /api/tasks/{task_id}/evidence/{evidence_id}` route checks task ownership/admin role; it never accepts a filesystem path or token in a URL. API clients must send the Bearer token in the `Authorization` header when retrieving an evidence image.

## Tests

```powershell
Set-Location .\backend
python -m pytest
```

The test suite uses isolated temporary SQLite databases. Run the existing frontend production build from the repository root with `npm run build`.
