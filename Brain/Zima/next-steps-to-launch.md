---
title: "Next Steps to Launch"
tags: [zima, launch, planning, product]
created: 2026-04-06
updated: 2026-04-06
---

# Next Steps to Launch

This document is the single view of everything that must be done before Zima accepts real users. It covers product, infrastructure, and compliance — in the order they should be tackled.

The launch product is a **one-time paid personal security audit**: identity exposure, account discovery, browser audit, device baseline, and a scored action plan. Not a subscription. Not ongoing monitoring.

---

## 1. Finish Stage 8 — Pre-Launch Hardening

Stage 8 is the launch gate. Nothing below this is optional.

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
- [ ] Privacy policy published at accessible public URL
- [ ] Terms of service published
- [ ] `privacy_policy_accepted_at` confirmed set on first sign-in
- [ ] Data retention policy documented and programmatic enforcement in place
- [ ] ICO registration completed (required if processing personal data commercially — £40/year)

See `MVP Build/stage-08-pre-launch-hardening.md` for the full checklist including final pre-launch sequence.

---

## 2. Provider Layer — Stages 10–13

The scan engine needs all launch providers implemented before any real audit can run end-to-end.

### Stage 10 — Identity Provider Clients

| Sub-stage | Work |
|---|---|
| 10a | Breach clients: hibp, dehashed, leakcheck, hudson_rock, breachdirectory — `schemas.py` + `mapper.py` |
| 10b | Social/reputation clients: emailrep, emailformat, gravatar, emailcrawlr |
| 10c | IntelX client (dark web) |
| 10d | Subprocess tool clients: mailcat, whatsmyname |

### Stage 11 — Identity Module Signal Rules

| Module | Providers |
|---|---|
| `breach_monitor` | hibp, dehashed, breachdirectory |
| `credential_exposure` | dehashed, leakcheck |
| `stealer_log_exposure` | hudson_rock |
| `account_enumeration_risk` | emailrep, holehe |
| `account_inventory` | holehe, mailcat, whatsmyname |
| `username_exposure` | maigret |
| `alias_correlation` | emailformat, whatsmyname |
| `phone_exposure` | numverify, callername |
| `darkweb_identity_monitor` | intelx |
| `public_profile_scan` | gravatar, emailcrawlr |

### Stage 12 — Device Pillar

| Sub-stage | Work |
|---|---|
| 12a | Provider clients: osquery, posture, macos_native, windows_native, linux_native |
| 12b | Provider clients: lynis, trivy, grype, syft, oui_master_database |
| 12c | Modules: os_security, patch_status, software_vulnerability, firewall_status |
| 12d | Module: device_inventory (offline OUI enrichment) |
| 12e | Module: software_inventory (syft) |

### Stage 13 — Browser Pillar

| Sub-stage | Work |
|---|---|
| 13a | Provider clients: browser_extension_detector, get_browser_extension_info, malicious_extension_sentry |
| 13b | Provider clients: chromium_enterprise_policies, firefox_enterprise_policies, crxcavator, chrome_web_store_api, firefox_addons_site_api |
| 13c | Modules: extension_risk, browser_configuration |

---

## 3. Email Account Identifier Pipeline — Stage 14

The centrepiece of the account discovery pillar. Runs after identity providers and feeds the password manager migration.

| Sub-stage | Work |
|---|---|
| 14a | mbox parser improvements — richer metadata, deduplication, performance pass |
| 14b | Password manager exporters Wave 1 — Bitwarden JSON + Proton Pass JSON |
| 14c | Upload API endpoint — `POST /api/v1/assets/import` |
| 14d | Newsletter and subscription detection pipeline — pre-pass noise reduction before account classification |
| 14e | Email alias management integration — SimpleLogin + Addy.io as remediation-layer action providers |
| 14f | Password manager exporters Wave 3 — 1Password `.1pux` |

**Note:** 14d (newsletter detection) must be stable before 14e (alias management). Build in order.

---

## 4. Infrastructure Providers — Stage 15

- **15a** — LeakIX client + `infrastructure_exposure` module
- **15b** — Frankenstein client + `browser_configuration` module

---

## 5. Integration and Wiring — Stage 16

- Remove epieos from registry (ToS violation)
- Remove twilio from provider layer (auth only — not a scan provider)
- Orchestrator updated to use `ProviderFinding` types throughout
- `evaluate_provider_policy()` enforced at orchestrator level for all providers
- End-to-end scan tests for each pillar (identity, device, browser)
- Chrome Web Store and Firefox Addons wave-3 providers wired

---

## 6. Frontend — Match the Audit Product

The frontend needs to reflect the one-time audit product, not a subscription dashboard. Key screens to complete or build:

- [ ] **Onboarding flow** — enter email, upload mbox, grant local scan permissions
- [ ] **Audit progress screen** — live scan status across all pillars (identity, device, browser)
- [ ] **Results report** — scored findings per pillar, severity breakdown, prioritised action list
- [ ] **Account inventory view** — discovered accounts with confidence, linked to PM export
- [ ] **Password manager export** — downloadable Bitwarden / Proton Pass / 1Password file
- [ ] **Remediation guidance** — per-finding step-by-step fix instructions
- [ ] **Browser audit view** — extension risk table, configuration findings
- [ ] **Device baseline view** — OS posture, patching status, encryption, firewall
- [ ] **Legal pages** — `/privacy` and `/terms` publicly accessible (required for Stage 8)
- [ ] **Billing / checkout** — Stripe payment for one-time audit, confirmation flow

---

## 7. Commercial Readiness

- [ ] Pricing decided and set in Stripe — single one-time charge for the audit
- [ ] Stripe test-mode end-to-end flow verified before switching to live keys
- [ ] Resend domain verified and sending from production domain
- [ ] Support channel available to users (email, or a simple intake form)
- [ ] Waitlist or early-access mechanism if soft-launching to a limited cohort

---

## Launch Sequence (Day Of)

Once all the above is done, complete these in order:

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

These are out of launch scope. Do not start them before launch:

- Ongoing monitoring / breach alert subscriptions (Stage 06b features)
- Subscription tier gating (Core / Plus / Pro / Business)
- Local LLM classification layer (needs production misclassification data first)
- Domain, IP, cloud, crypto, content analysis providers
- Network and Wi-Fi inspection
- Custom domain aliasing
- socid_extractor, sociallinks, huginn_muninn

---

## See Also

- `MVP Build/stage-08-pre-launch-hardening.md` — full Stage 8 checklist
- `MVP Build/stage-10-16-implementation-plan.md` — detailed provider and module spec
- `Launch Plan/_index.md` — provider launch wave ordering
- `Archive/MVP Build 2026/launch-execution-guide.md` — original launch product definition
