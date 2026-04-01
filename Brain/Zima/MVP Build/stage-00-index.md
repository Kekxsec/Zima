---
tags: [zima, mvp, build, index, graph_exclude]
type: build_index_support
obsidianUIMode: preview
---

← [[MVP Master|Stage Progress]]

# Zima MVP — Master Implementation Plan (Revised)

This is the definitive index. All previous versions are superseded. Every stage file listed here is required.

---

## Deployment Decision

**Platform: Railway**

Reasons: GitHub-native deployments, managed Postgres and Redis, automatic SSL, built-in environment variable management, £15-25/month at MVP scale, zero infrastructure management.

**AWS migration when ready:** Point the same Docker image at ECS. Update `DATABASE_URL` and `REDIS_URL` to RDS and ElastiCache. Update CI/CD to push to ECR. DNS update. No application code changes required. Full migration checklist is in `stage-00b-railway-deployment.md`.

---

## Complete Stage List

| File | Contents | Status |
|---|---|---|
| `stage-00-environment-and-tooling.md` | Python pinning, uv, pre-commit, import checker, Docker, `.env.example`, CI, CLAUDE.md | Required — complete first |
| `stage-00b-railway-deployment.md` | Railway setup, environment variables, CI/CD wiring, AWS migration path | Required — complete before first deploy |
| `stage-01-scaffold.md` | Full folder structure, core layer, db layer, security headers, HTTPS Nginx config, health endpoints, tier config | Required |
| `stage-01b-audit-threat-validation.md` | AuditEvent model + repository, threat model document, Pydantic input length validation | Required — integrate into Stage 1 |
| `stage-02b-testing-foundation.md` | Full `conftest.py`, test factories, pytest configuration, test file structure convention | Required — complete before any Stage 2 tests |
| `stage-02-otp-auth.md` | OTP auth models, AuthService, JWT utils, EmailService (Resend), auth API endpoints | Required |
| `stage-03-signal-pipeline.md` | Asset model, Signal model, dedup, SignalRepository, FindingRepository (with upsert), Score model (append-only with versioning) | Required |
| `stage-04-provider-and-module.md` | BaseProviderClient, HIBP provider, BaseModuleService, breach_monitor module | Required |
| `stage-05-correlation-scoring-remediation.md` | CorrelationEngine, HighIdentityCompromiseRisk rule, identity score calculator, RemediationEngine | Required |
| `stage-06-jobs-api-orchestration.md` | ModuleRunner, ScanOrchestrator (own session), ScanRepository, scans/findings/scores API endpoints (paginated) | Required |
| `stage-06b-breach-alerts-and-stale-scans.md` | Breach alert email template, send_breach_alert on EmailService, startup stale scan check | Required — integrate into Stage 6 |
| `stage-07-gdpr-and-billing.md` | Account deletion (GDPR), data export, Stripe integration, webhook handler with tier cache invalidation, consent at sign-up | Required |
| `stage-08-pre-launch-hardening.md` | Security audit checklist, dependency scan, environment validation, logging hygiene, error handling, monitoring, final launch sequence | Required — gate before any real users |

---

## What Changed From the Previous Version

### Bugs Fixed (from review)

| Bug | Fix | Where |
|---|---|---|
| Background task uses closed request-scoped DB session | Every background task creates its own `AsyncSessionLocal()` | stage-06 |
| Celery in dependencies but not used | Removed entirely | stage-00 |
| `run_full_scan` did not pass repos | Orchestrator creates repos internally | stage-06 |
| `FindingRepository` not defined | Fully defined with atomic upsert | stage-03 |
| Scores overwritten on each scan | Append-only Score model with scorer_version | stage-03 |
| No Scan history model | Scan model with status, timing, counts | stage-01 |
| CorrelationEngine mutated finding post-construction | user_id passed into evaluate() | stage-05 |
| No pagination on list endpoints | limit/offset on all list endpoints with PaginationParams | stage-06 |
| Module runner assumed email-only inputs | Modules declare required_entity_types | stage-06 |

### Pre-Launch Requirements Integrated

| Requirement | Where |
|---|---|
| Railway deployment + CI/CD wired | stage-00b |
| HTTPS Nginx config | stage-01 |
| Security headers (CSP, HSTS, XFO, etc.) | stage-01 |
| CORS from environment — never hardcoded | stage-01 |
| AuditEvent model and logging | stage-01b |
| Threat model document | stage-01b |
| Input length validation on all Pydantic schemas | stage-01b |
| Full conftest.py with fixtures | stage-02b |
| Test factories for all core models | stage-02b |
| OTP auth — replaces passwords, email verification, password reset | stage-02 |
| OTP rate limiting — brute force protection | stage-02 |
| Transactional email via Resend | stage-02 |
| Stale scan detection and automatic timeout | stage-06b |
| Finding and signal suppression endpoints | stage-06b |
| Breach alert email notification with deduplication | stage-06b |
| Account deletion — GDPR right to erasure | stage-07 |
| Data export — GDPR right of access | stage-07 |
| Consent recorded at sign-up | stage-07 |
| Stripe billing with webhook handling | stage-07 |
| Tier cache invalidation on upgrade | stage-07 |
| Production environment validation at startup | stage-08 |
| Global error handler — no internal error leakage | stage-08 |
| Dependency security scan via pip-audit | stage-08 |
| Monitoring: Sentry, UptimeRobot | stage-08 |

---

## Key Decisions — Do Not Revisit During Build

**Deployment:** Railway for MVP. Docker-based for clean AWS portability later.

**Auth:** OTP-only. No passwords anywhere. Sign-in proves email ownership. No separate verification step needed.

**Background tasks:** `BackgroundTasks` for MVP. Every task creates `async with AsyncSessionLocal() as session`. Never pass a request-scoped session into a background task.

**Scores:** Append-only rows. `scorer_version` field. Historical records are never deleted.

**Deduplication:** Deterministic hash IDs for both signals and findings. Repeated scan runs upsert, never duplicate.

**Module inputs:** Modules declare `required_entity_types`. The runner queries those asset types. Adding a new module requires zero changes to the runner.

**No Celery:** `BackgroundTasks` for MVP. Migrate to Celery when scan volume requires job persistence and retry visibility.

**Suppression:** Users can suppress findings and signals they have acknowledged. Default list view shows open status only.

**Notifications:** Breach alert email sent for new high/critical signals. `notified_at` on Signal prevents repeat notifications across scan runs.

---

## Expansion Path After Stage 8

```
Stage 8 complete + first real user signed up
  ↓
mfa_posture module (accounts domain)
  ↓
LeakCheck provider (Pattern B — second breach source, same module)
  ↓
Second correlation rule: breach + MFA missing → account_takeover_risk
  ↓
Dark web monitoring module
  ↓
Minimal Next.js frontend (score dashboard, findings, remediation tasks)
  ↓
Public launch: Product Hunt, Reddit, SEO
```

Each new module follows Stages 4 and 5 exactly. The pattern is fully established after Stage 5.
