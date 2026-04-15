# Zima — Claude Code Context

**Read `AGENTS.md` first, then `.claude/CLAUDE-CODE-BRIEFING.md`. The briefing supersedes this file where they conflict.**

---

## Project Identity

Zima is a modular cybersecurity platform. Python 3.12, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, PostgreSQL, Redis, Railway deployment. Rust companion binary for local browser/OS visibility.

---

## Current Development State

**As of 2026-04-15.** Before starting any session, verify against `Brain/Zima.md`.

| Stage | Status |
|---|---|
| 00–09 | ✅ Complete |
| 08 | 🔴 Open — code done; HTTPS/TLS, Sentry, monitoring, Doppler, ICO registration still outstanding |
| 10a | ✅ Complete — schemas + mappers: dehashed, leakcheck, hudson_rock, breachdirectory |
| 10b | ✅ Complete — schemas + mappers: emailrep, emailformat, gravatar, skymem, emailcrawlr |
| 10c | ✅ Complete — IntelX schema/mapper verified |
| 10d | ✅ Complete — mailcat, whatsmyname, holehe, maigret schemas/mappers verified |
| 11 | ✅ Complete — identity module tests added |
| 12 | ✅ Complete — device module tests passing |
| 13 | 🔄 Complete enough for MVP — browser modules implemented, coverage still partial |
| 14 | ✅ Complete — upload streaming, PM exporter verification, newsletter filtering, and alias remediation paths are in code |
| 15 | ✅ Complete — LeakIX + Frankenstein schemas/mappers added |
| 16 | ✅ Complete — wiring and e2e pillar tests |
| 17 | ✅ Complete — Zima Companion (Rust, Phase 1 visibility) |

**Active next work:** Stage 08 deploy-time hardening + frontend polish around PM export/remediation UX

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
- Companion models: `backend/app/db/models/companion.py`
- Companion repository: `backend/app/db/repositories/companion.py`
- Companion API: `backend/app/api/v1/companion.py`

---

## Established Patterns

### Provider Schema/Mapper Pattern (established in Stage 10a/10b)

Every provider that feeds a module must have:

```
backend/app/providers/<category>/<name>/
    client.py     — async HTTP client, returns raw dicts
    schemas.py    — TypedDict definitions for the provider raw payload and finding shape
    mapper.py     — to_provider_finding(finding: ProviderFindingShape) -> ProviderFinding
```

`schemas.py` structure:
```python
from typing import NotRequired, TypedDict
from backend.app.providers.base.models import ProviderFinding

class ProviderNameRaw(TypedDict, total=False):
    field: NotRequired[str]

class ProviderNameFinding(TypedDict, total=False):
    title: str
    description: str | None
    tags: list[str]
    raw: ProviderNameRaw

def to_provider_finding(finding: ProviderNameFinding) -> ProviderFinding:
    # promote the normalised finding dict to ProviderFinding
    ...
```

Enrichment-only providers (emailformat, gravatar) emit no raw payload — their mapper documents the enrichment contract and returns the schema type directly.

### Module Signal Rules Pattern

Every module consumes `ProviderFinding` objects and emits `Signal` objects via `SignalRepository`. Module services live at:
```
backend/app/modules/<domain>/<module_name>/service.py
```

### Module Execution Contract

`BaseModuleService.run()` returns `ModuleOutcome` (not `list[SignalCreate]`):

```python
from backend.app.modules.base.outcome import ModuleOutcome

# Regular signals → signal_repo.upsert()
# Account-discovery signals → account_repo.upsert()
return ModuleOutcome(signals=[...], account_signals=[...])
```

- Modules that only emit regular signals: `return ModuleOutcome(signals=signals)`
- `account_inventory` (holehe/mailcat/whatsmyname) populates `account_signals` directly
- `_to_outcome` shim has been removed — do NOT re-introduce it
- `ScanExecutionContext` is imported under `TYPE_CHECKING` to avoid circular imports

### Active Module Registry

All module wiring lives in `backend/app/active/modules.py` as a flat `ACTIVE_MODULES: list[ModuleSpec]` list. `runner.py` no longer contains direct imports of concrete module classes.

```python
# backend/app/active/specs.py
@dataclass(frozen=True)
class ModuleSpec:
    service_class: type[BaseModuleService]
    domain: str
    tier_minimum: Tier
    status: Literal["active", "deferred"]
    requires_credentials: bool
```

Dependency rule: `active/` may import from `modules/**`; nothing in `modules/**` imports from `active/`. The `active/` package is a leaf.

When adding a new module: add its `ModuleSpec` to `ACTIVE_MODULES` and update `_EXPECTED_MODULE_NAMES` in `tests/unit/jobs/test_runner_specs.py`.

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
|---|---|---|
| Python | 3.12 | |
| Next.js | 16.2.1 | Uses `proxy.ts` for rewrites — NOT `middleware.ts`. Verify file naming before creating Next.js config files. |
| FastAPI | see pyproject.toml | |
| SQLAlchemy | 2.0 async | `Mapped[]` typed columns only |
| Pydantic | v2 | `model_validate()` not `from_orm()` |
| Rust (companion) | see `companion/rust-toolchain.toml` | Cross-platform: macOS arm/x86/universal, Linux, Windows |

---

## Stage Workflow

- Before starting a stage, check if a prior session already completed it: read the stage file and grep for expected output files.
- Do NOT archive a stage as complete without explicit user confirmation.
- After every provider/module change, run the full affected test suite and fix all failures before declaring work complete.
- Show actual pytest output — do not assert "tests pass" without pasting the command and result.

---

## Documentation Maintenance

**Update the Brain Vault as work is completed — do not let it drift.**

When a stage or sub-stage is finished:

1. **`Brain/Zima.md`** — update the status table row (✅ / 🔴 / 🔲 / 🔄) and `updated` date in frontmatter.
2. **`Brain/next-steps-to-launch.md`** — mark completed checklist items `[x]` and update the stage table status column. Update `updated` in frontmatter.
3. **`Brain/MVP Build/stage-10-16-implementation-plan.md`** — update the provider status column for any provider whose client, schemas, or mapper is now done.
4. **The active stage spec file** — update frontmatter `status:` field (`not_started` → `in_progress` → `complete`). Add a dated status note at the top if partially done.
5. **`Brain/Archive/MVP Build 2026/MVP Master.md`** — add the stage to the summary table once confirmed complete.

**Rules:**
- Update docs in the same commit as the code change, not after.
- Use `updated: YYYY-MM-DD` in frontmatter — always set to today's date when editing.
- Stage status fields must use exactly: `complete`, `in_progress`, `open`, `not_started`.
- Do not archive a stage file to `Archive/` until the user confirms it is closed.
- If a provider's status changes mid-stage (e.g. schema added but mapper not yet), record the partial state accurately rather than waiting for full completion.

---

## Working Style

- When the user provides a plan or doc to review, **review it first** before taking any investigative action.
- Do not summarize completed work at the end of a response — the user can read the diff.

---

## When Unsure

Output exactly: `CLARIFICATION NEEDED: [specific question]`
Do not guess. Do not add features not in the spec. Do not "improve" beyond what is specified.
