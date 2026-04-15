---
title: "Signal Registry — Canonical Implementation Reference"
tags: [zima, signals, registry, canonical, implementation]
type: canonical_signal_registry
created: 2026-03-27
updated: 2026-03-27
status: wave_1_frozen
kind: canonical
llm_include: true
code_scope: backend
---

← [[Signal Research Guide|Research Guide]] · [[Provider Module Map|Module Map]] · [[../Archive/MVP Build 2026/pre-stage-06-signal-registry-handoff|Pre-Stage-6 Handoff]]

# Signal Registry — Canonical Implementation Reference

This is the implementation-ready signal registry for Zima. It is the authoritative source for:

- `rules.py` severity decision logic in every module
- `mapper.py` SignalCreate construction
- correlation rule planning
- score calculator category weighting
- remediation playbook mapping

**Scope:** Wave 0 (anchor) + Wave 1 (core launch identity expansion) signals.

**Freeze status:** Wave 1 identity signals are frozen for implementation. Downstream domains (device, browser, domain, network) are first-pass only — not yet frozen.

---

## Confidence Policy (Provisional)

Do not block implementation on perfect confidence calibration. Use this temporary policy until real scan volume exists (target: 1,000 scans):

| Source quality | Provisional confidence |
|---|---|
| Highly authoritative, curated (HIBP, SpamHaus, Hudson Rock) | `high` (0.90–0.95) |
| Good quality, well-documented (DeHashed, LeakCheck, BreachDirectory) | `high` (0.85) |
| Moderate quality, some noise (Epieos, EmailRep) | `medium` (0.70–0.75) |
| Tool-based discovery (Holehe, Maigret, WhatsmyName) | `low` (0.55–0.65) |
| Purely contextual / enrichment (Accounts, social profiles) | not applicable — no signal row |

Add `# TODO: calibrate after first 1000 scans` to every confidence assignment in code.

---

## Severity Framework

| Severity | Meaning |
|---|---|
| `critical` | Active compromise likely or imminent — immediate action required |
| `high` | Significant risk — resolve within days |
| `medium` | Notable risk — should be addressed |
| `low` | Minor risk or hygiene issue |
| `info` | Contextual data, not a risk in isolation — no signal row |

---

## identity_security

### Module: breach_monitor

Source module: `breach_monitor`
Entity type: `email`
Providers: `hibp`, `dehashed`, `breachdirectory`

| signal_type | severity | severity_is_conditional | confidence | providers | trigger_condition |
|---|---|---|---|---|---|
| `email_breached` | `high` | yes | 0.85 | hibp, dehashed, breachdirectory | email found in breach record with no password field |
| `email_breached` | `critical` | yes | 0.90 | dehashed | email found in breach record with password hash or plaintext present |

**Conditional severity rule (frozen):**

```python
# In breach_monitor/rules.py
def severity_for_breach(finding: dict) -> Severity:
    has_password = bool(
        finding.get("password") or finding.get("hashed_password")
    )
    return Severity.CRITICAL if has_password else Severity.HIGH
```

**Evidence fields to preserve:**
- `breach_name`
- `breach_date`
- `data_classes` (list of what was exposed)
- `is_verified` (breach verification status)
- `is_sensitive`
- `password_present` (bool — computed, not raw)
- `source_provider`

**Summary template:**
- `high`: "Email found in {breach_name} breach ({breach_date})"
- `critical`: "Email found in {breach_name} breach with password data exposed"

**Notes:**
- HIBP is authoritative and highly reliable — confidence stays at 0.85 even for single breach hits
- DeHashed: charges per query — rate limit aggressively (see config.py)
- BreachDirectory: supplementary evidence only — lower data quality, confidence 0.80
- Dedup key: `(user_id, "email_breached", entity_id)` — one signal per breach source per email. Use `evidence.breach_name` + `evidence.source_provider` to distinguish within the signal.
- Merge multiple breach hits into a single signal with `tags` and `details` — avoid per-breach signal spam

---

### Module: credential_exposure

Source module: `credential_exposure`
Entity type: `email`
Providers: `dehashed`, `leakcheck`, `breachdirectory`

| signal_type | severity | severity_is_conditional | confidence | providers | trigger_condition |
|---|---|---|---|---|---|
| `password_exposed` | `critical` | yes | 0.90 | dehashed, leakcheck | plaintext password present in breach record |
| `password_exposed` | `high` | yes | 0.85 | dehashed, leakcheck, breachdirectory | password hash present (no plaintext) |

**Conditional severity rule (frozen):**

```python
# In credential_exposure/rules.py
def severity_for_credential(finding: dict) -> Severity:
    has_plaintext = bool(finding.get("password"))
    has_hash = bool(finding.get("hashed_password") or finding.get("password_hash"))
    if has_plaintext:
        return Severity.CRITICAL
    if has_hash:
        return Severity.HIGH
    return Severity.HIGH  # fallback if module called without password check — shouldn't happen
```

**Evidence fields to preserve:**
- `breach_name`
- `breach_date`
- `password_present` (bool — always True for this signal)
- `has_plaintext` (bool)
- `has_hash` (bool)
- `hash_type` (if detectable: md5, sha1, bcrypt, etc.)
- `source_provider`

**Summary template:**
- `critical`: "Plaintext password exposed in {breach_name} breach"
- `high`: "Password hash exposed in {breach_name} breach"

**Notes:**
- `password_exposed` is a distinct signal from `email_breached` — even if the same breach generates both, they represent different risks and require different remediation
- Never log or persist the actual password value — only presence flags
- BreachDirectory: confirm password field presence from their API before mapping this signal

---

### Module: stealer_log_exposure

Source module: `stealer_log_exposure`
Entity type: `email`
Providers: `hudson_rock`

| signal_type | severity | severity_is_conditional | confidence | providers | trigger_condition |
|---|---|---|---|---|---|
| `stealer_log_hit` | `critical` | no | 0.90 | hudson_rock | email or username found in stealer log database |

**Evidence fields to preserve:**
- `stealer_family` (malware family name if available)
- `date_compromised` (date the infection likely occurred)
- `computer_name`
- `operating_system`
- `antiviruses` (AV products present — context for why stealer succeeded)
- `credentials_count` (number of credentials exfiltrated from that device)
- `top_passwords` (MUST NOT be stored — only count)
- `source_provider`

**Summary template:**
- "Device infected with {stealer_family} — credentials exfiltrated and found in stealer log"

**Notes:**
- Stealer logs indicate active device compromise, not just credential exposure — remediation is device wipe + full credential rotation, not just password change
- Hudson Rock is considered authoritative for this signal type (confidence 0.90 frozen)
- `top_passwords` field: log count only, never values — this is a hard rule, not a suggestion
- STRIPPED from hudson_rock/client.py confirmed severity=CRITICAL for this provider (was hardcoded in findings dict — violation of Rule 2, but confirms intended severity)

---

### Module: username_exposure

Source module: `username_exposure`
Entity type: `email` / `username`
Providers: `maigret`, `epieos`, `emailrep`

| signal_type | severity | severity_is_conditional | confidence | providers | trigger_condition |
|---|---|---|---|---|---|
| `username_exposure` | `medium` | yes | 0.70 | epieos | username/alias discovered and linked to email via OSINT |
| `username_exposure` | `low` | yes | 0.60 | maigret | username found registered on external platform |

**Conditional severity rule (frozen):**

```python
# In username_exposure/rules.py
def severity_for_username(finding: dict) -> Severity:
    # Epieos: confirmed account association — medium
    if finding.get("source_provider") == "epieos":
        return Severity.MEDIUM
    # Tool-based discovery: lower confidence — low
    return Severity.LOW
```

**Evidence fields to preserve:**
- `username`
- `platform`
- `profile_url`
- `source_provider`
- `confirmed` (bool — whether the account association was verified)

**Summary template:**
- `medium`: "Username '{username}' linked to this email on {platform}"
- `low`: "Username '{username}' found registered on {platform}"

**Notes:**
- STRIPPED from maigret/client.py: `severity=FindingSeverity.LOW` — confirmed
- STRIPPED from epieos/client.py: `severity=FindingSeverity.MEDIUM` for account found — confirmed
- emailrep: INFO-level enrichment for this signal — no signal row needed; feeds context into `account_enumeration_risk` module
- Username exposure on its own is low-medium risk; escalates to high via correlation with `email_breached`

---

### Module: alias_correlation

Source module: `alias_correlation`
Entity type: `email`
Providers: `epieos`

| signal_type | severity | severity_is_conditional | confidence | providers | trigger_condition |
|---|---|---|---|---|---|
| `alias_exposure_detected` | `low` | no | 0.70 | epieos | secondary email or alias linked to this email discovered |

**Evidence fields to preserve:**
- `alias_email`
- `platform`
- `source_provider`

**Summary template:**
- "Alias email '{alias_email}' discovered and linked to this identity"

**Notes:**
- STRIPPED from epieos/client.py: `severity=FindingSeverity.LOW` for secondary email/alias — confirmed
- Alias exposure is informational in isolation; becomes high risk when combined with `email_breached` on the alias address
- Correlation rule needed: `alias_exposure_detected` + `email_breached` (on alias) → escalate finding severity

---

### Module: account_inventory

Source module: `account_inventory`
Entity type: `email`
Providers: `holehe`, `whatsmyname`

| signal_type | severity | severity_is_conditional | confidence | providers | trigger_condition |
|---|---|---|---|---|---|
| `account_discovered` | `low` | no | 0.60 | holehe, whatsmyname | email or username found registered on external service |

**Evidence fields to preserve:**
- `platform`
- `profile_url`
- `registration_confirmed` (bool)
- `source_provider`

**Summary template:**
- "Account found registered on {platform}"

**Notes:**
- STRIPPED from holehe/client.py: `severity=FindingSeverity.LOW` — confirmed
- accounts/client.py: `severity=FindingSeverity.INFO` — pure inventory, no risk signal unless combined
- `account_discovered` is LOW severity by itself — the value is in building the account graph for correlation
- holehe/maigret both use blocking `subprocess.run()` — this MUST be replaced with `asyncio.create_subprocess_exec()` before production use

---

### Module: account_enumeration_risk

Source module: `account_enumeration_risk`
Entity type: `email`
Providers: `emailrep`, `holehe`

| signal_type | severity | severity_is_conditional | confidence | providers | trigger_condition |
|---|---|---|---|---|---|
| `account_enumeration_risk` | `medium` | yes | 0.70 | emailrep | email reputation indicates high exposure / spam / suspicious history |

**Conditional severity rule (frozen):**

```python
# In account_enumeration_risk/rules.py
def severity_for_emailrep(finding: dict) -> Severity:
    suspicious = finding.get("suspicious", False)
    spam = finding.get("spam", False)
    blacklisted = finding.get("blacklisted", False)
    if blacklisted or suspicious:
        return Severity.MEDIUM
    if spam:
        return Severity.LOW
    return None  # no signal if no risk indicators
```

**Evidence fields to preserve:**
- `reputation_score`
- `suspicious` (bool)
- `spam` (bool)
- `blacklisted` (bool)
- `references` (number of external references)
- `profiles` (list of known platforms)
- `source_provider`

**Summary template:**
- `medium`: "Email reputation flagged as suspicious or blacklisted"

**Notes:**
- EmailRep returns INFO-level data when reputation is clean — no signal emitted in that case
- STRIPPED from emailrep was not directly observed, but architecture analysis confirms MEDIUM is appropriate for suspicious/blacklisted flags

---

## Conditional Severity Providers — Frozen Rules

These five providers require explicit conditional logic. Rules are frozen before implementation.

### breachdirectory

```python
# Maps to breach_monitor (email_breached) and credential_exposure (password_exposed)
def severity_breachdirectory(finding: dict) -> Severity:
    has_password = bool(finding.get("password") or finding.get("sha1"))
    return Severity.CRITICAL if has_password else Severity.HIGH
```

### greynoise / greynoise_community

```python
# Maps to network/ip_reputation signals (not Wave 1)
def severity_greynoise(finding: dict) -> Severity:
    classification = finding.get("classification", "")
    return Severity.HIGH if classification in {"malicious", "attack"} else Severity.MEDIUM
```

### virustotal

```python
# Maps to threat_intel signals (not Wave 1)
# Conditional: HIGH if malicious >= 3 else MEDIUM
def severity_virustotal(finding: dict) -> Severity:
    malicious = finding.get("malicious", 0)
    return Severity.HIGH if malicious >= 3 else Severity.MEDIUM
```

### threatjammer

```python
# Maps to network/ip_reputation signals (not Wave 1)
def severity_threatjammer(finding: dict) -> Severity:
    score = finding.get("score", 0)
    return Severity.HIGH if isinstance(score, (int, float)) and score >= 70 else Severity.MEDIUM
```

### honeypot

```python
# Maps to network/ip_reputation signals (not Wave 1)
def severity_honeypot(finding: dict) -> Severity:
    threat_level = finding.get("threat_score", 0)
    return Severity.HIGH if threat_level >= 40 else Severity.MEDIUM
```

---

## Signals by Wave — Implementation Queue

### Wave 0 (built — HIBP anchor)

| signal_type | module | status |
|---|---|---|
| `email_breached` | `breach_monitor` | implemented |

### Wave 1 — Identity Expansion (build order)

| # | signal_type | module | providers | status |
|---|---|---|---|---|
| 1 | `email_breached` | `breach_monitor` | + dehashed, breachdirectory | extend existing |
| 2 | `password_exposed` | `credential_exposure` | dehashed, leakcheck, breachdirectory | new module |
| 3 | `stealer_log_hit` | `stealer_log_exposure` | hudson_rock | new module |
| 4 | `username_exposure` | `username_exposure` | maigret, epieos | new module |
| 5 | `alias_exposure_detected` | `alias_correlation` | epieos | new module |
| 6 | `account_discovered` | `account_inventory` | holehe, whatsmyname | new module |
| 7 | `account_enumeration_risk` | `account_enumeration_risk` | emailrep | new module |

### Wave 2+ (first-pass research only — not frozen)

Domain | signal_type examples | tier
---|---|---
`device_security` | `os_outdated`, `disk_encryption_disabled`, `firewall_disabled`, `screen_lock_not_configured` | Core
`browser_security` | `risky_extension_detected`, `extension_excessive_permissions` | Core
`domain_security` | `missing_dmarc`, `missing_spf`, `expired_certificate` | Pro
`network_security` | `exposed_rdp`, `exposed_ssh`, `weak_wifi_encryption` | Plus
`reputation` | `ip_blocklist_hit`, `ip_flagged_threat_intel` | Plus

---

## Correlation Rules Required After Wave 1

These correlation rules need to be added to `backend/app/correlation/rules/` after Wave 1 modules are built:

| rule | signals required | output finding |
|---|---|---|
| identity_compromise_escalation | `email_breached` + `password_exposed` | `high_identity_compromise_risk` |
| stealer_plus_breach | `stealer_log_hit` + `email_breached` | `high_identity_compromise_risk` (critical) |
| alias_chain_breach | `alias_exposure_detected` + `email_breached` (on alias) | escalate severity |
| username_reuse_pattern | `username_exposure` × 3+ platforms | `username_reuse_detected` |

---

## Score Calculator Impact — Wave 1

All Wave 1 signals map to `identity_security` category. The existing `identity_score.py` calculator handles this category.

**Deduction weights to confirm before implementation:**

| signal_type | severity | expected deduction |
|---|---|---|
| `stealer_log_hit` | critical | large (−25 to −30) |
| `password_exposed` (plaintext) | critical | large (−25 to −30) |
| `password_exposed` (hash) | high | medium (−15 to −20) |
| `email_breached` (with password) | critical | medium-large (−20) |
| `email_breached` (no password) | high | medium (−10 to −15) |
| `username_exposure` | medium | small (−5) |
| `account_discovered` | low | minimal (−2) |
| `alias_exposure_detected` | low | minimal (−2) |
| `account_enumeration_risk` | medium | small (−5) |

---

## Remediation Playbooks Required — Wave 1

Add to `backend/app/remediation/engine.py` → `SIGNAL_TO_PLAYBOOK`:

| signal_type | playbook key | action summary |
|---|---|---|
| `password_exposed` | `rotate_exposed_password` | Rotate password on affected service immediately; use unique password; enable MFA |
| `stealer_log_hit` | `device_compromise_response` | Assume device compromised; full credential rotation; consider device wipe |
| `username_exposure` | `review_account_footprint` | Review accounts on discovered platforms; close dormant accounts |
| `alias_exposure_detected` | `review_alias_accounts` | Review alias email; check if alias appears in breaches |
| `account_discovered` | `review_account_footprint` | Review and secure discovered accounts |
| `account_enumeration_risk` | `review_email_exposure` | Investigate email reputation flags; check for spam/abuse |

---

## Naming Review Log

Reviewed for duplicates and antipatterns on 2026-03-27:

- `email_breached` vs `breach_detected` — chose `email_breached` (entity-first naming)
- `password_exposed` vs `credential_exposed` — chose `password_exposed` (specific to password field)
- `stealer_log_hit` vs `stealer_log_detected` — chose `stealer_log_hit` (industry term)
- `account_discovered` vs `account_found` — chose `account_discovered` (cleaner, consistent with domain language)
- `username_exposure` vs `username_found` — chose `username_exposure` (consistent with `alias_exposure_detected`)
- `alias_exposure_detected` vs `alias_found` — chose `alias_exposure_detected` (explicit about risk framing)
- `account_enumeration_risk` — retained as-is (module name matches signal name — acceptable)

---

## See Also

- [[Signal Research Guide]] — methodology for designing signals
- [[Provider Module Map]] — provider to module ownership
- [[../Archive/MVP Build 2026/pre-stage-06-signal-registry-handoff|Pre-Stage-6 Handoff]] — exit criteria for Stage 6 readiness
- [[../Architecture/section-08-signal-model|§8 Signal Model]] — Signal data structure
- [[../Architecture/section-20-domain-breakdown|§20 Domain Breakdown]] — all module domains
