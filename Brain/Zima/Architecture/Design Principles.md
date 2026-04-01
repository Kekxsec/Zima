---
tags: [zima, architecture, rules]
created: 2026-03-21
---

# Design Principles

← [[../Zima|Zima Home]] · [[System Architecture]]

These rules are non-negotiable. The CI enforces most of them automatically.

---

## Rule 1 — Dependency Direction

```
core → db → auth → assets → signals → providers → modules
     → correlation → scoring → remediation → automation → api
```

Lower layers **never** import higher layers. Import checker runs in CI — violations fail the build.

---

## Rule 2 — Provider / Module Separation

| Layer | Does | Never does |
|---|---|---|
| **Provider** | Fetch, auth, parse, rate-limit | Assign severity, emit user-facing outputs |
| **Module** | Interpret data, emit signals | Make HTTP requests, call other modules |

> **Providers answer:** *How do I get the data?*
> **Modules answer:** *What does the data mean?*

This boundary is non-negotiable.

---

## Rule 3 — Background Tasks

Every background task creates its own `async with AsyncSessionLocal() as session`.

**Never** pass a request-scoped `AsyncSession` into a background task.

---

## Rule 4 — Repository Pattern

All database access through repository classes in `backend/app/db/repositories/`.

No raw queries. No `session.execute()` outside repositories (except migration scripts).

---

## Rule 5 — Verified Assets Only

Scans run **only** against assets where `is_verified=True`.

`is_verified` is set **only** by `AssetService.register_verified_email()`.

Never set `is_verified=True` elsewhere.

---

## Rule 6 — No Passwords

OTP-only authentication. No passwords, no `passlib`, no `bcrypt`, no password fields anywhere.

---

## Rule 7 — No Celery

Use `FastAPI BackgroundTasks`. Do not add Celery.
Migrate when scan volume requires job persistence and retry visibility (typically 20–50 concurrent users).

---

## Rule 8 — Model Locations

| Model | Location | Import |
|---|---|---|
| `Scan` | `backend/app/jobs/models.py` | `from backend.app.jobs.models import Scan` |
| `AuditEvent` | `backend/app/db/models/audit.py` | `from backend.app.db.models.audit import AuditEvent` |

---

## Rule 9 — User Has No Email Column

`User` table has no email column. Email lives in the `Asset` table.

To look up a user by email: query `Asset` where `entity_type='email'` and `value=email`, then get `user_id`.

---

## Code Standards

- Python 3.12 type hints on **every** parameter and return value
- Strict mypy — no `Any`, no `# type: ignore` without justification
- Pydantic v2 `model_validate()` not `from_orm()`
- SQLAlchemy 2.0 `Mapped[]` typed columns — no `Column()` style
- `async/await` throughout — no synchronous database calls
- `SecretStr` for all secret values in `Settings`
- All `datetime` objects timezone-aware: `datetime.now(timezone.utc)`
- Every Python file starts with a path comment: `# backend/app/some/module.py`

---

## When Unsure

Output exactly: `CLARIFICATION NEEDED: [specific question]`

Do not guess. Do not add features not in the spec. Do not "improve" beyond what is specified.

---

## See Also

- [[System Architecture]] — layers and pipeline
- `Zima/.claude/CLAUDE.md` — authoritative source
