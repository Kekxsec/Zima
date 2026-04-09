# Zima — Claude Code Context

**Always read CLAUDE-CODE-BRIEFING.md first. That document supersedes this one where they conflict.**

---

## Project Identity

Zima is a modular cybersecurity platform. Python 3.12, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, PostgreSQL, Redis, Railway deployment.

---

## Non-Negotiable Rules

### Rule 1 — Dependency Direction
```
core → db → auth → assets → signals → providers → modules
     → correlation → scoring → remediation → automation → api
```
Lower layers NEVER import higher layers. The CI import checker enforces this. Violations fail the build.

### Rule 2 — Provider / Module Separation
- Providers: fetch data, parse responses, return typed models. Nothing else.
- Modules: interpret provider data, emit signals. Nothing else.
- NEVER assign severity in a provider.
- NEVER make HTTP requests in a module.

### Rule 3 — Background Tasks
Every background task creates its own `AsyncSessionLocal()` session.
NEVER pass a request-scoped `AsyncSession` into a background task.

### Rule 4 — Repository Pattern
All database access via repository classes in `backend/app/db/repositories/`.
No raw queries, no `session.execute()` outside repositories except in migration scripts.

### Rule 5 — Verified Assets Only
Scans run ONLY against assets where `is_verified=True`.
`is_verified` is set ONLY by `assets/service.py::AssetService.register_verified_email()`.
NEVER set `is_verified=True` elsewhere.

### Rule 6 — No Passwords
OTP-only authentication. No passwords, no `passlib`, no `bcrypt`, no password fields on any model.

### Rule 7 — No Celery
Use `FastAPI BackgroundTasks`. Do not add Celery.

### Rule 8 — Scan Model Location
`Scan` model is in `backend/app/jobs/models.py`.
Import: `from backend.app.jobs.models import Scan`
NEVER import `Scan` from `auth/models.py`.

### Rule 9 — AuditEvent Model Location
`AuditEvent` model is in `backend/app/db/models/audit.py`.
Import: `from backend.app.db.models.audit import AuditEvent, AuditEventType`

### Rule 10 — User Model Has No Email Column
`User` table has no email column. Email lives in the `Asset` table.
To look up a user by email: query `Asset` where `entity_type='email'` and `value=email`, then get `user_id`.

### Rule 11 — Companion Architecture Boundary
The companion binary MUST NOT write to the database directly. All companion → backend communication is HTTP only via `POST /api/v1/companion/register` and `POST /api/v1/companion/snapshot`.
- Companion JWTs have `type: "companion"` — never accept them in `get_current_user()`.
- `get_companion_user()` in `backend/app/api/dependencies.py` is Bearer-only (no cookie).
- Phase 1 is visibility only: the companion reads state and reports it. It does NOT modify browser settings or OS configuration.
- Companion models live in `backend/app/db/models/companion.py`.
- Companion repository lives in `backend/app/db/repositories/companion.py`.
- Companion API lives in `backend/app/api/v1/companion.py`.

---

## Code Standards

- Python 3.12 type hints on every function parameter and return value
- Strict Mypy — no `Any`, no `# type: ignore` without justification
- Pydantic v2 `model_validate()` not `from_orm()`
- SQLAlchemy 2.0 `Mapped[]` typed columns — no `Column()` style
- `async/await` throughout — no synchronous database calls
- `SecretStr` for all secret values in `Settings`
- All `datetime` objects timezone-aware — use `datetime.now(timezone.utc)`

---

## File Header Convention

Every Python file starts with a comment showing its path from repo root:

```python
# backend/app/some/module.py
```

This is mandatory for every file generated.

---

## Stack Versions

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.12 | |
| Next.js | 16.2.1 | Uses `proxy.ts` for rewrites — NOT `middleware.ts`. Verify file naming before creating any Next.js config files. |
| FastAPI | see pyproject.toml | |
| SQLAlchemy | 2.0 async | `Mapped[]` typed columns only |
| Pydantic | v2 | `model_validate()` not `from_orm()` |

---

## MVP Stage Workflow

- Before implementing a stage, **check if prior sessions already completed it**. Read the stage file and grep for the output files before writing anything.
- Do NOT archive a stage as complete without explicit user confirmation.
- After every module/provider change, run the full affected test suite and fix all failures before declaring work complete.
- Show actual pytest output — do not assert "tests pass" without pasting the command and result.

---

## Working Style

- When the user provides a plan or doc to review, **review it first** before taking any investigative action.
- Do not summarize completed work at the end of a response — the user can read the diff.

---

## When Unsure

Output exactly: `CLARIFICATION NEEDED: [specific question]`
Do not guess. Do not add features not in the spec. Do not "improve" beyond what is specified.
