---
title: Next Steps to Launch
aliases: [Next Steps, MVP Next Steps]
tags: [zima, launch, planning, product]
created: 2026-04-06
updated: 2026-04-15
verified: 2026-04-15
related:
  - "[[Zima]]"
  - "[[MVP Build/stage-08-pre-launch-hardening]]"
  - "[[MVP Build/stage-10-16-implementation-plan]]"
---

# Next Steps to Launch

Single view of everything that must be done before Zima accepts real users — product, infrastructure, and compliance, in order.

The launch product is a **one-time paid personal security audit**: identity exposure, account discovery, browser audit, device baseline, and a scored action plan.

---

## 1. Finish Stage 8 — Pre-Launch Hardening

Stage 8 is the launch gate. All code items are done. The remaining items are infrastructure and operational — they require a live deployment to verify.

**Infrastructure (deploy-time)**
- [ ] HTTPS enforced at Nginx — HTTP 301 redirect to HTTPS
- [ ] TLS 1.2 minimum, TLS 1.3 preferred — 1.0 and 1.1 disabled
- [ ] HSTS header: `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- [ ] SSL certificate auto-renewing with expiry monitoring (alert at 30 days)
- [ ] Database not publicly accessible — only reachable from the application server
- [ ] Database user restricted to `SELECT/INSERT/UPDATE/DELETE` — no DDL

**Environment and Secrets**
- [ ] All secrets loaded via Pydantic `SecretStr` — verified no plain-string secrets
- [ ] Production secrets in Doppler — not `.env` files on server
- [ ] Run `git log --all --full-history -- "*.env"` — must return nothing
- [ ] `detect-private-key` pre-commit hook active and tested

**CORS and Headers (verify post-deploy)**
- [ ] `CORS_ALLOWED_ORIGINS` set to production domain only in Railway
- [ ] Run https://securityheaders.com — target A or A+
- [ ] No `Server` header leaking framework or version

**Input Validation**
- [ ] All request bodies validated by Pydantic v2 schemas — audit any bare `dict` params
- [ ] Email inputs normalised to lowercase before use across all endpoints
- [ ] Pagination `limit` capped at 100, `offset` >= 0 on all paginated routes
- [ ] `/scans/` POST — 5 per hour per user rate limit confirmed active
- [ ] Global API rate limiter configured (beyond per-endpoint rules)

**CI Security**
- [ ] `pip-audit` added to dev dependencies and running in CI — zero known vulnerabilities required

**Monitoring and Alerting**
- [ ] Sentry configured — capturing unhandled exceptions with user context
- [ ] UptimeRobot pinging `/health/ready` every 5 minutes
- [ ] Log aggregation configured (Papertrail or Logtail)
- [ ] Alerts set: service down, unhandled exception spike, Stripe webhook failures

**GDPR and Legal**
- [ ] Account deletion endpoint tested end-to-end
- [ ] Data export endpoint tested end-to-end
- [x] Privacy policy page exists in frontend at `/privacy`
- [x] Terms of service page exists in frontend at `/terms`
- [ ] `privacy_policy_accepted_at` confirmed set on first sign-in
- [ ] Data retention policy documented and programmatic enforcement in place
- [ ] ICO registration completed (required if processing personal data commercially — £40/year)

See [[MVP Build/stage-08-pre-launch-hardening]] for the full checklist including final pre-launch sequence.

---

## 2. Provider Layer — Stages 10–13

The scan engine needs all launch providers implemented before a real audit can run end-to-end.

### Stage 10 — Identity Provider Clients

| Sub-stage | Work | Status |
|---|---|---|
| 10a | Breach clients schemas/mappers: hibp, dehashed, leakcheck, hudson_rock, breachdirectory | ✅ Complete (2026-04-09) |
| 10b | Social/reputation schemas/mappers: emailrep, emailformat, gravatar, emailcrawlr, skymem | ✅ Complete (2026-04-09) |
| 10c | IntelX schemas/mapper (client already complete) | ✅ Complete (2026-04-15) |
| 10d | Subprocess tool schemas/mappers: mailcat, whatsmyname, holehe, maigret (all clients complete) | ✅ Complete (2026-04-15) |

### Stage 11 — Identity Module Signal Rules *(all services implemented — tests gap)*

| Module | Providers | Status |
|---|---|---|
| `breach_monitor` | hibp, dehashed, breachdirectory, leakcheck | ✅ Complete |
| `credential_exposure` | dehashed, leakcheck | ✅ Complete |
| `stealer_log_exposure` | hudson_rock | ✅ Complete |
| `account_enumeration_risk` | emailrep, holehe | ✅ Complete — unit tests added (2026-04-15) |
| `account_inventory` | holehe, mailcat, whatsmyname | ✅ Complete — unit tests added (2026-04-15) |
| `username_exposure` | emailcrawlr, gravatar | ✅ Complete |
| `alias_correlation` | whatsmyname | ✅ Complete |
| `darkweb_identity_monitor` | intelx | ✅ Complete — unit tests added (2026-04-15) |
| `public_profile_scan` | gravatar, emailcrawlr | ✅ Complete — unit tests added (2026-04-15) |

### Stage 12 — Device Pillar *(all services implemented — tests gap)*

| Item | Status |
|---|---|
| Provider clients: osquery, macos_native, windows_native, linux_native, lynis, trivy, grype | ✅ All complete |
| Modules: os_security, patch_status, software_vulnerability, firewall_status, device_inventory, software_inventory | ✅ All complete — 40 unit tests passing (2026-04-15) |

### Stage 13 — Browser Pillar *(all services implemented)*

| Item | Status |
|---|---|
| Provider clients: browser_extension_detector, get_browser_extension_info, malicious_extension_sentry, chromium_enterprise_policies, firefox_enterprise_policies, crxcavator, chrome_web_store_api, firefox_addons_site_api | ✅ All complete |
| Modules: extension_risk, browser_configuration | ✅ Both complete |

---

## 3. Email Account Identifier Pipeline — Stage 14

The centrepiece of the account discovery pillar. Runs after identity providers and feeds the password manager migration.

| Sub-stage | Work | Status |
|---|---|---|
| 14a | mbox parser improvements — richer metadata, deduplication, performance pass | ✅ Complete — upload now streams to temp storage and parser reads from disk or bytes with fallback dedup |
| 14b | Password manager exporters — Bitwarden JSON + Proton Pass JSON + 1Password `.1pux` | ✅ Complete — Bitwarden, Proton Pass, and 1Password verified by unit tests |
| 14c | Upload API endpoint — `POST /imports/vault` | ✅ Complete |
| 14d | Newsletter and subscription detection pipeline — pre-pass noise reduction | ✅ Complete — scored classifier filters newsletters before account discovery and persists review drafts |
| 14e | Email alias management integration — SimpleLogin + Addy.io as remediation actions | ✅ Complete — integration management + alias-creation endpoints are live |

**Note:** Stage 14 is complete in code. Remaining work here is real-world tuning and rollout validation, not missing implementation.

---

## 4. Infrastructure Providers — Stage 15

| Item | Status |
|---|---|
| LeakIX client | ✅ Complete |
| Frankenstein client | ✅ Complete |
| `infrastructure_exposure` module | ✅ Complete (287 lines) |
| Schemas/mappers for leakix + frankenstein | ✅ Complete (2026-04-15) |

---

## 5. Integration and Wiring — Stage 16 ✅ Complete (2026-04-15)

- [x] Remove epieos from registry (ToS violation) — removed from `scan_inventory.py` `_PROVIDER_TO_SOURCE_TYPE`
- [x] Remove/clarify twilio scope — audited: twilio not used in any active module (phone_exposure uses CallerNameProvider + NumverifyProvider); no code change needed
- [x] Orchestrator `ProviderFinding` type usage — audited: correct usage in `infrastructure_exposure`; no issues found
- [x] `evaluate_provider_policy()` enforced at orchestrator level — `_policy_allows_module()` gate added to `runner.py::run_for_user()`
- [x] End-to-end scan tests for each pillar — `tests/integration/test_e2e_pillars.py` — 10 tests passing (identity ×3, device ×2, browser ×5)

---

## 6. Frontend — Match the Audit Product

The frontend needs to reflect the one-time audit product, not a subscription dashboard.

- [ ] **Onboarding flow** — enter email, upload mbox, grant local scan permissions
- [x] **Audit progress screen** — onboarding scan page builds and shows live status UX
- [x] **Results report** — onboarding results page builds
- [x] **Account inventory view** — dashboard account inventory page builds
- [ ] **Password manager export** — downloadable Bitwarden / Proton Pass / 1Password file
- [ ] **Remediation guidance** — per-finding step-by-step fix instructions
- [x] **Browser audit view** — browser page builds
- [x] **Device baseline view** — device page builds
- [x] **Legal pages** — `/privacy` and `/terms` publicly accessible
- [x] **Billing / checkout** — checkout pages and in-app modal build against the current billing API

---

## 7. Companion (Stage 17) — ✅ Complete

The Zima Companion Rust binary (Phase 1 — visibility only) is implemented:

- DB models: `CompanionSession` + `BrowserSnapshot` in `backend/app/db/models/companion.py`
- API: `POST /companion/setup-token`, `POST /companion/register`, `POST /companion/snapshot`, `GET /companion/status`
- Rust binary: `companion/` with cross-platform build (macOS arm/x86/universal, Linux, Windows)
- Browser baselines: `companion/baselines/{chrome,brave,firefox}-v1.json` (5 rules each)
- CI: `companion-ci.yml` + `companion-release.yml` with optional macOS codesign

**Remaining:** Phase 2 remediation actions (post-launch).

---

## 8. Commercial Readiness

- [ ] Pricing decided and set in Stripe — single one-time charge for the audit
- [ ] Stripe test-mode end-to-end flow verified before switching to live keys
- [ ] Resend domain verified and sending from production domain
- [ ] Support channel available to users (email or simple intake form)
- [ ] Waitlist or early-access mechanism if soft-launching to a limited cohort

---

## Launch Sequence (Day Of)

Once all the above is done:

1. Run full test suite — all green
2. Run `pip-audit` — zero vulnerabilities
3. Run import direction checker — no violations
4. Deploy to production
5. Verify `/health/ready` returns 200
6. Verify HTTPS redirect (curl `http://yourdomain.com` → 301)
7. Run https://securityheaders.com — A or A+
8. Request OTP for test email — verify Resend delivery
9. Complete a full scan end-to-end — verify findings produced
10. Verify Stripe checkout and webhook (`stripe trigger customer.subscription.updated`)
11. Verify account deletion removes all personal data
12. Verify data export returns expected fields
13. Confirm privacy policy and terms are publicly accessible

---

## What Is Explicitly Deferred

Do not start these before launch:

- Ongoing monitoring / breach alert subscriptions (Stage 06b features)
- Subscription tier gating (Core / Plus / Pro / Business)
- Domain, IP, cloud, crypto, content analysis providers
- Network and Wi-Fi inspection
- Custom domain aliasing
- socid_extractor, sociallinks, huginn_muninn
- Companion Phase 2 remediation actions
- **Phone providers** — truecaller, numverify, callername (target module: `phone_exposure`)
- **Dark-web index providers** — ahmia, darksearch (target module: `darkweb_identity_monitor`; note: IntelX is in-scope for Stage 10c)

### Local LLM Classification Layer

A private self-hosted model (Llama 3.x 8B or similar via Ollama) as a confidence and disambiguation layer inside the email account identifier pipeline.

**Intended role (narrow):**
- Is this sender a true account service or newsletter/marketing?
- Do these domains belong to the same product/vendor?
- Is this message stream transactional or promotional?
- Is this service safe to treat as a password-manager candidate?

Acts as a rescoring layer on top of: rules → headers → service knowledge base → model → human review. Not the sole authority.

**Why deferred:**
- Cannot tune or evaluate the model before real-world misclassification data exists
- The rule-based pipeline must ship first and accumulate edge cases
- Infrastructure overhead (Ollama on Railway CPU: 3–10s inference — unnecessary pre-launch)

**Prerequisites before building:**
1. Rule-based pipeline is live and producing account inventory
2. At least one batch of real inbox data has been processed
3. Misclassification examples are catalogued
4. Confidence score gaps are identified from production output

**Architecture:** implement as a pipeline component in the module layer, not a provider. The rule pipeline should emit confidence scores and an `ambiguous` flag to give the model clean, scoped inputs.

**Never:** fully autonomous destructive actions, unsubscribing without review, changing login identities without supervision, irreversible account actions from low-confidence evidence.

---

## See Also

- [[MVP Build/stage-08-pre-launch-hardening]] — full Stage 8 checklist
- [[MVP Build/stage-10-16-implementation-plan]] — detailed provider and module spec
