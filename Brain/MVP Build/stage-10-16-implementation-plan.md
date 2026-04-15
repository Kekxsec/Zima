---
tags: [zima, mvp, build, providers, stages]
created: 2026-04-02
updated: 2026-04-15
status: in_progress
related:
  - "[[Zima]]"
  - "[[next-steps-to-launch]]"
  - "[[stage-10-browser-identity-device-providers]]"
---

← [[../Archive/MVP Build 2026/MVP Master|MVP Stage History]]

# Stage 10–16 — Provider and Module Implementation Plan

Confirmed provider scope and implementation order for all remaining stages. See [[next-steps-to-launch]] for the launch checklist view.

For the older deep spec that breaks down the browser, device, and identity provider slice in more detail, see [[stage-10-browser-identity-device-providers]].

**Deferred providers (removed from scope):**
- `epieos` — no public API, ToS prohibits automation. Remove from registry.
- `accounts` (soxoj) — GitHub repo 404. Replaced by mailcat + holehe + maigret.
- `twilio` — auth only (OTP sending), not a scan provider. Move out of `providers/` or remove.

---

## Identity Pillar — P0/P1 Providers

| Provider | Path | Module(s) | Priority | Status |
|---|---|---|---|---|
| hibp | `providers/breach/hibp` | breach_monitor | P0 | client done, schema stub only |
| dehashed | `providers/breach/dehashed` | breach_monitor, credential_exposure | P0 | ✅ client + schema + mapper |
| leakcheck | `providers/breach/leakcheck` | credential_exposure | P0 | ✅ client + schema + mapper + wired into breach_monitor |
| breachdirectory | `providers/breach/breachdirectory` | breach_monitor | P1 | ✅ client + schema + mapper |
| hudson_rock | `providers/breach/hudson_rock` | stealer_log_exposure | P1 | ✅ client + schema + mapper |
| emailrep | `providers/reputation/emailrep` | account_enumeration_risk | P1 | ✅ client + schema + mapper |
| holehe | `providers/tools/holehe` | account_inventory, account_enumeration_risk | P1 | ✅ client + schema + mapper |
| maigret | `providers/tools/maigret` | username_exposure | P1 | ✅ client + schema + mapper |
| mailcat | `providers/tools/mailcat` | account_inventory | P1 | ✅ client + schema + mapper |
| whatsmyname | `providers/tools/whatsmyname` | account_inventory, alias_correlation | P1 | ✅ client + schema + mapper |
| intelx | `providers/threat_intel/intelx` | breach_monitor, darkweb_identity_monitor | P1 | ✅ client + schema + mapper |
| emailformat | `providers/social/emailformat` | alias_correlation | P2 | ✅ schema + mapper (enrichment-only) |
| gravatar | `providers/social/gravatar` | public_profile_scan | P2 | ✅ schema + mapper (enrichment-only) |
| skymem | `providers/social/skymem` | username_exposure | P2 | ✅ schema + mapper |
| emailcrawlr | `providers/social/emailcrawlr` | username_exposure | P2 | ✅ schema + mapper |
| socid_extractor | `providers/tools/socid_extractor` | username_exposure, account_inventory | P2 | not implemented — deferred |

## Identity Pillar — Optional at Launch (P2/P3)

| Provider | Path | Module | Priority |
|---|---|---|---|
| numverify | `providers/phone/numverify` | phone_exposure | P2 |
| truecaller | `providers/phone/truecaller` | phone_exposure | P2 — DEFERRED (no API) |
| callername | `providers/phone/callername` | phone_exposure | P2 |
| ahmia | `providers/darkweb/ahmia` | darkweb_identity_monitor | P3 |
| darksearch | `providers/darkweb/darksearch` | darkweb_identity_monitor | P3 |

---

## Device Pillar — P0 (local subprocess, agent-dependent)

| Provider | Path | Module(s) | Priority | Status |
|---|---|---|---|---|
| osquery | `providers/tools/osquery` | os_security, patch_status, software_vulnerability | P0 | ✅ client done |
| posture | `providers/tools/posture` | device baseline | P0 | client exists |
| macos_native | `providers/tools/macos_native` | device baseline | P0 | ✅ client done |
| windows_native | `providers/tools/windows_native` | device baseline | P0 | ✅ client done |
| linux_native | `providers/tools/linux_native` | device baseline | P0 | ✅ client done |
| lynis | `providers/tools/lynis` | os_security, firewall_status | P1 | ✅ client done |
| trivy | `providers/tools/trivy` | software_vulnerability | P1 | ✅ client done |
| grype | `providers/tools/grype` | software_vulnerability | P1 | ✅ client done |
| oui_master_database | `providers/tools/oui_master_database` | device_inventory (offline enrichment) | P2 | research complete |
| syft | `providers/tools/syft` | software_inventory | P2 | not implemented |

---

## Browser Pillar — P0 (local collector-dependent)

| Provider | Path | Module | Priority | Status |
|---|---|---|---|---|
| browser_extension_detector | `providers/tools/browser_extension_detector` | extension_risk | P0 | ✅ client done |
| get_browser_extension_info | `providers/tools/get_browser_extension_info` | extension_risk | P0 | ✅ client done |
| malicious_extension_sentry | `providers/tools/malicious_extension_sentry` | extension_risk | P0 | ✅ client done |
| chromium_enterprise_policies | `providers/tools/chromium_enterprise_policies` | browser_configuration | P1 | ✅ client done |
| firefox_enterprise_policies | `providers/tools/firefox_enterprise_policies` | browser_configuration | P1 | ✅ client done |
| crxcavator | `providers/threat_intel/crxcavator` | extension_risk | P1 | ✅ client done |
| chrome_web_store_api | `providers/cloud/chrome_web_store_api` | extension_risk | P2 | ✅ client done |
| firefox_addons_site_api | `providers/cloud/firefox_addons_site_api` | extension_risk | P2 | ✅ client done |

---

## Infrastructure (Wave 2 — researched, selective)

| Provider | Path | Module | Priority | Status |
|---|---|---|---|---|
| leakix | `providers/threat_intel/leakix` | infrastructure_exposure | Wave 2 | ✅ client + schema + mapper |
| frankenstein | `providers/tools/frankenstein` | infrastructure_exposure, browser_configuration | Wave 2 | ✅ client + schema + mapper |

---

## Post-Launch / Enterprise

| Provider | Notes |
|---|---|
| sociallinks | Commercial identity graph, 500+ sources — requires trial contract |
| huginn_muninn | DHCP fingerprint DB, 11M records — unique value but P3 |

---

## Stage-by-Stage Implementation Order

### Stage 10 — Complete the Identity Provider Layer

**10a — P0 breach provider schemas/mappers** ✅ Done (2026-04-09)
- `ProviderFinding` typed dataclass in `base/models.py`
- `schemas.py` + `mapper.py` for: dehashed, leakcheck, hudson_rock, breachdirectory
- LeakCheck wired into `breach_monitor` module

**10b — Social/reputation schemas/mappers** ✅ Done (2026-04-09)
- `schemas.py` + `mapper.py` for: emailrep, emailformat, gravatar, skymem, emailcrawlr
- emailformat and gravatar are enrichment-only (no raw payload)

**10c — IntelX schemas/mapper** ✅ Done (2026-04-15)
- `schemas.py` + `mapper.py` present in `providers/threat_intel/intelx/`
- Mapper contract verified by `tests/unit/providers/test_mapper_contracts.py`

**10d — Subprocess tool schemas/mappers** ✅ Done (2026-04-15)
- `schemas.py` + `mapper.py` present for mailcat, whatsmyname, holehe, maigret
- Mapper contract verified by `tests/unit/providers/test_mapper_contracts.py`

### Stage 11 — Identity Module Signal Rules *(substantially complete as of 2026-04-15)*

| Sub-stage | Module | Status |
|---|---|---|
| 11a | breach_monitor | ✅ Complete — fully implemented with HIBP, dehashed, leakcheck, breachdirectory |
| 11b | credential_exposure | ✅ Complete — dehashed + leakcheck |
| 11c | stealer_log_exposure | ✅ Complete — hudson_rock |
| 11d | account_enumeration_risk | ✅ Complete — emailrep + holehe |
| 11e | account_inventory | ✅ Complete — holehe + mailcat + whatsmyname |
| 11f | username_exposure | ✅ Complete — emailcrawlr + gravatar (maigret in separate maigret_scan module) |
| 11g | alias_correlation | ✅ Complete — whatsmyname |
| 11h | phone_exposure | 🔲 Not started — numverify, callername (deferred pre-launch) |
| 11i | darkweb_identity_monitor | ✅ Complete — intelx |
| 11j | public_profile_scan | ✅ Complete — gravatar + emailcrawlr |

**Launch-scope remaining gap:** None. Phone providers remain deferred pre-launch.

### Stage 12 — Device Pillar *(substantially complete as of 2026-04-15)*

All provider clients and module services are implemented:
- **Providers:** osquery, macos_native, windows_native, linux_native, lynis, trivy, grype — all have `client.py`
- **Modules:** os_security (281 lines), patch_status (246 lines), software_vulnerability (200 lines), firewall_status, device_inventory, software_inventory — all implemented

**Remaining gap:** Coverage can expand later, but the launch-scope device module suite is in place (40 passing tests).

### Stage 13 — Browser Pillar *(substantially complete as of 2026-04-15)*

All provider clients and module services are implemented:
- **Providers:** browser_extension_detector, get_browser_extension_info, malicious_extension_sentry, chromium_enterprise_policies, firefox_enterprise_policies, crxcavator, chrome_web_store_api, firefox_addons_site_api — all have `client.py`
- **Modules:** extension_risk (358 lines), browser_configuration (241 lines) — both implemented

**Remaining gap:** Unit tests exist for extension_risk and browser_configuration but coverage is partial.

### Stage 14 — File Upload Parsers ✅ Complete (2026-04-15)

- **14a** — mbox parser: upload now streams to temp storage, parser supports file-based iteration, richer headers, and fallback dedup
- **14b** — Password manager exporters: Bitwarden, Proton Pass, and 1Password `.1pux` verified by `tests/unit/providers/test_vault_export_providers.py`
- **14c** — Upload API endpoint: ✅ `POST /imports/vault` implemented
- **14d** — Newsletter detection pipeline: scored classifier implemented in `backend/app/email_accounts/newsletter.py` and applied in `backend/app/jobs/mbox_processor.py`
- **14e** — Email alias management: SimpleLogin/Addy.io integration and alias-creation endpoints live in `api/v1/integrations.py` and `api/v1/email_accounts.py`

### Stage 15 — Infrastructure Providers ✅ Complete (2026-04-15)

- **LeakIX:** ✅ client + schema + mapper
- **Frankenstein:** ✅ client + schema + mapper
- **infrastructure_exposure module:** ✅ Implemented (287 lines), uses LeakIX
- Mapper contract verified by `tests/unit/providers/test_mapper_contracts.py`

### Stage 16 — Integration & Wiring ✅ Complete (2026-04-15)

- [x] Remove epieos from registry — removed from `email_accounts/scan_inventory.py` `_PROVIDER_TO_SOURCE_TYPE`
- [x] Twilio scope audited — not used in any active module; no change needed
- [x] `ProviderFinding` usage audited — correct usage in `infrastructure_exposure`; no issues
- [x] `evaluate_provider_policy()` enforced at orchestrator — `_policy_allows_module()` gate in `runner.py::run_for_user()`
- [x] End-to-end pillar tests — `tests/integration/test_e2e_pillars.py`: 10 tests passing (identity ×3, device ×2, browser ×5)
