---
title: "MVP Implementation Plan — Stages 10–16"
tags: [zima, mvp, implementation, stages]
type: implementation_plan
created: 2026-03-22
updated: 2026-04-06
---

# MVP Implementation Plan — Stages 10–16

This document is the single authoritative source for launch scope.
It supersedes the individual wave docs (`wave-0` through `wave-3`), which remain as research background.

## Deferred — Not In Launch Scope

These were evaluated and explicitly removed:

- **epieos** — no public API, ToS prohibits automation, enterprise contract required
- **accounts (soxoj)** — GitHub repo 404, replaced by mailcat + holehe + maigret pipeline
- **skymem** — HTML scraping only, no official API
- **truecaller** — no commercial API available
- **twilio** — OTP-only auth use only; does not belong in the provider layer
- **socid_extractor** — P2 enrichment, post-launch
- **ahmia / darksearch** — deferred; IntelX covers the dark-web story at launch
- **sociallinks** — commercial identity graph, requires trial contract
- **huginn_muninn** — DHCP fingerprint DB, P3
- **local LLM classification** — post-launch; requires production misclassification data first

---

## Full Launch Provider Scope

### Identity Pillar

| Provider | Path | Module(s) | Wave | Priority |
|---|---|---|---|---|
| hibp | `providers/breach/hibp` | `breach_monitor` | 0 | P0 |
| dehashed | `providers/breach/dehashed` | `breach_monitor`, `credential_exposure` | 1 | P0 |
| leakcheck | `providers/breach/leakcheck` | `credential_exposure` | 1 | P0 |
| breachdirectory | `providers/breach/breachdirectory` | `breach_monitor` | 1 | P1 |
| hudson_rock | `providers/breach/hudson_rock` | `stealer_log_exposure` | 1 | P1 |
| emailrep | `providers/reputation/emailrep` | `account_enumeration_risk` | 1 | P1 |
| holehe | `providers/tools/holehe` | `account_inventory`, `account_enumeration_risk` | 1 | P1 |
| maigret | `providers/tools/maigret` | `username_exposure` | 1 | P1 |
| whatsmyname | `providers/tools/whatsmyname` | `account_inventory`, `alias_correlation` | 1 | P1 |
| mailcat | `providers/tools/mailcat` | `account_inventory` | 1 | P1 |
| intelx | `providers/threat_intel/intelx` | `darkweb_identity_monitor` | 2 | P1 |
| emailformat | `providers/social/emailformat` | `alias_correlation` | 2 | P2 |
| gravatar | `providers/social/gravatar` | `public_profile_scan` | 2 | P2 |
| emailcrawlr | `providers/social/emailcrawlr` | `public_profile_scan` | 2 | P2 |
| numverify | `providers/phone/numverify` | `phone_exposure` | 3 | P2 |
| callername | `providers/phone/callername` | `phone_exposure` | 3 | P2 |

### Device Pillar

| Provider | Path | Module(s) | Wave | Priority |
|---|---|---|---|---|
| osquery | `providers/tools/osquery` | `os_security`, `patch_status`, `software_vulnerability` | 0 | P0 |
| posture | `providers/tools/posture` | device baseline | 1 | P0 |
| macos_native | `providers/tools/macos_native` | device baseline | 1 | P0 |
| windows_native | `providers/tools/windows_native` | device baseline | 1 | P0 |
| linux_native | `providers/tools/linux_native` | device baseline | 1 | P0 |
| lynis | `providers/tools/lynis` | `os_security`, `firewall_status` | 2 | P1 |
| trivy | `providers/tools/trivy` | `software_vulnerability` | 2 | P1 |
| grype | `providers/tools/grype` | `software_vulnerability` | 2 | P1 |
| syft | `providers/tools/syft` | `software_inventory` | 2 | P2 |
| oui_master_database | `providers/tools/oui_master_database` | `device_inventory` (offline enrichment) | 2 | P2 |

### Browser Pillar

| Provider | Path | Module(s) | Wave | Priority |
|---|---|---|---|---|
| browser_extension_detector | `providers/tools/browser_extension_detector` | `extension_risk` | 0 | P0 |
| get_browser_extension_info | `providers/tools/get_browser_extension_info` | `extension_risk` | 0 | P0 |
| malicious_extension_sentry | `providers/tools/malicious_extension_sentry` | `extension_risk` | 1 | P1 |
| chromium_enterprise_policies | `providers/tools/chromium_enterprise_policies` | `browser_configuration` | 2 | P1 |
| firefox_enterprise_policies | `providers/tools/firefox_enterprise_policies` | `browser_configuration` | 2 | P1 |
| crxcavator | `providers/threat_intel/crxcavator` | `extension_risk` | 2 | P1 |
| chrome_web_store_api | `providers/cloud/chrome_web_store_api` | `extension_risk` | 3 | P2 |
| firefox_addons_site_api | `providers/cloud/firefox_addons_site_api` | `extension_risk` | 3 | P2 |

### Infrastructure

| Provider | Path | Module(s) | Wave | Priority |
|---|---|---|---|---|
| leakix | `providers/threat_intel/leakix` | `infrastructure_exposure` | 2 | Wave 2 |
| frankenstein | `providers/tools/frankenstein` | `infrastructure_exposure`, `browser_configuration` | 2 | Wave 2 |

---

## Staged Implementation Plan

### Stage 10 — Identity Provider Layer

**10a — Breach provider clients: schema + mapper**
- HIBP, DeHashed, LeakCheck, HudsonRock, BreachDirectory
- Introduce `ProviderFinding` typed dataclass in `base/models.py`
- `schemas.py` + `mapper.py` for each

**10b — Social and reputation provider clients: schema + mapper**
- EmailRep, EmailFormat, Gravatar, EmailCrawlr
- Promote all four to registry
- `schemas.py` + `mapper.py` for each

**10c — IntelX client + schema/mapper**
- Full client implementation
- Add to registry

**10d — Subprocess tool clients: Mailcat, WhatsmyName**
- Full client implementations (subprocess pattern — same as holehe/maigret)
- `schemas.py` + `mapper.py`
- Add to registry

---

### Stage 11 — Identity Module Signal Rules

**11a — breach_monitor mapper/rules/schemas**
- `constants.py`, `config.py`, `schemas.py`, `rules.py`, `mapper.py`

**11b — credential_exposure rules/mapper**

**11c — stealer_log_exposure rules/mapper** (HudsonRock)

**11d — account_enumeration_risk rules/mapper** (EmailRep + Holehe account footprint)

**11e — account_inventory rules/mapper** (Holehe + Mailcat + WhatsmyName)

**11f — username_exposure rules/mapper** (Maigret)

**11g — alias_correlation rules/mapper** (EmailFormat + WhatsmyName)

**11h — phone_exposure rules/mapper** (Numverify + CallerName)

**11i — darkweb_identity_monitor module** (new — IntelX)

**11j — public_profile_scan module** (new — Gravatar + EmailCrawlr)

---

### Stage 12 — Device Pillar

**12a — Device provider clients: osquery, posture, macos_native, windows_native, linux_native**

**12b — Device provider clients: lynis, trivy, grype, syft, oui_master_database**

**12c — Device modules: os_security, patch_status, software_vulnerability, firewall_status**

**12d — Device module: device_inventory** (offline OUI enrichment)

**12e — Device module: software_inventory** (syft)

---

### Stage 13 — Browser Pillar

**13a — Browser provider clients: browser_extension_detector, get_browser_extension_info, malicious_extension_sentry**

**13b — Browser provider clients: chromium_enterprise_policies, firefox_enterprise_policies, crxcavator, chrome_web_store_api, firefox_addons_site_api**

**13c — Browser modules: extension_risk, browser_configuration**

---

### Stage 14 — Email Account Identifier Pipeline

**14a — mbox parser improvements**
- Richer metadata extraction, deduplication, performance pass

**14b — Password manager exporters (Wave 1)**
- Bitwarden JSON export package
- Proton Pass JSON export package
- Fields at launch: service name, login URL, username/alias, generated password placeholder, notes (source: email account identifier), tags

**14c — Upload API endpoint**
- `POST /api/v1/assets/import`

**14d — Newsletter and subscription detection pipeline**
- Pre-pass stage before account classification — strips inbox noise before the account inventory is built
- Signals used: `List-Unsubscribe`, `List-ID`, bulk-mail header patterns, known ESP domains, sender frequency, absence of account/security semantics
- Output: review queue with sender/service name, message volume, last seen date, unsubscribe availability, confidence level, recommended action
- Design rule: review workflow only — no silent automated unsubscribes; user approves every action
- Sequencing constraint: build after 14a (mbox parser) is stable

**14e — Email alias management integration (SimpleLogin + Addy.io)**
- Action providers that create per-service email aliases after account discovery
- Sit in the remediation layer — Zima proposes, user approves, provider creates
- Alias flow: account_inventory confirms service → Zima proposes alias → user approves → provider creates alias → alias inserted into PM export
- Requires: per-user provider API key storage, alias naming pattern config
- Sequencing constraint: depends on 14d (newsletter detection) reducing account discovery noise first

**14f — Password manager exporters (Wave 3)**
- 1Password `.1pux` export package
- `.1pux` is a zip archive containing `export.data` JSON
- Sequencing constraint: build after 14b exporters are stable

---

### Stage 15 — Infrastructure

**15a — LeakIX client + schema/mapper + infrastructure_exposure module**

**15b — Frankenstein client + schema/mapper**

---

### Stage 16 — Integration and Wiring

- Remove epieos from registry (deferred — ToS violation)
- Remove twilio from provider layer; keep in auth only for OTP
- Orchestrator updated to use `ProviderFinding` types throughout
- `evaluate_provider_policy()` enforced at orchestrator level for all providers
- End-to-end scan test for each pillar (identity, device, browser)
- Final wave 3 extension store providers wired: chrome_web_store_api, firefox_addons_site_api
