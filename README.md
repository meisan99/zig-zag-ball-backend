# Arcade Leaderboard Backend

FastAPI + Postgres leaderboard service, old-school arcade style:
no accounts, no login — just submit a name (or 3-letter initials)
with a score, and read back the top N. Supports multiple independent
leaderboards (game modes, e.g. "classic", "energy"), each capped at
its own top-50.

## Structure

```
app/
  main.py              # FastAPI app, router registration
  config.py            # env-based settings
  database.py          # async engine/session, Base
  models.py            # SQLAlchemy: GameMode (lookup) + Score, per-mode leaderboards
  schemas.py           # Pydantic request/response models
  result.py            # Result<T>-style wrapper for expected failures
  routers/leaderboard.py   # "controller" — HTTP layer
  services/leaderboard_service.py  # business logic, talks to the DB
scripts/init_db.py     # for seeding game mode
```

Routers only handle HTTP concerns (status codes, request/response
shape) and delegate to services for logic. Services return `Result[T]`
for expected failure cases instead of raising — same idea as a typed
`Result<T>` in C#. Currently the main expected failure is an unknown
`game_mode` slug (404); the shape stays ready for more validation —
profanity filter, rate limiting, etc. — as it gets added.

## Setup

```bash
python3 -m venv .venv

source .venv/Scripts/activate # Git Bash
# or
.venv\Scripts\Activate.ps1 # Powershell

pip install -r requirements.txt

cp .env.example .env   # then point DATABASE_URL at your Postgres instance

alembic upgrade head          # creates schema
python -m scripts.init_db     # seeds game_modes (classic/energy)

uvicorn app.main:app --reload
```

Docs at http://localhost:8000/docs once running.

## Testing

Tests run against a real Postgres database, not SQLite — `Score.id` uses
Postgres' native `UUID` type. Each test runs in its own transaction
(SQLAlchemy 2.0 `join_transaction_mode="create_savepoint"`) that's rolled
back afterward, so nothing persists between runs.

One-time setup — create a separate test database and apply migrations to it:

```bash
# create the zig_zag_ball_test database (e.g. via pgAdmin), then:

$env:DATABASE_URL = "postgresql+asyncpg://<role>:<password>@localhost:5432/zig_zag_ball_test"  # PowerShell
alembic upgrade head
Remove-Item Env:DATABASE_URL

cp .env.example .env.test   # then point DATABASE_URL at zig_zag_ball_test
```

Then, any time:

```bash
pytest
```

## Endpoints

- `POST /leaderboard/scores` — submit a score (`name`, `value`, `game_mode` slug)
- `GET /leaderboard/top?mode=classic&limit=10` — top N entries for a game mode, ranked, highest first
- `GET /health` — liveness check