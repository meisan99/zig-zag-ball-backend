# ZigZagBall Leaderboard API

[![CI](https://github.com/meisan1999/zig-zag-ball-backend/actions/workflows/ci.yml/badge.svg)](https://github.com/meisan1999/zig-zag-ball-backend/actions/workflows/ci.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)

Arcade-style leaderboard backend for **ZigZagBall**, a Unity infinite-runner game. The Unity client lives in a separate repo; this repo is the API only.

There are no accounts and no login. Players submit a name (or 3-letter initials) with a score and read back the top N. Each game mode (`classic`, `energy`, ...) has its own leaderboard that keeps only its top 50 scores.

**Live:** https://zig-zag-ball-backend.onrender.com · [Interactive docs](https://zig-zag-ball-backend.onrender.com/docs)

> [!NOTE]
> The live API runs on free tiers. The first request after a quiet period can be slow while the services wake up (see [Free-tier behavior](#free-tier-behavior)).

[Quick start](#quick-start) · [API](#api) · [Testing](#testing) · [Deployment](#deployment) · [Architecture](#architecture)

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/leaderboard/scores` | Submit a score (`name`, `value`, `game_mode` slug) |
| `GET` | `/leaderboard/top?mode=classic&limit=10` | Top entries for a mode, highest first (`limit` 1–100, default 10) |
| `GET` | `/health` | Liveness check |

Error responses: unknown `game_mode` returns `404`; a name that fails the profanity filter returns `422`.

## Tech stack

| Area | Choice |
|---|---|
| Language / framework | Python 3.12, FastAPI on uvicorn |
| Database | PostgreSQL (local for development, Neon in production) |
| Data access | SQLAlchemy 2.0 (async) + asyncpg, Alembic migrations |
| Validation / config | Pydantic v2, pydantic-settings |
| Name filtering | better-profanity |
| Tests | pytest, pytest-asyncio, httpx |
| Delivery | Docker, GitHub Actions (CI), Render (hosting) |

## Quick start

**Prerequisites:** Python 3.12 and a local PostgreSQL server.

```bash
python -m venv .venv
source .venv/Scripts/activate   # Git Bash
# .venv\Scripts\Activate.ps1    # PowerShell

pip install -r requirements.txt

cp .env.example .env            # then set DATABASE_URL for your local Postgres

alembic upgrade head            # create tables
python -m scripts.init_db       # seed game modes (classic, energy)

uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the interactive docs.

### Environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | Postgres connection string in asyncpg form: `postgresql+asyncpg://<user>:<password>@<host>/<db>`. Add `?ssl=require` for hosted databases. |
| `ENVIRONMENT` | `local` (default) enables SQL echo logging. Use `production` on Render. |

## Testing

Tests run against a real Postgres database, not SQLite, because `Score.id` uses Postgres' native `UUID` type. Each test runs in a transaction that is rolled back afterward, so tests never affect each other.

**One-time setup:** create a `zig_zag_ball_test` database, then apply the migrations to it.

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://<role>:<password>@localhost:5432/zig_zag_ball_test"
alembic upgrade head
Remove-Item Env:DATABASE_URL

cp .env.example .env.test   # then point DATABASE_URL at zig_zag_ball_test
```

**Run the tests:**

```bash
pytest
```

### Try the Docker image locally

Inside a container `localhost` is the container itself, so use `host.docker.internal` to reach Postgres on your machine:

```bash
docker build -t zig-zag-ball-backend .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://<role>:<password>@host.docker.internal:5432/zig_zag_ball" \
  -e ENVIRONMENT=local \
  zig-zag-ball-backend
```

Then check http://localhost:8000/health.

## Architecture

```
app/
  main.py                          # FastAPI app, CORS, routers, /health
  config.py                        # env-based settings
  database.py                      # async engine/session, declarative Base
  models.py                        # GameMode (lookup) + Score
  schemas.py                       # Pydantic request/response models
  result.py                        # Result[T] wrapper for expected failures
  routers/leaderboard.py           # HTTP layer only
  services/leaderboard_service.py  # submit, prune to top 50, rank
alembic/versions/                  # migration scripts
scripts/init_db.py                 # seeds game_modes
tests/                             # service and endpoint tests
Dockerfile, docker-entrypoint.sh   # production image: migrate, then start uvicorn
.github/workflows/ci.yml           # migrations + tests on push/PR
```

Design decisions:

- **Routers vs. services.** Routers handle HTTP only (status codes, request/response shapes). Business logic lives in services.
- **Expected failures are returned, not raised.** Services return a `Result[T]` (like a typed `Result<T>` in C#) and routers map it to an HTTP status.
- **Top-50 cap per mode.** After each insert, rows outside the mode's top 50 are deleted in the same transaction. Ties rank by `value DESC, created_at ASC`, so the first player to reach a score ranks higher.
- **Game modes are data, not code.** Adding a mode means adding a row to `game_modes`, not changing code.

## Deployment

Production is two services linked only by `DATABASE_URL`:

```
Unity game (itch.io) → Render (HTTPS, Docker) → uvicorn → FastAPI → Neon (pooled) → Postgres
```

### On every push to `main`

Two independent pipelines start:

1. **CI (GitHub Actions)** starts a throwaway Postgres container, runs `alembic upgrade head` and `pytest`. It reports pass or fail and deploys nothing.
2. **Render** builds the image from the `Dockerfile` (`.dockerignore` keeps `.env`, `tests/`, `.venv` out) and swaps in the new container once it is healthy.

On start, `docker-entrypoint.sh` runs `alembic upgrade head` (applying only pending migrations, so schema changes deploy with the code), then `exec`s uvicorn on Render's `$PORT` so shutdown signals reach it directly.

### Configuration

- **Render** (Docker web service): set `DATABASE_URL` to the Neon **pooled** URL (host contains `-pooler`) and `ENVIRONMENT=production`. Render sets `PORT`.
- **Neon:** convert the default connection string for asyncpg:
  - scheme `postgresql://` → `postgresql+asyncpg://`
  - query `?sslmode=require&channel_binding=require` → `?ssl=require`
- **CORS:** `app/main.py` allows `https://html-classic.itch.zone` (the itch.io WebGL build). Add origins there if the game is hosted elsewhere.

Secrets live only in Render's dashboard and your local `.env` files, never in the image or repo.

### Seeding a fresh database

Migrations create tables, not rows. Seed once from your machine:

```powershell
$env:DATABASE_URL = "<Neon direct URL, asyncpg form>"
alembic upgrade head
python -m scripts.init_db
Remove-Item Env:DATABASE_URL
```

> [!IMPORTANT]
> When running migrations by hand, use Neon's **direct** URL (no `-pooler`).

### Free-tier behavior

Render stops the service after 15 minutes without traffic and Neon suspends the database after 5 minutes idle. The next request wakes both, so it is noticeably slower. The restart re-runs the migration step, which finds nothing to apply.
