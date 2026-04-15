---
title: Codex Execution Plan — Road to Launch
tags: [zima, mvp, launch, execution, codex]
created: 2026-04-15
updated: 2026-04-15
status: active
related:
  - "[[../next-steps-to-launch]]"
  - "[[stage-10-16-implementation-plan]]"
  - "[[stage-08-pre-launch-hardening]]"
---

← [[../Zima|Zima]] · [[../next-steps-to-launch|Launch Checklist]]

# Codex Execution Plan — Road to Launch

Phased execution plan covering all remaining work before Zima accepts real users. Generated 2026-04-15. Single source of truth for phase sequencing and task breakdown.

**Total estimate:** ~23 working days on critical path.

---

## Current State (2026-04-15)

| Stage | Status |
|---|---|
| 00–09, 17 | ✅ Complete |
| 10a/10b | ✅ Complete — breach + social schemas/mappers |
| 10c/10d | ✅ Complete — schemas/mappers verified by unit tests |
| 11 | ✅ Complete — all identity module unit tests added |
| 12 | ✅ Complete — all device module unit tests passing (40) |
| 13 | ✅ Complete — browser modules implemented, partial test coverage |
| 15 | ✅ Complete — LeakIX + Frankenstein schemas/mappers added and tested |
| 16 | ✅ Complete — wiring + e2e pillar tests (10 passing) |
| 08 | 🔴 Code done — HTTPS/TLS, Sentry, monitoring, Doppler, ICO outstanding (deploy-time) |
| 14 | ✅ Complete — streamed upload path, PM exporter verification, newsletter filtering, and alias remediation endpoints are in code |
| Frontend | 🔄 Partial — onboarding scan/results, account, browser/device, and checkout pages build; PM export/remediation polish remains |

---

## Non-Negotiable Constraints

Read `/Users/max/Zima/.claude/CLAUDE.md` before any code change. Summary:

1. **Dependency direction:** `core → db → auth → assets → signals → providers → modules → correlation → scoring → remediation → automation → api` — enforced by CI import checker
2. **Provider/Module separation:** Providers fetch+parse only. Modules interpret+emit signals only. No severity in providers. No HTTP in modules.
3. **No Celery** — FastAPI BackgroundTasks only
4. **OTP-only auth** — no passwords, no passlib
5. **Repository pattern** — all DB access via `backend/app/db/repositories/`
6. **Verified assets only** — `is_verified=True` set only in `AssetService.register_verified_email()`
7. **User model** — User table has NO email column; email lives in Asset table

---

## Phase 1 — Provider Schema/Mapper Verification (Days 1–2)

*Code-only. No blockers. Start immediately.*

### 1a — Verify Stage 10c/10d (IntelX, mailcat, whatsmyname, holehe, maigret)

Check that schemas/mappers from the last session landed correctly and tests pass.

| Task | File | Done |
|---|---|---|
| Verify `intelx` schemas.py + mapper.py exist and match the mapper contract | `backend/app/providers/threat_intel/intelx/` | [x] |
| Verify `mailcat` schemas.py + mapper.py | `backend/app/providers/tools/mailcat/` | [x] |
| Verify `whatsmyname` schemas.py + mapper.py | `backend/app/providers/tools/whatsmyname/` | [x] |
| Verify `holehe` schemas.py + mapper.py | `backend/app/providers/tools/holehe/` | [x] |
| Verify `maigret` schemas.py + mapper.py | `backend/app/providers/tools/maigret/` | [x] |
| Run mapper contract tests for all five providers | `pytest tests/unit/providers/test_mapper_contracts.py -q` | [x] |
| Update docs: 10c/10d → ✅ Complete | `Brain/Zima.md` + `stage-10-16-implementation-plan.md` | [x] |

### 1b — Stage 15: LeakIX + Frankenstein Schemas/Mappers

Clients and `infrastructure_exposure` module are implemented. Only schemas/mappers missing.

| Task | File | Done |
|---|---|---|
| Create `LeakIXRaw` + `LeakIXFinding` TypedDicts | `backend/app/providers/threat_intel/leakix/schemas.py` | [x] |
| Create `to_provider_finding()` mapper for LeakIX | `backend/app/providers/threat_intel/leakix/mapper.py` | [x] |
| Create `FrankensteinRaw` + `FrankensteinFinding` TypedDicts | `backend/app/providers/tools/frankenstein/schemas.py` | [x] |
| Create `to_provider_finding()` mapper for Frankenstein | `backend/app/providers/tools/frankenstein/mapper.py` | [x] |
| Write unit tests for both new mappers | `tests/unit/providers/test_mapper_contracts.py` | [x] |
| Update docs: Stage 15 schemas/mappers → ✅ Complete | `Brain/Zima.md` + `stage-10-16-implementation-plan.md` | [x] |

**Schema pattern** (from CLAUDE.md):
```python
# backend/app/providers/<category>/<name>/schemas.py
from typing import NotRequired, TypedDict
from backend.app.providers.base.models import ProviderFinding

class ProviderNameRaw:
    field: NotRequired[str]

class ProviderNameFinding(TypedDict, total=False):
    title: str
    description: str | None
    tags: list[str]
    raw: ProviderNameRaw

def to_provider_finding(finding: ProviderNameFinding) -> ProviderFinding:
    ...
```

**Phase 1 gate:** All provider unit tests green before moving to Phase 2.

---

## Phase 2 — Email Account Identifier Pipeline (Days 3–8)

*Code-only. Phase 2c depends on Phase 2a. Phase 2d is DEFERRED.*

### 2a — mbox Parser Improvements (Days 3–4)

| Task | File | Done |
|---|---|---|
| Audit existing mbox_parser for memory issues | `backend/app/providers/tools/mbox_parser/client.py` | [x] |
| Replace in-memory parse with generator/streaming | same | [x] |
| Add header extraction: From, To, Subject, Date (ISO 8601), Message-ID, References | same | [x] |
| Lowercase-normalise all email addresses on extract | same | [x] |
| Implement deduplication: by Message-ID; fallback hash of (From, To, Subject, Date ±1 min) | same | [x] |
| Extract MIME type + message size per message | same | [x] |
| Write unit tests: streaming large fixture (1K messages), dedup, edge cases | `tests/unit/email_accounts/test_mbox_parser.py` | [x] |
| Harden upload path by streaming to temp storage before background processing | `backend/app/api/v1/email_accounts.py` + `backend/app/jobs/mbox_processor.py` | [x] |
| Add file-based parser path so processing does not require full upload bytes in memory | `backend/app/providers/tools/mbox_parser/client.py` | [x] |

**Status:** Phase 2a is complete in code. Further memory benchmarking is still useful, but the structural in-memory upload bottleneck has been removed.

### 2b — Password Manager Exporter Verification (Days 5–6)

| Task | File | Done |
|---|---|---|
| Verify Bitwarden JSON exporter with fixture | `backend/app/providers/tools/bitwarden_json_exporter/client.py` | [x] |
| Verify Proton Pass JSON exporter with fixture | `backend/app/providers/tools/proton_pass_json_exporter/client.py` | [x] |
| Verify 1Password .1pux exporter happy path + missing export rejection | `backend/app/providers/tools/onepassword_1pux_exporter/client.py` | [x] |
| Add error handling: invalid/corrupted exports on all three | all three clients | [x] |
| Write unit tests with fixture exports for all three | `tests/unit/providers/test_vault_export_providers.py` | [x] |

**Status:** Phase 2b is complete for the launch scope.

### 2c — Newsletter Detection Pipeline (Days 7–8)

*Depends on Phase 2a (needs header extraction).*

| Task | File | Done |
|---|---|---|
| Build newsletter classifier rule engine: header-based (`List-Unsubscribe`, `Precedence: bulk`), sender patterns (`noreply@`, `newsletter@`), subject patterns | `backend/app/email_accounts/newsletter.py` | [x] |
| Add confidence scoring (0–100): header indicators +30, sender match +20, subject match +15, unsubscribe link +25; threshold >= 70 → newsletter | same | [x] |
| Integrate classifier before account extraction so newsletters are filtered out of discovery | `backend/app/jobs/mbox_processor.py` | [x] |
| Write unit tests with fixture emails; conservative threshold retained | `tests/unit/email_accounts/test_newsletter_detector.py` | [x] |

**Status:** Phase 2c is complete in code with a conservative threshold; production tuning remains a rollout concern, not an implementation blocker.

### 2d — Email Alias Management

| Task | File | Done |
|---|---|---|
| Connect/update SimpleLogin and Addy.io integrations | `backend/app/api/v1/integrations.py` | [x] |
| Create aliases for discovered accounts via remediation endpoint | `backend/app/api/v1/email_accounts.py` | [x] |
| Verify endpoint access control and ownership boundaries | `tests/api/test_email_accounts_endpoints.py` | [x] |

**Phase 2 gate:** Met. Newsletter detection, PM exporters, and alias remediation paths are all implemented and verified for the launch scope.

---

## Phase 3 — Frontend Audit Product UI (Days 9–16)

*Code-only. Can run in parallel with Phase 2 for 3a/3b/3d.*

The frontend is a **one-time paid audit product**, not a subscription dashboard. Users flow: onboarding → scan in progress → results report → account inventory → remediation.

### 3a — Audit Progress Screen (Day 9)

| Task | File | Done |
|---|---|---|
| Create real-time scan progress tracker component | `frontend/src/components/audit/ScanProgressTracker.tsx` | [ ] |
| Wire polling hook (every 2s) to refetch scan status | `frontend/src/app/(onboarding)/onboarding/scan/page.tsx` | [x] |
| Per-pillar status indicators: Pending → Running → Completed with finding count | `frontend/src/components/audit/PillarStatus.tsx` | [ ] |

### 3b — Results Report & Findings (Days 10–11)

| Task | File | Done |
|---|---|---|
| Results report page: overall risk score, per-pillar breakdown, top 5 critical findings, CTA | `frontend/src/app/(onboarding)/onboarding/results/page.tsx` | [x] |
| Findings detail page: filterable/sortable table, click → detail panel with evidence + remediation | `frontend/src/app/(dashboard)/findings/page.tsx` | [ ] |
| Severity + pillar + status filter component | `frontend/src/components/audit/FindingsFilter.tsx` | [ ] |
| Remediation card: problem statement, numbered steps, effort estimate, external links | `frontend/src/components/audit/RemediationCard.tsx` | [ ] |

### 3c — Account Inventory & PM Export (Days 12–13)

*Depends on Phase 2b (PM exporters).*

| Task | File | Done |
|---|---|---|
| Account inventory page: service, email, confidence %, source badge, bulk select | `frontend/src/app/(dashboard)/accounts/page.tsx` | [x] |
| PM export modal: choose format (Bitwarden/Proton Pass/1Password), download, import instructions | `frontend/src/components/audit/PasswordManagerExportModal.tsx` | [ ] |
| Account source badges (breach DB / mbox parse / enumeration tool) | `frontend/src/components/audit/AccountSourceBadge.tsx` | [ ] |

### 3d — Device & Browser Deep Dives (Days 14–15)

| Task | File | Done |
|---|---|---|
| Device baseline page: OS, patching status, firewall, encryption, software inventory, vulnerable packages table | `frontend/src/app/(dashboard)/device/page.tsx` | [x] |
| Browser extensions page: extension table with risk score, configuration findings | `frontend/src/app/(dashboard)/browser/page.tsx` | [x] |
| Extension detail modal: metadata, permissions breakdown, risk explanation, uninstall instructions | `frontend/src/components/audit/ExtensionDetailModal.tsx` | [ ] |

### 3e — Billing & Checkout (Day 16)

*Depends on Stripe account + test keys being configured (infrastructure decision).*

| Task | File | Done |
|---|---|---|
| Stripe checkout page: product listing, one-time price, Stripe payment form | `frontend/src/app/(onboarding)/onboarding/checkout/page.tsx` | [x] |
| Payment success + failure pages | `frontend/src/app/(onboarding)/onboarding/checkout/success/page.tsx` + `failure/page.tsx` | [x] |
| In-app checkout modal (for mid-session upgrade) | `frontend/src/components/billing/CheckoutModal.tsx` | [x] |

**Risk:** Never touch raw card data — use Stripe's hosted form exclusively.

### 3f — Legal Pages (Day 16)

| Task | File | Done |
|---|---|---|
| Verify `/privacy` page is public and covers: data collected, processing, retention, deletion, third parties | `frontend/src/app/(legal)/privacy/page.tsx` | [x] |
| Verify `/terms` page is public and covers: one-time purchase, liability limitation, acceptable use | `frontend/src/app/(legal)/terms/page.tsx` | [x] |
| Add privacy policy acceptance checkbox on first sign-in; set `privacy_policy_accepted_at` in backend | `frontend/src/app/(auth)/sign-in/page.tsx` + backend | [ ] |

**Phase 3 gate:** All pages functional in staging. Stripe test payment completes end-to-end. Legal pages publicly accessible.

---

## Phase 4 — Backend Pre-Launch Hardening (Days 17–19)

*Code-only.*

### 4a — Input Validation (Day 17)

| Task | File | Done |
|---|---|---|
| Audit all API endpoints for bare `dict` params — convert to Pydantic v2 schemas | `backend/app/api/v1/*.py` | [ ] |
| Normalise all email inputs to lowercase on ingress across all endpoints | multiple | [ ] |
| Enforce pagination: `limit` <= 100, `offset` >= 0 on all paginated routes | multiple | [ ] |
| Enforce scan rate limit: 5 per hour per user (Redis) | `backend/app/api/v1/scans.py` | [ ] |
| Add global API rate limiter: 100 req/min per IP, 1000 req/min per user, return 429 | `backend/app/core/middleware.py` | [ ] |

### 4b — Security Headers & CORS (Day 18)

| Task | File | Done |
|---|---|---|
| Strip `Server` header from all responses | `backend/app/core/middleware.py` | [ ] |
| Set `CORS_ALLOWED_ORIGINS` to production domain only (no `*`) | `backend/app/core/config.py` | [ ] |
| Add headers middleware: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Content-Security-Policy`, `Referrer-Policy: no-referrer` | `backend/app/core/middleware.py` | [ ] |

### 4c — Secrets Audit (Day 18)

| Task | Notes | Done |
|---|---|---|
| Verify all secrets use Pydantic `SecretStr` | `backend/app/core/config.py` | [ ] |
| Run `git log --all --full-history -- "*.env"` — must return nothing | If files found: `git filter-branch` to remove from history | [ ] |
| Confirm `detect-private-key` pre-commit hook is active | `.pre-commit-config.yaml` | [ ] |

### 4d — GDPR: Deletion & Export (Day 19)

| Task | Notes | Done |
|---|---|---|
| Test account deletion end-to-end: create user → delete → verify no PII remains | Manual | [ ] |
| Test data export end-to-end: create user → request export → verify all fields present, no other user data leaked | Manual | [ ] |
| Confirm `privacy_policy_accepted_at` is set on first sign-in | Backend audit | [ ] |
| Confirm data retention policy is documented and enforcement is in place | `Brain/next-steps-to-launch.md` | [ ] |
| Confirm audit logging covers all deletions with user_id + timestamp | `backend/app/db/models/audit.py` | [ ] |

### 4e — Dependency Security (Day 19)

| Task | File | Done |
|---|---|---|
| Add `pip-audit` to dev dependencies and CI — fail on known vulnerabilities | `.github/workflows/ci.yml` | [ ] |
| Run `pip-audit` locally — fix all issues | manual | [ ] |

**Phase 4 gate:** `pip-audit` clean. GDPR tests pass. CORS blocks cross-origin. No secrets in git history.

---

## Phase 5 — Deploy-Time Infrastructure (Days 20–23)

*Not code — requires live Railway deployment and third-party accounts.*

### 5a — HTTPS/TLS

- [ ] HTTP → HTTPS 301 redirect enforced at Nginx
- [ ] TLS 1.2 minimum, TLS 1.3 preferred; 1.0 and 1.1 disabled
- [ ] HSTS header: `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- [ ] SSL certificate auto-renewing; expiry alert at 30 days

### 5b — Secrets Management (Doppler)

- [ ] Create Doppler project; migrate all prod secrets from Railway env vars
- [ ] Verify no hardcoded secrets remain in Railway UI
- [ ] Test app boots from Doppler secrets only

### 5c — Monitoring & Alerting

- [ ] Sentry DSN configured — capturing unhandled exceptions with user context; error spike alert
- [ ] UptimeRobot pinging `/health/ready` every 5 minutes; alert on down
- [ ] Log aggregation configured (Papertrail or Logtail)

### 5d — CORS & Security Headers Verification

- [ ] Test CORS from browser: cross-origin request must not return `Access-Control-Allow-Origin`
- [ ] Run https://securityheaders.com — target A or A+

### 5e — ICO Registration ⏰ Start Early

- [ ] Register with ICO at https://ico.org.uk/for-organisations/data-protection-register/ (£40/year)
- **Note:** Takes 2–4 weeks. Start this in Phase 1 week.

### 5f — Database Hardening

- [ ] Database not publicly accessible — firewall: application server only
- [ ] Database user restricted to `SELECT/INSERT/UPDATE/DELETE` — no DDL
- [ ] Automated daily backups with 30-day retention

### 5g — Stripe Production

- [ ] Pricing decided and set in Stripe (one-time charge)
- [ ] Stripe test-mode end-to-end verified before switching to live keys
- [ ] Swap to live Stripe keys
- [ ] Verify webhook endpoint with live keys

### 5h — Commercial Readiness

- [ ] Resend domain verified and sending from production domain
- [ ] Support channel available (email or simple intake form)
- [ ] Waitlist or early-access mechanism if soft-launching

### 5i — Pre-Launch Sequence

Run in order:
1. Full test suite — all green
2. `pip-audit` — zero vulnerabilities
3. Import direction checker — no violations
4. Deploy to production
5. Verify `/health/ready` returns 200
6. Verify HTTPS redirect (`curl http://yourdomain.com` → 301)
7. Run securityheaders.com — A or A+
8. Request OTP for test email — verify Resend delivery
9. Complete a full scan end-to-end — verify findings produced
10. Verify Stripe checkout and webhook (`stripe trigger payment_intent.succeeded`)
11. Verify account deletion removes all personal data
12. Verify data export returns expected fields
13. Confirm privacy policy and terms are publicly accessible

---

## Execution Order & Parallelisation

```
Day 1–2:   Phase 1 (providers)
           + Start ICO registration (Phase 5e) ← do this today, 4-week wait

Day 3–8:   Phase 2 (email account pipeline)
           Phase 3a/3b/3d can run in parallel (frontend, independent of Phase 2)

Day 9–16:  Phase 3 (frontend UI)
           Phase 4 can begin once Phase 3 is underway (mostly independent)

Day 17–19: Phase 4 (backend hardening)

Day 20–23: Phase 5 (deployment + infrastructure)
```

**Parallelisable pairs:**
- Phase 1 + Phase 3a/3b/3d (independent)
- Phase 2a + Phase 3a/3b/3d (independent)
- Phase 4 + Phase 3 (mostly independent)

---

## Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| 10c/10d schemas/mappers broken or missing | High | Phase 1a verification is mandatory first step |
| mbox parser OOM on large files | High | Benchmark early; cap accepted file size at upload |
| 1Password .1pux decryption complexity | High | Spike first; defer to post-launch if blocked |
| Newsletter detector high false-positive rate | Medium | Conservative threshold; do NOT ship Phase 2d until stable in prod |
| Stripe checkout misconfigured | High | Full test-mode run before live keys; never touch raw card data |
| Secrets in git history | Critical | `git log --all --full-history -- "*.env"` mandatory in Phase 4c |
| GDPR deletion incomplete | Critical | Full manual test before launch |
| Database publicly accessible | Critical | Firewall lockdown in Phase 5f mandatory |

---

## Deferred (Post-Launch)

- Phase 2d: Email alias management (SimpleLogin/Addy.io) — blocked on Phase 2c production stability
- Companion Phase 2: Remediation actions
- Subscription tiers and ongoing breach alerts
- Phone providers (truecaller, numverify, callername)
- Dark-web index providers (ahmia, darksearch)
- Domain, IP, cloud, content analysis providers
- Local LLM classification layer for email pipeline
