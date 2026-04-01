---
tags: [zima, architecture, tech-stack]
created: 2026-03-21
---

# Tech Stack

← [[../Zima|Zima Home]] · [[System Architecture]]

---

## Core Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| API framework | FastAPI (async throughout) |
| ORM | SQLAlchemy 2.0 async + Alembic migrations |
| Validation | Pydantic v2 |
| Database | PostgreSQL (prod) / SQLite (dev / personal tier) |
| Cache / queue | Redis (rate limits, short-lived state) |
| Auth | OTP-only via Resend email — no passwords |
| Payments | Stripe (Checkout + Customer Portal) |
| Email | Resend |
| Deployment | Railway (MVP) → Docker → AWS ECS (when ready) |
| Package manager | uv |
| Linting | ruff + mypy (strict) |
| Testing | pytest + pytest-asyncio + respx |

---

## Key Architectural Decisions

### Auth: OTP-only (no passwords)
Sign-in proves email ownership. No password fields, no bcrypt, no passlib. Eliminates password reset flows and credential breach risk on Zima itself.

### Background tasks: FastAPI BackgroundTasks (no Celery)
Scans take <10 seconds. BackgroundTasks runs in-process — no Redis worker, no extra deployment. Every task creates its own `AsyncSessionLocal()`.
**Upgrade trigger:** when concurrent load exceeds capacity or you need job persistence/retry visibility.

### Scores: append-only rows
Scores are never overwritten. Each recalculation appends a new row with `scorer_version`. Historical scores are always recoverable.

### Signals: deterministic hash IDs
Signals use deterministic hash IDs for deduplication. Repeated scan runs upsert, never create duplicates.

### No frontend yet
MVP is API-only. Minimal Next.js frontend (score dashboard, findings, remediation tasks) comes after Stage 8 and first real user.

### Deployment: Railway → AWS
Railway for MVP: GitHub-native, managed Postgres + Redis, auto SSL, £15-25/month.
AWS migration path: point same Docker image at ECS, update `DATABASE_URL` / `REDIS_URL`. Zero app code changes required.

---

## Provider Categories (~150 active)

| Category | Examples |
|---|---|
| breach | HIBP, LeakCheck, HudsonRock |
| dns | SecurityTrails, WhoisXML, crt.sh |
| threat_intel | OTX, ThreatFox, OpenPhish |
| infrastructure | Shodan, Censys, BinaryEdge |
| cloud | Google Workspace, Microsoft 365, AWS, GitHub |
| reputation | VirusTotal, GreyNoise |
| local | device agent, browser collector, network scanner |

> Note: `tools/` providers are stubs — deferred to a separate dev phase.

---

## Infrastructure Costs

| Service | MVP cost |
|---|---|
| Railway (API + Postgres + Redis) | £15–25/month |
| Resend (email) | Free tier → £20/month at scale |
| Stripe fees | 2.9% + 20p per transaction |
| Total at 50 customers | ~£50–60/month |

**Gross margin at £500 MRR:** ~88%

---

## See Also

- [[System Architecture]] — pipeline and layers
- [[Design Principles]] — non-negotiable rules
- `Zima/docs/Architecture/section-04-backend-architecture.md`
