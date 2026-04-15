# Backend Agent Guide

Read [../.claude/AGENTS.md](/Users/max/Zima/.claude/AGENTS.md) first, then `.claude/CLAUDE-CODE-BRIEFING.md` for implementation patterns.

## Scope

- `backend/app/` application code
- `tests/` Python tests
- Alembic, repositories, providers, modules, jobs, API

## Run

```bash
uv sync --dev
uv run alembic upgrade head
uv run uvicorn backend.app.main:app --reload
```

## Test

```bash
docker compose up -d --force-recreate postgres redis
createdb zima_test || true
set -a && source .env.test && set +a
uv run pytest
```

## Backend Invariants

- `APP_ENV=testing` is required for pytest.
- Repository access belongs in `backend/app/db/repositories/`.
- Providers do not assign severity.
- Modules do not make raw HTTP requests.
- Background jobs create their own DB session.
- Redis availability matters for rate-limit and quota behavior; do not silently assume it is absent in integration tests.
