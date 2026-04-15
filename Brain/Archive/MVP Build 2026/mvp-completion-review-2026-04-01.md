---
tags: [zima, mvp, review, status]
created: 2026-04-01
---

← [[MVP Master|Stage Progress]]

# MVP Completion Review — 2026-04-01

## Decision

The codebase appears to have implemented the core product work for Stages 00 through 07, and parts of Stage 08.

The MVP Build should **not** be fully archived yet.

Reason: Stage 08 defines the exit gate for MVP completion, and that gate is not fully closed. Some items are already implemented in code, but the full launch-hardening checklist is not complete and several operational checks cannot be confirmed from source alone.

## What Is Clearly Implemented

### Stages 00–05

These stages appear materially implemented in the repository:

- environment/tooling, CI, Railway config, and import checks
- scaffold, DB layer, health endpoints, core config
- OTP auth, hashed OTP storage, JWT auth, rate limiting
- signal/finding/score pipeline
- provider/module pattern, correlation, scoring, remediation

Representative evidence:

- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/auth/service.py`
- `backend/app/signals/models.py`
- `backend/app/correlation/engine.py`
- `backend/app/scoring/calculators/identity_score.py`
- `backend/app/remediation/engine.py`
- `.github/workflows/ci.yml`
- `railway.toml`

### Stage 06 — Jobs, API, Orchestration

This stage is implemented despite `MVP Master.md` still saying "Not started".

Representative evidence:

- `backend/app/jobs/models.py`
- `backend/app/db/repositories/scans.py`
- `backend/app/jobs/runner.py`
- `backend/app/jobs/orchestrator.py`
- `backend/app/api/v1/scans.py`
- `backend/app/api/v1/findings.py`
- `backend/app/api/v1/signals.py`
- `backend/app/api/v1/scores.py`
- `tests/api/test_scan_endpoints.py`
- `tests/api/test_findings_endpoints.py`
- `tests/integration/test_scan_pipeline.py`

### Stage 06b — Breach Alerts and Stale Scans

This stage is also implemented in code.

Representative evidence:

- `backend/app/email/templates/breach_alert.py`
- `backend/app/email/service.py`
- `backend/app/jobs/orchestrator.py`
- `backend/app/main.py`
- `tests/unit/test_stale_scans.py`
- `tests/unit/test_email_templates.py`

### Stage 07 — GDPR and Billing

This stage appears materially implemented.

Representative evidence:

- `backend/app/api/v1/account.py`
- `backend/app/api/v1/billing.py`
- `backend/app/api/v1/legal.py`
- `backend/app/billing/service.py`
- `backend/app/billing/webhooks.py`
- `backend/app/auth/models.py`
- `backend/app/auth/service.py`
- `tests/api/test_account_endpoints.py`

## Why The MVP Is Not Fully Complete Yet

Stage 08 says:

> Every item in this stage is complete and verified. This is the gate between "technically working" and "ready to accept real users."

That condition is not yet satisfied.

## Stage 08 Status

### Already Implemented In Code

- startup environment verification:
  - `backend/app/core/startup.py`
- stale scan cleanup at startup:
  - `backend/app/main.py`
- global exception handler:
  - `backend/app/main.py`
- security headers middleware:
  - `backend/app/main.py`
- `pip-audit` in CI:
  - `.github/workflows/ci.yml`
- `detect-private-key` pre-commit hook:
  - `.pre-commit-config.yaml`
- privacy consent field on user:
  - `backend/app/auth/models.py`
- consent recorded on first sign-in path:
  - `backend/app/auth/service.py`
- Stripe webhook secret verification:
  - `backend/app/billing/webhooks.py`
- scan endpoint rate limit:
  - `backend/app/api/v1/scans.py`

### Not Fully Confirmed / Still Open

- deployed HTTPS/TLS enforcement and certificate monitoring
- production-domain CORS verification
- public privacy and terms pages on the frontend
- complete verification that all request bodies are schema-bound and normalized
- confirmation that provider responses are always mapped before persistence
- global API-wide rate limiting beyond endpoint-level rules
- data retention enforcement
- monitoring/alerting integration such as Sentry and uptime checks
- full day-of-launch sequence verification

One concrete example: the backend exposes `/legal/privacy` and `/legal/terms`, but the frontend does not currently appear to contain privacy or terms pages under `frontend/src/app/`.

## Archival Decision

Do not archive the whole `MVP Build` folder yet.

Recommended approach:

1. Keep the MVP docs active until Stage 08 is closed.
2. Update or supersede `MVP Master.md`, because it is stale and under-reports progress.
3. Treat the new Stage 09 plan as parallel forward planning, not proof that the MVP gate is closed.

## Practical Conclusion

- Stages 00–07: substantially implemented
- Stage 08: partially implemented, not fully verified
- Full MVP archive: **No, not yet**

Once Stage 08 is fully verified, the `MVP Build` files can be archived as historical implementation records.
