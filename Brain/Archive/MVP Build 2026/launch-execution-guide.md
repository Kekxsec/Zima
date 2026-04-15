---
tags: [zima, mvp, launch, execution, guide]
created: 2026-03-23
updated: 2026-03-23
---

← [[../../Zima|Zima]] · [[MVP Master|MVP Master]] · [[../../MVP Build/MVP Next Steps|Next Steps]]

# Launch Execution Guide

Comprehensive guide for the Zima launch product: a **one-and-done paid personal security audit** that discovers what's wrong, guides the user through fixing it, and gets them set up with proper tooling.

This supersedes the generic next-steps docs for launch planning purposes. The MVP stages, architecture, and extension patterns remain valid — this guide scopes what to actually build and in what order.

---

## Launch Product Definition

The launch product is not an ongoing monitoring subscription. It is a single paid engagement that delivers:

1. **Identity exposure report** — breaches, credential leaks, stealer logs
2. **Account discovery** — passive scan + mbox-based comprehensive inventory
3. **Password manager migration** — prioritised account list with reset guides, exportable to Bitwarden/1Password
4. **Browser audit + hardening** — extension risk, configuration audit, recommended settings and extensions
5. **Device baseline** — OS posture, patching, encryption, firewall
6. **Scored action plan** — prioritised remediation with specific tool recommendations

The user enters their information, Zima finds everything wrong, and guides them through fixing it in priority order.

---

## What This Changes From Current Planning

| Current assumption                          | Launch reality                                                         | Impact                                                 |
| ------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------ |
| Subscription tiers (Core/Plus/Pro/Business) | One-time paid audit                                                    | Simplifies billing, removes tier gating from providers |
| Ongoing monitoring + breach alerts          | One-time scan with report                                              | Stage 06b (alerts) deferred past launch                |
| 150+ providers across all domains           | ~20 providers across 4 pillars                                         | Research scope dramatically narrower                   |
| Signal registry for all tiers               | Signal registry for launch pillars only                                | Synthesis is smaller and faster                        |
| No inbox/mbox scanning                      | Mbox scanner is centrepiece feature                                    | New component to build                                 |
| Account-Identify is separate project        | Absorbed into Zima as account inventory + PM migration UI              | Integration work required                              |
| Remediation is generic playbook mapping     | Remediation includes specific tool recommendations + guided reset flow | Playbook content is a deliverable                      |

---

## Part 1: Research — What to Research and Why

### Research Scope for Launch

You only need research for providers that serve the four launch pillars. Everything else is deferred.

#### Pillar 1: Identity Exposure (breach + credential)

These providers answer: "Have your credentials or identity been compromised?"

| Provider | Priority | Why | Research status |
|---|---|---|---|
| `hibp` | P0 | Anchor breach source, already built as provider | needs output.md |
| `dehashed` | P0 | Richest credential data (password hashes, cleartext) | needs output.md |
| `leakcheck` | P0 | Credential lookup, good coverage | needs output.md |
| `breachdirectory` | P1 | Supplementary breach coverage | needs output.md |
| `hudson_rock` | P1 | Stealer log exposure — critical severity signals | needs output.md |
| `emailrep` | P1 | Email reputation + exposure context | needs output.md |

**Research question per provider:** What fields come back? Which fields trigger signals? What severity? What's the auth/rate-limit model?

#### Pillar 2: Account Discovery (social + tools)

These providers answer: "What accounts do you have, and which need attention?"

| Provider | Priority | Why | Research status |
|---|---|---|---|
| `accounts` | P0 | Username-to-service discovery from handles | needs output.md |
| `holehe` | P1 | Email-to-service account existence check | needs output.md |
| `epieos` | P1 | Email-based account + alias discovery | needs output.md |
| `maigret` | P1 | Username footprint across 2000+ sites | needs output.md |
| `whatsmyname` | P1 | Username-to-service presence check | needs output.md |

**Research question per provider:** What services does it check? What does a hit look like? What's the false positive rate? How does it complement the others?

**Important:** These providers produce `utility_only` or `enrichment_only` output for the account inventory — they don't emit standalone signals. The signals come from cross-referencing discovered accounts with breach data and MFA status.

#### Pillar 3: Browser Audit + Hardening

| Provider | Priority | Why | Research status |
|---|---|---|---|
| `browser_extension_detector` | P0 | Detect installed extensions locally | needs output.md |
| `get_browser_extension_info` | P0 | Normalise extension metadata + permissions | needs output.md |
| `malicious_extension_sentry` | P0 | Known-bad extension classification | needs output.md |
| `chromium_enterprise_policies` | P1 | Browser config/policy audit (Chromium) | needs output.md |
| `firefox_enterprise_policies` | P1 | Browser config/policy audit (Firefox) | needs output.md |
| `crxcavator` | P1 | Extension reputation enrichment | needs output.md |

**Additionally needed (no provider — remediation content only):**
- Browser hardening settings checklist (DNS-over-HTTPS, HTTPS-only, autofill off, etc.)
- Recommended extension stack (uBlock Origin, Bitwarden, Malwarebytes Browser Guard)
- Recommended browser configuration per browser (Firefox, Brave, Chrome)

#### Pillar 4: Device Baseline

| Provider | Priority | Why | Research status |
|---|---|---|---|
| `osquery` | P0 | Broad device inventory + posture | needs output.md |
| `posture` | P0 | Opinionated posture checks | needs output.md |
| `macos_native` | P0 | macOS-specific baseline | needs output.md |
| `windows_native` | P0 | Windows-specific baseline | needs output.md |
| `linux_native` | P0 | Linux-specific baseline | needs output.md |

**P1 additions (after core device baseline works):**

| Provider | Priority | Why                            |
| -------- | -------- | ------------------------------ |
| `lynis`  | P1       | Host hardening audit           |
| `trivy`  | P1       | Vulnerable package scanning    |
| `grype`  | P1       | Package vulnerability scanning |

### What NOT to Research for Launch

- All `domain/` providers — no domain audit at launch
- All `ip/` providers — no infrastructure scanning
- Most `threat_intel/` — no IOC feeds at launch (exception: `crxcavator` for browser extensions)
- All `cloud/` — no cloud posture at launch
- All `crypto/` — not relevant
- All `search/` — not relevant
- `darkweb/` providers — defer; breach providers already cover credential exposure
- `phone/` providers — defer; low value for a one-time audit
- `content_analysis/` — utility layer, research only when a consuming module needs it
- `serus` — deferred until API existence confirmed

### Research Order

Follow the existing wave order from `launch-provider-research-plan.md` with this adjustment:

**Round 1 — Do first (the scan loop depends on these):**
1. `hibp`
2. `accounts`
3. `osquery`
4. `browser_extension_detector`
5. `get_browser_extension_info`

**Round 2 — Do second (enriches round 1 results):**
6. `dehashed`
7. `leakcheck`
8. `breachdirectory`
9. `emailrep`
10. `epieos`
11. `holehe`
12. `maigret`
13. `whatsmyname`

**Round 3 — Do third (completes the audit):**
14. `posture`
15. `macos_native`
16. `windows_native`
17. `linux_native`
18. `malicious_extension_sentry`
19. `hudson_rock`

**Round 4 — Do fourth (hardening depth):**
20. `chromium_enterprise_policies`
21. `firefox_enterprise_policies`
22. `crxcavator`
23. `lynis`
24. `trivy`
25. `grype`

### How to Research Each Provider

For each provider, follow the `provider-research-protocol.md` process:

1. Read the provider's `prompt.md`
2. Research using official docs, API references, and SDK documentation
3. Fill the provider's `output.md` with:
   - API/tool surface appendix
   - Module mapping table
   - Signal contract table (only for `direct_signal_input` providers)
   - Confidence guidance
   - Implementation notes
4. Update `output.md` status to `complete` or `deferred`

**The critical output per provider is:** what fields come back, what triggers a signal, what severity, and what evidence to store.

---

## Part 2: After Research — Signal Registry Synthesis

Once the provider research outputs are complete, synthesise them into a single canonical registry. This is the bridge between research and code.

### Step 1: Collect All Signal Rows

Go through every completed `output.md` and extract the signal contract rows. You will end up with a flat list of signals like:

```
hibp          → email_breached (high)
dehashed      → email_breached (high/critical conditional)
dehashed      → credential_exposed (critical)
leakcheck     → credential_exposed (critical)
hudson_rock   → stealer_log_hit (critical)
breachdirectory → email_breached (medium)
...
```

### Step 2: Deduplicate and Normalise

Multiple providers may produce the same logical signal. Merge them:

- `hibp` and `breachdirectory` both produce `email_breached` → same signal_type, different provider field in evidence
- `dehashed` and `leakcheck` both produce `credential_exposed` → same signal_type
- Do NOT merge signals that have materially different severity or meaning

**Naming rules:**
- Use `snake_case` consistently
- One canonical name per concept
- Module owns the signal, not the provider
- Example: `email_breached`, not `hibp_breach_found`

### Step 3: Assign Module Ownership

Every signal must belong to exactly one module. Map them:

| Module | Signals it owns |
|---|---|
| `breach_monitor` | `email_breached`, `domain_breached` |
| `credential_exposure` | `credential_exposed`, `plaintext_password_leaked` |
| `stealer_log_exposure` | `stealer_log_hit` |
| `account_inventory` | (utility — no standalone signals; feeds into cross-reference) |
| `username_exposure` | `username_widely_exposed` |
| `extension_risk` | `malicious_extension_detected`, `risky_extension_permissions` |
| `browser_configuration` | `browser_insecure_setting` |
| `os_security` | `disk_encryption_disabled`, `firewall_disabled`, `screen_lock_disabled` |
| `patch_status` | `os_update_available`, `critical_patch_missing` |
| `software_vulnerability` | `vulnerable_package_found` |

### Step 4: Freeze Severity Rules

For each signal, lock the severity logic:

```
email_breached:
  - high: email found in breach, no password data present
  - critical: password hash or plaintext present in breach record

credential_exposed:
  - critical: always (password data confirmed)

stealer_log_hit:
  - critical: always (active credential theft)

malicious_extension_detected:
  - critical: known malware extension
  - high: known data-harvesting extension
  - medium: excessive permissions, unverified publisher

disk_encryption_disabled:
  - high: always (direct physical access risk)
```

### Step 5: Define Evidence Fields

For each signal, list the raw provider fields that must be stored in the signal's `evidence` object. These are needed for:

- Deduplication (the hash ID)
- Remediation context (what to show the user)
- Audit trail
- Future confidence calibration

### Step 6: Write the Canonical signal-registry.md

Create `/Zima/Research/signal-registry.md` with one row per (signal_type, provider) pair using the full signal contract table format.

### Step 7: Define the Provisional Confidence Policy

Do not block on perfect confidence. Adopt:

- Authoritative sources (HIBP, SpamHaus) → provisional `high`
- Well-maintained tools with known accuracy (holehe, maigret) → provisional `medium`
- Noisy or unverified sources → provisional `low`
- Add `# TODO: calibrate after N scans` to each

---

## Part 3: After Signal Registry — What to Build

### The Build Sequence

Once the signal registry is frozen, the build proceeds in this order:

```
1. Provider clients        — fetch + parse only
2. Module rules + mappers  — severity + SignalCreate
3. Scan orchestrator       — runs modules in sequence (Stage 6)
4. API endpoints           — expose scan results (Stage 6)
5. Mbox scanner            — account discovery from email archive
6. Account-Identify merge  — inventory UI + PM export + guided reset
7. Browser hardening       — remediation content (no code, just playbook data)
8. Scoring + remediation   — score calculator + playbook engine
9. Billing                 — one-time payment via Stripe (Stage 7)
10. Hardening              — security audit, monitoring (Stage 8)
```

### Build Block 1: Provider Clients (one per provider)

For each launch provider, implement:

```
backend/app/providers/<category>/<name>/
├── client.py      — HTTP calls or local command execution
├── schemas.py     — Pydantic models for raw response
├── mapper.py      — raw response → list of dicts (not SignalCreate yet)
└── exceptions.py  — provider-specific errors
```

**Rules:**
- `client.py` only fetches and parses
- No severity logic in the provider
- No imports from modules/

**Order:** HIBP is already built. Next: `dehashed`, `leakcheck`, then the rest following the research round order.

### Build Block 2: Modules (one per security domain)

For each launch module, implement:

```
backend/app/modules/<domain>/<name>/
├── service.py     — BaseModuleService, calls provider(s), returns signals
├── mapper.py      — provider output → SignalCreate with severity
├── rules.py       — severity decision logic (from signal registry)
├── schemas.py     — module-specific types
└── constants.py   — thresholds, port lists, etc.
```

**Launch modules to build:**

| Module | Domain | Providers it consumes |
|---|---|---|
| `breach_monitor` | identity | hibp, breachdirectory |
| `credential_exposure` | identity | dehashed, leakcheck |
| `stealer_log_exposure` | identity | hudson_rock |
| `username_exposure` | identity | emailrep, epieos, maigret, whatsmyname |
| `account_inventory` | accounts | accounts, holehe (utility — feeds inventory, not signals) |
| `extension_risk` | browser | browser_extension_detector, get_browser_extension_info, malicious_extension_sentry, crxcavator |
| `browser_configuration` | browser | chromium_enterprise_policies, firefox_enterprise_policies |
| `os_security` | device | osquery, posture, macos_native, windows_native, linux_native |
| `patch_status` | device | osquery, native checks |
| `software_vulnerability` | device | trivy, grype |

### Build Block 3: Mbox Scanner (new component)

This is a new component that doesn't exist in the current architecture. It sits alongside the provider layer as an alternative account discovery source.

```
backend/app/tools/mbox_scanner/
├── parser.py          — RFC 4155 mbox parsing, extract From/Subject/body
├── classifier.py      — message type classification (signup, reset, security, marketing)
├── domain_resolver.py — sender domain → service name + metadata
├── deduplicator.py    — subdomain collapsing, alias merging
└── schemas.py         — DiscoveredAccount model
```

**Or** keep it in Account-Identify as a standalone local tool that outputs JSON, and have Zima consume that JSON. This may be cleaner architecturally — the mbox file never touches the backend.

**Key design decision:** The mbox scanner should run entirely client-side (in the browser via Account-Identify) or entirely locally. Email data should never be uploaded to Zima's servers. This is a trust and privacy requirement.

**Output:** A list of `DiscoveredAccount` objects:

```json
{
  "domain": "github.com",
  "display_name": "GitHub",
  "confidence": "high",
  "evidence_types": ["signup_confirmation", "security_alert"],
  "first_seen": "2019-03-14",
  "last_seen": "2026-03-20",
  "message_count": 47,
  "category": "developer"
}
```

This list gets merged with the passive discovery results (holehe/maigret/whatsmyname) and enriched with:
- 2fa.directory data (MFA support, methods)
- Breach cross-reference (is this account in a known breach?)
- Sign-in / password reset / MFA setup URLs

### Build Block 4: Account-Identify Integration

Absorb the existing Account-Identify repo into Zima. It becomes the frontend for:

1. **Account inventory display** — shows all discovered accounts (passive + mbox)
2. **Breach cross-reference** — flags breached accounts
3. **MFA status** — shows which services support MFA (from 2fa.directory)
4. **Priority sorting** — breached + finance/email/cloud + MFA-capable = fix first
5. **Guided reset flow** — per-service card with sign-in link, reset link, MFA setup link
6. **Password manager export** — Bitwarden CSV, 1Password CSV

**What to keep from Account-Identify:**
- `build-service-db.js` — service database from 2fa.directory
- Encrypted local persistence (AES-GCM)
- Zima branding and dark/light mode
- Security hardening (CSP, no backend)

**What to add:**
- Mbox file import (drag-and-drop or file picker)
- Mbox parser running in a Web Worker
- Import from Zima scan results (JSON from passive discovery)
- Breach status overlay per account
- Reset/MFA guided flow UI
- Export buttons (Bitwarden CSV, 1Password CSV, generic CSV)

### Build Block 5: Browser Hardening Playbook

This is remediation content, not code. Create a structured data file that the remediation engine can reference:

```json
{
  "browser_hardening": {
    "dns_over_https": {
      "title": "Enable DNS-over-HTTPS with malware blocking",
      "why": "Encrypts DNS queries and blocks known malicious domains at the DNS level",
      "firefox": "Settings → Privacy & Security → DNS over HTTPS → Max Protection → Quad9",
      "chrome": "Settings → Privacy & Security → Use Secure DNS → Quad9",
      "recommended_resolver": "Quad9 (dns.quad9.net) — blocks malware, nonprofit, zero-logging"
    },
    "https_only": {
      "title": "Enable HTTPS-Only Mode",
      "firefox": "Settings → Privacy & Security → HTTPS-Only Mode → Enable in all windows",
      "chrome": "Settings → Privacy & Security → Always use secure connections → On"
    },
    "disable_autofill": {
      "title": "Disable built-in password and payment autofill",
      "why": "Use Bitwarden instead — it provides phishing protection by matching exact domains",
      "firefox": "Settings → Privacy & Security → Logins and Passwords → uncheck all",
      "chrome": "Settings → Autofill and passwords → disable Password Manager, Payment methods, Addresses"
    },
    "recommended_extensions": [
      {"name": "uBlock Origin", "why": "Ad/tracker/malware blocking via filter lists", "url": "..."},
      {"name": "Bitwarden", "why": "Password manager with domain-matched autofill (phishing protection)", "url": "..."},
      {"name": "Malwarebytes Browser Guard", "why": "Real-time phishing and scam detection", "url": "..."}
    ],
    "recommended_browser": {
      "primary": "Firefox — native DoH, HTTPS-only, Enhanced Tracking Protection, Container Tabs",
      "alternative": "Brave — built-in ad/tracker blocking, fingerprinting protection, Chromium-based"
    }
  }
}
```

### Build Block 6: Scoring + Remediation

Update the existing scoring and remediation layers for the launch signal set:

**Score domains for launch:**
- `identity` — breach + credential exposure signals
- `browser` — extension risk + configuration signals
- `device` — OS security + patching + vulnerability signals

**Remediation playbook entries to add:**

| Signal | Playbook |
|---|---|
| `email_breached` | `rotate_credentials` |
| `credential_exposed` | `rotate_credentials_urgent` |
| `stealer_log_hit` | `rotate_credentials_urgent` + `scan_device_for_malware` |
| `malicious_extension_detected` | `remove_extension` |
| `risky_extension_permissions` | `review_extension` |
| `browser_insecure_setting` | `browser_hardening` (references the playbook data above) |
| `disk_encryption_disabled` | `enable_disk_encryption` |
| `firewall_disabled` | `enable_firewall` |
| `critical_patch_missing` | `apply_updates` |
| `vulnerable_package_found` | `update_package` |

**Tool recommendations per playbook:**

| Playbook | Tool recommendations |
|---|---|
| `rotate_credentials` | Bitwarden (free), 1Password |
| `rotate_credentials_urgent` | Bitwarden + enable MFA immediately (Ente Auth, Aegis) |
| `browser_hardening` | Firefox, uBlock Origin, Malwarebytes Browser Guard, Quad9 DNS |
| `scan_device_for_malware` | Malwarebytes (free scan), built-in Defender/XProtect |
| `enable_disk_encryption` | FileVault (macOS), BitLocker (Windows), LUKS (Linux) |

---

## Part 4: Updated MVP Stage Sequence

### What Changes in the Existing Stages

| Stage | Original scope | Launch scope | Notes |
|---|---|---|---|
| 06 | Jobs, API, orchestration | Same but scoped to launch modules only | Build ScanOrchestrator for ~10 modules, not 50+ |
| 06b | Breach alerts + stale scans | **Defer past launch** | One-time audit doesn't need ongoing alerts |
| 07 | GDPR + Stripe billing | Stripe one-time payment only; GDPR still needed | Simpler billing — no subscription management |
| 08 | Pre-launch hardening | Same | Still required before real users |

### New Stages / Work Blocks

| Block | What | When |
|---|---|---|
| Mbox scanner | Parser + classifier + domain resolver | After Stage 6, before Stage 7 |
| Account-Identify integration | Absorb repo, add mbox import + breach overlay + export | After mbox scanner |
| Browser hardening content | Structured playbook data for browser recommendations | Anytime — no code dependency |
| Tool recommendation engine | Extend remediation playbooks with specific product recommendations | During Stage 6 remediation updates |

### Revised Stage Sequence

```
Current state: Stages 0–5 complete, 17/17 tests passing
                                      │
                    ┌─────────────────────────────────────┐
                    │  RESEARCH PHASE (you are here)      │
                    │                                     │
                    │  1. Complete provider output.md      │
                    │     files for launch providers       │
                    │     (Rounds 1–4, ~25 providers)     │
                    │                                     │
                    │  2. Synthesise signal-registry.md    │
                    │                                     │
                    │  3. Freeze severity + evidence       │
                    │                                     │
                    │  4. Build implementation queue       │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  STAGE 6: Build the scan engine     │
                    │                                     │
                    │  a. Provider clients (Round 1 first) │
                    │  b. Module rules + mappers           │
                    │  c. ScanOrchestrator                 │
                    │  d. Scan/findings/scores API         │
                    │  e. Correlation rules                │
                    │  f. Score calculators (3 domains)    │
                    │  g. Remediation playbooks            │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  MBOX SCANNER + ACCOUNT-IDENTIFY    │
                    │                                     │
                    │  a. Mbox parser (client-side)        │
                    │  b. Service classifier               │
                    │  c. 2fa.directory enrichment          │
                    │  d. Breach cross-reference            │
                    │  e. Account-Identify UI integration   │
                    │  f. PM export (Bitwarden/1Password)   │
                    │  g. Guided reset flow                 │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  STAGE 7: Billing + GDPR            │
                    │                                     │
                    │  a. Stripe one-time payment           │
                    │  b. GDPR deletion + export            │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  STAGE 8: Pre-launch hardening       │
                    │                                     │
                    │  a. Security audit                    │
                    │  b. Dependency scan                   │
                    │  c. Monitoring (Sentry + uptime)      │
                    │  d. Browser hardening content QA      │
                    └──────────────┬──────────────────────┘
                                   │
                                   ▼
                              LAUNCH
```

---

## Part 5: Complete Task Checklist

### Phase A: Research (current phase)

- [ ] Complete output.md for Round 1 providers (hibp, accounts, osquery, browser_extension_detector, get_browser_extension_info)
- [ ] Complete output.md for Round 2 providers (dehashed, leakcheck, breachdirectory, emailrep, epieos, holehe, maigret, whatsmyname)
- [ ] Complete output.md for Round 3 providers (posture, macos_native, windows_native, linux_native, malicious_extension_sentry, hudson_rock)
- [ ] Complete output.md for Round 4 providers (chromium_enterprise_policies, firefox_enterprise_policies, crxcavator, lynis, trivy, grype)

### Phase B: Signal Registry Synthesis

- [ ] Collect all signal rows from completed output.md files
- [ ] Deduplicate and normalise signal names
- [ ] Assign module ownership for each signal
- [ ] Freeze severity rules (including conditional logic)
- [ ] Define evidence fields per signal
- [ ] Write canonical signal-registry.md
- [ ] Define provisional confidence policy
- [ ] Review: naming consistency, category alignment, entity types

### Phase C: Implementation Queue

- [ ] Create implementation queue for provider clients
- [ ] Create implementation queue for modules
- [ ] Map correlation rules to add
- [ ] Map score calculators to update
- [ ] Map remediation playbooks to create
- [ ] Identify test fixtures needed per provider

### Phase D: Stage 6 Build

- [ ] Provider clients — Round 1 providers
- [ ] Provider clients — Round 2 providers
- [ ] Provider clients — Round 3 providers
- [ ] Provider clients — Round 4 providers
- [ ] Module: breach_monitor (rules.py + mapper.py)
- [ ] Module: credential_exposure
- [ ] Module: stealer_log_exposure
- [ ] Module: username_exposure
- [ ] Module: account_inventory
- [ ] Module: extension_risk
- [ ] Module: browser_configuration
- [ ] Module: os_security
- [ ] Module: patch_status
- [ ] Module: software_vulnerability
- [ ] ScanOrchestrator — register all modules
- [ ] API endpoints — scans, findings, scores
- [ ] Correlation rules — cross-breach identity risk, cross-signal device risk
- [ ] Score calculators — identity, browser, device
- [ ] Remediation playbooks — all launch signals mapped

### Phase E: Mbox Scanner + Account-Identify

- [ ] Design: mbox scanner architecture (client-side in Account-Identify vs backend)
- [ ] Mbox parser — RFC 4155 format, extract headers + body snippets
- [ ] Message classifier — signup/reset/security/marketing pattern matching
- [ ] Domain resolver — sender domain → service name via service-db
- [ ] Subdomain deduplicator — collapse mail.x.com, noreply.x.com → x.com
- [ ] Account-Identify: mbox file import UI (drag-and-drop)
- [ ] Account-Identify: Web Worker for background parsing
- [ ] Account-Identify: import Zima scan results (passive discovery JSON)
- [ ] Account-Identify: merge + deduplicate passive + mbox results
- [ ] Account-Identify: breach status overlay (cross-ref with scan results)
- [ ] Account-Identify: MFA status from 2fa.directory enrichment
- [ ] Account-Identify: priority sorting (breached + high-value + MFA-capable)
- [ ] Account-Identify: guided reset flow (per-service card with action links)
- [ ] Account-Identify: password manager export (Bitwarden CSV, 1Password CSV)
- [ ] Service database: add sign-in URL mappings for top 200 services
- [ ] Service database: add password reset URL mappings
- [ ] Service database: add MFA setup URL mappings
- [ ] Service database: domain alias mappings (amazonses.com → Amazon)
- [ ] Guide: how to export mbox from Gmail
- [ ] Guide: how to export mbox from Outlook
- [ ] Guide: how to export mbox from Apple Mail

### Phase F: Browser Hardening Content

- [ ] DNS-over-HTTPS setup guide (Firefox + Chrome + Brave) with Quad9 recommendation
- [ ] HTTPS-only mode setup guide
- [ ] Autofill disable guide (use Bitwarden instead)
- [ ] Recommended extension list with install links
- [ ] Recommended browser comparison (Firefox vs Brave)
- [ ] Cookie/tracker blocking settings guide
- [ ] Permission defaults guide (camera, mic, location, notifications)
- [ ] Search engine recommendation (DuckDuckGo / Brave Search)

### Phase G: Tool Recommendations Content

- [ ] Password manager recommendation page (Bitwarden, 1Password)
- [ ] MFA app recommendation page (Ente Auth, Aegis, built-in iOS/macOS)
- [ ] Email alias service recommendation (SimpleLogin, iCloud Hide My Email)
- [ ] DNS resolver recommendation (Quad9, NextDNS)
- [ ] VPN recommendation (Mullvad, ProtonVPN)
- [ ] Backup recommendation (Time Machine/Windows Backup + cloud)
- [ ] Data broker removal recommendation (DeleteMe, Optery)
- [ ] Encrypted messaging recommendation (Signal)

### Phase H: Stage 7 — Billing + GDPR

- [ ] Stripe one-time payment integration
- [ ] Payment → scan access flow
- [ ] GDPR: account deletion endpoint
- [ ] GDPR: data export endpoint
- [ ] GDPR: consent recording at signup

### Phase I: Stage 8 — Pre-Launch Hardening

- [ ] Security audit checklist pass
- [ ] Dependency scan (pip-audit)
- [ ] Environment validation at startup
- [ ] Logging hygiene (no internal data leakage)
- [ ] Global error handler
- [ ] Sentry integration
- [ ] UptimeRobot monitoring
- [ ] Browser hardening content QA review
- [ ] End-to-end test: full audit flow from email input to export

---

## See Also

- [[MVP Master]] — stage status
- [[pre-stage-06-signal-registry-handoff]] — detailed synthesis process
- [[../../Research/launch-research-dashboard|Launch Research Dashboard]] — provider research tracking
- [[../../Research/Signal Research Guide|Signal Research Guide]] — signal design methodology
- [[../../Research/Extending the Platform|Extending the Platform]] — implementation patterns
- [[../../Research/provider-research-protocol|Provider Research Protocol]] — per-provider research format
