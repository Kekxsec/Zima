---
tags: [zima, mvp, build, status]
created: 2026-03-21
updated: 2026-04-06
status: complete
---

← [[../../Zima|Zima]]

# MVP Stage Progress

> **Stages 00–07 and 09 implemented.** Stage 08 (pre-launch hardening) remains open — it is the launch gate. Stage files for completed stages archived here. Active development continues from Stage 10. See `Brain/next-steps-to-launch.md` for the full picture.

**Deployment:** Railway · **Auth:** OTP-only · **Background tasks:** FastAPI BackgroundTasks

---

## Stage Summary

| Stage | Name | Status |
|---|---|---|
| 00 | Environment & Tooling | ✅ Complete |
| 00b | Railway Deployment | ✅ Complete |
| 01 | Scaffold | ✅ Complete |
| 01b | Audit & Threat Validation | ✅ Complete |
| 02b | Testing Foundation | ✅ Complete |
| 02 | OTP Auth | ✅ Complete |
| 03 | Signal Pipeline | ✅ Complete |
| 04 | Provider & Module | ✅ Complete |
| 05 | Correlation, Scoring, Remediation | ✅ Complete — 17/17 tests pass |
| 06 | Jobs, API, Orchestration | ✅ Implemented in code |
| 06b | Breach Alerts & Stale Scans | ✅ Implemented in code |
| 07 | GDPR & Billing | ✅ Implemented in code |
| 08 | Pre-Launch Hardening | 🔴 Open — launch gate, see `MVP Build/stage-08-pre-launch-hardening.md` |
| 09 | Execution Policy & Security Hardening | ✅ Complete |

---

## Stage Details

### Stage 00–00b: Environment & Railway
- Python pinning, uv, pre-commit, import checker, Docker, CI
- Railway setup, env vars, CI/CD wiring, AWS migration path

### Stage 01–01b: Scaffold & Security Foundation
- Full folder structure, core layer, db layer
- Security headers, HTTPS Nginx config, health endpoints, tier config
- `AuditEvent` model, threat model document
- Pydantic input length validation on all schemas

### Stage 02–02b: Auth & Testing Foundation
- Full `conftest.py`, test factories, pytest configuration
- OTP auth models, `AuthService`, JWT utils
- `EmailService` (Resend), auth API endpoints
- OTP rate limiting (brute force protection)

### Stage 03: Signal Pipeline
- `Asset` model, `Signal` model with dedup
- `SignalRepository`, `FindingRepository` (atomic upsert)
- `Score` model (append-only with `scorer_version`)

### Stage 04: First Provider + Module
- `BaseProviderClient`, HIBP provider
- `BaseModuleService`, `breach_monitor` module
- Pattern is now fully established for all future modules

### Stage 05: Correlation, Scoring, Remediation ✅
- `CorrelationEngine` + `HighIdentityCompromiseRisk` rule
- Identity score calculator
- `RemediationEngine`
- 17/17 tests passing

---

## Stages 6–8: Current State

The original stage status below is no longer accurate. Stages 6 and 7 are materially implemented in the codebase. Stage 8 has also begun and includes several completed hardening items, but it is not yet fully closed.

See:

- [[mvp-completion-review-2026-04-01]]
- [[stage-09-execution-policy-and-security-hardening]]
- [[mvp-archive-plan]]

### Stage 06: Jobs, API, Orchestration
- `ModuleRunner`, `ScanOrchestrator` (own session)
- `ScanRepository`
- Scans / findings / scores API endpoints (paginated)
- Status: implemented in code

### Stage 06b: Breach Alerts & Stale Scans
- Breach alert email template
- `send_breach_alert` on `EmailService`
- Startup stale scan check + automatic timeout
- Finding and signal suppression endpoints
- Status: implemented in code

### Stage 07: GDPR & Billing
- Account deletion (GDPR right to erasure)
- Data export (GDPR right of access)
- Consent recorded at sign-up
- Stripe integration + webhook handler with tier cache invalidation
- Status: implemented in code

### Stage 08: Pre-Launch Hardening
- Security audit checklist
- Dependency scan (`pip-audit`)
- Environment validation at startup
- Logging hygiene + global error handler (no internal leakage)
- Monitoring: Sentry + UptimeRobot
- **Gate:** must pass before any real users
- Status: partially implemented, not yet complete enough to archive the MVP build

---

## Key Decisions (Do Not Revisit)

| Decision | Choice |
|---|---|
| Deployment | Railway for MVP |
| Auth | OTP-only — no passwords |
| Background tasks | `BackgroundTasks` — every task creates its own session |
| Scores | Append-only, `scorer_version` field |
| Deduplication | Deterministic hash IDs for signals and findings |
| Module inputs | Modules declare `required_entity_types` — runner queries asset types |
| No Celery | `BackgroundTasks` until concurrent load demands more |
| Suppression | Users can suppress findings/signals; default view shows `open` only |
| Notifications | Breach alerts for new high/critical signals; `notified_at` prevents repeats |

---

## See Also

- [[stage-00-index]] — master implementation spec index
- [[MVP - Road to Launch]] — what comes after Stage 8
- [[mvp-completion-review-2026-04-01]] — current code-vs-plan review
- [[mvp-archive-plan]] — archive criteria and archive procedure after Stage 8 closes
- [[stage-09-execution-policy-and-security-hardening]] — next implementation stage
- [[pre-stage-06-signal-registry-handoff]] — required bridge between provider research and Stage 6
- [[../../next-steps-to-launch|Next Steps]] — current focus and open questions
- [[../../Architecture/CLAUDE-CODE-BRIEFING|Implementation Reference]] — canonical code patterns
