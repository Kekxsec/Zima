# Zima Agent Guide

Start here for a fresh coding session. `Brain/Zima.md` is the human entry point. This file is the model entry point.

## Repo Map

- `backend/` FastAPI app, SQLAlchemy models/repositories, providers, modules, jobs, tests target.
- `frontend/` Next.js 16 app router frontend.
- `companion/` Rust companion daemon and browser baseline assets.
- `tests/` Python unit, integration, and API tests.
- `Brain/` Obsidian vault for architecture, research, launch planning, and implementation notes.
- `.claude/` model-facing context, including the canonical implementation briefing.

## Canonical Docs

- `Brain/Zima.md` project home and current status.
- `.claude/CLAUDE-CODE-BRIEFING.md` canonical implementation briefing. This is the authoritative code-pattern reference.
- `Brain/Architecture/CLAUDE-CODE-BRIEFING.md` vault mirror note for the canonical briefing path used in wiki links.
- `Brain/Architecture/section-02-design-principles.md` full design rules.
- `Brain/Architecture/Design Principles.md` short design-principles summary for vault navigation.
- `Brain/next-steps-to-launch.md` active launch and implementation queue.
- `Brain/MVP Build/stage-10-16-implementation-plan.md` current provider/module build order.

## Required Services

- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`

Bring them up from repo root:

```bash
docker compose up -d --force-recreate postgres redis
```

## Local Run Commands

Backend:

```bash
uv sync --dev
uv run alembic upgrade head
uv run uvicorn backend.app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Companion:

```bash
cd companion
cargo build
```

## Canonical Test Bootstrap

Use this default workflow unless a task explicitly needs something else.

1. Start Postgres and Redis with `docker compose up -d --force-recreate postgres redis`.
2. Load the test environment from `.env.test`.
3. Ensure the `zima_test` database exists.
4. Run pytest with the test environment active.

Example:

```bash
docker compose up -d --force-recreate postgres redis
createdb zima_test || true
set -a && source .env.test && set +a
uv sync --dev
uv run pytest
```

Important test invariants:

- Tests must run with `APP_ENV=testing`.
- `tests/conftest.py` expects Redis to be reachable unless a test module overrides that fixture.
- `.env.test` is the canonical local test env; do not improvise ad hoc env values when a reproducible run matters.

## Active Work And Invariants

- Stage `14` is complete in code: streamed mbox upload/parsing, vault exporter verification, newsletter filtering, and alias remediation endpoints are all present.
- Active build priority is now Stage `08` deploy-time hardening plus frontend polish around PM export and remediation UX.
- Stage `08` is still the launch gate for infra and operational hardening.
- Providers fetch and normalize data. Modules interpret provider data and emit signals. Do not mix those layers.
- Dependency direction is one-way: core/db/providers/modules/correlation/scoring/remediation/automation/api.
- Verified assets only: scans run against `is_verified=True` assets.
- OTP-only auth. No passwords.
- Companion is visibility-only and communicates with the backend over HTTP only.

## Vault Usage Rules

- Treat `Brain/Zima.md` as the vault home page and keep hub-note links working.
- Keep the canonical implementation briefing in `.claude/CLAUDE-CODE-BRIEFING.md`; do not fork competing copies.
- Use `kind`, `status`, `llm_include`, and `code_scope` frontmatter on research notes.
- Keep `prompt.md`, `output.md`, templates, and external dumps searchable but out of default model context with `llm_include: false`.
- Link meaningful docs into the graph. Do not link artifact leaves just to reduce orphan count.
- Prefer updating existing hubs over creating duplicate navigation notes.
