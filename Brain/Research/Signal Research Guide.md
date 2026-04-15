---
kind: canonical
status: active
llm_include: true
code_scope: backend
tags: [zima, signals, research, methodology]
created: 2026-03-21
---

← [[../Zima|Home]] · [[Provider Schemas|← Schemas]] · [[../next-steps-to-launch|Next Steps →]]

# Signal Research Guide

How to design, document, and build the signal registry before writing any module code. The signal registry is the most valuable output of the research phase — everything else is mechanical once it's defined.

---

## What a Signal Is

A signal answers one question: **"Is something about this asset currently bad?"**

Every signal has five properties to define before writing any code:

| Property | Question it answers |
|---|---|
| `signal_type` | What happened? (unique string key) |
| `category` | Which security domain? (used by scorer) |
| `severity` | How bad is it? (`critical`/`high`/`medium`/`low`/`info`) |
| `entity_type` | What kind of asset does this attach to? |
| `source` | Which module detected it? |

**The design test:** If you can't write a one-sentence description of what the signal means and why it's bad, the signal is not well-defined yet.

---

## The Signal Registry Format

**Output target:** `signal-registry.md` — one row per (provider, signal_type) pair.

```markdown
## identity_security

| signal_type              | severity | confidence | providers                    | trigger condition                        |
|--------------------------|----------|------------|------------------------------|------------------------------------------|
| email_breached           | high     | 0.85       | hibp, dehashed, leakcheck    | email found in breach record             |
| email_breached           | critical | 0.90       | dehashed, snusbase           | password hash or plaintext present       |
| stealer_log_hit          | critical | 0.90       | hudson_rock, illicit_services| email in stealer log                     |
| credential_paste_mention | medium   | 0.70       | pastebin, psbdmp             | email or username found in paste         |
```

---

## Signal Entry Template

```
Domain          | identity
Module          | credential_exposure
Provider        | dehashed
Provider method | search_breaches(email)
Provider cat.   | credential_leak
---
Signal type     | email_breached
Signal category | identity_security
Severity rule   | high if total_records > 0 and no password field
                | critical if password_hash or plaintext_password present
Confidence rule | use provider value (0.85) unless total_records == 1 → reduce to 0.70
Entity type     | email
Inputs required | email
Notes           | DeHashed charges per query — rate limit aggressively
```

---

## Severity Framework

Use this consistently so severity is comparable across all domains.

| Severity | Meaning | Examples |
|---|---|---|
| `critical` | Active compromise likely or imminent — immediate action required | Stealer log hit, plaintext password, RDP open, root credentials in repo |
| `high` | Significant risk — resolve within days | Email in breach with password hash, vulnerable service, no MFA |
| `medium` | Notable risk — should be addressed | Email in breach (no password), blocklist hit, no DMARC |
| `low` | Minor risk or hygiene issue | Social profile publicly indexed, old breach (5+ years), low-confidence mention |
| `info` | Contextual data, not a risk in isolation | Geolocation, subdomain discovered, technology stack fingerprint |

**Decision test:** If a user sees this signal and takes no action, what's the realistic worst case? That determines severity.

---

## Example Signal Table: Network Exposure Domain

**Plain-language description first:**
> "If port 22 (SSH) is open to the internet, that's a medium signal. If it's running an outdated version with a known CVE, that's high. If RDP (3389) is open, that's critical — RDP brute force is near-guaranteed. If a database port (5432, 3306) is directly exposed, that's critical."

**Resulting signal table:**

| `signal_type` | `category` | `severity` | `entity_type` | trigger |
|---|---|---|---|---|
| `open_port_ssh` | `network_security` | `medium` | `ip` | SSH open to internet |
| `vulnerable_service_ssh` | `network_security` | `high` | `ip` | SSH with known CVE |
| `open_port_rdp` | `network_security` | `critical` | `ip` | RDP exposed |
| `exposed_database_port` | `network_security` | `critical` | `ip` | DB port (5432/3306/27017) exposed |
| `plaintext_http_exposed` | `network_security` | `medium` | `domain` | HTTP without TLS |
| `tls_cert_expired` | `network_security` | `high` | `domain` | TLS cert expired |
| `tls_cert_self_signed` | `network_security` | `medium` | `domain` | Self-signed cert |

---

## Example Signal Tables: Other Domains

### Dark Web / Identity

| `signal_type` | `category` | `severity` | trigger |
|---|---|---|---|
| `email_in_paste` | `identity_security` | `medium` | email found on paste site |
| `credentials_in_paste` | `identity_security` | `high` | email + password hash found |
| `plaintext_password_leaked` | `identity_security` | `critical` | cleartext password posted |
| `personal_data_leaked` | `identity_security` | `medium` | PII (name, address) in breach |

### DNS / Domain Hygiene

| `signal_type` | `category` | `severity` | trigger |
|---|---|---|---|
| `spf_record_missing` | `domain_security` | `medium` | no SPF TXT record |
| `dmarc_missing` | `domain_security` | `medium` | no _dmarc record |
| `dmarc_not_enforced` | `domain_security` | `low` | p=none or p=quarantine |
| `dnssec_not_configured` | `domain_security` | `low` | no DNSSEC signing |
| `domain_expiring_soon` | `domain_security` | `high` | expires in <30 days |

---

## Research Process (Phased)

### Phase 0 — Build the template first

Before researching anything, define the exact table structure (see template above). Don't start filling in cells until the schema is agreed.

### Phase 1 — Harvest STRIPPED comments first

Your providers were adapted from SpiderFoot with severity decisions stripped. Those comments are your fastest first-pass:

```bash
grep -r "STRIPPED:" backend/app/providers/ | grep -v ".pyc"
```

Example:
```python
# STRIPPED: severity = FindingSeverity.HIGH if malicious >= 3 else FindingSeverity.MEDIUM
```

That tells you exactly what the original author decided. **Harvest all of these first** — it covers ~60% of your research in one session and gives you SpiderFoot's own calibrated severity decisions to review and adjust.

### Phase 2 — Prioritise by tier

Work in build-priority order (don't research all 150 at once):

| Priority | Providers | Target tier |
|---|---|---|
| 1 | `breach/` all, `reputation/emailrep`, `social/epieos`, `accounts` | Core |
| 2 | `darkweb/` all, `reputation/` IP blocklists, `social/` public profile, `phone/` | Plus |
| 3 | `domain/` all, `ip/shodan` + `censys` + `binaryedge`, `threat_intel/` major, `social/github` | Pro |
| 4 | `cloud/`, remaining `threat_intel/`, `crypto/` | Business |

### Phase 3 — AI-assisted research per category

For well-known providers (Shodan, VirusTotal, HIBP, SecurityTrails, GreyNoise, AbuseIPDB), AI can describe API response schemas accurately. Use this prompt structure:

> "I'm building a security platform signal table. For the following provider, describe: (1) what fields the API response contains beyond what I've already extracted, (2) what security significance each field has, (3) what severity a signal from this provider should carry and why, (4) any known reliability issues. Provider: [name]. My client already extracts: [paste your client's findings dict]."

**What AI is good for here:**
- API schema lookup for well-documented providers
- Severity rule drafting (knows CVSS, OWASP conventions)
- Signal type naming consistency review

**What AI is bad for here:**
- Confidence scores — calibrate from real data, not guessed
- Novel or context-dependent severity without your domain input
- Behaviour of SpiderFoot-adapted clients vs raw APIs

### Phase 4 — Confidence calibration (not with AI)

Confidence is the one thing to set from real data, not bulk AI output.

- **Source quality:** HIBP is highly reliable (0.95+). Ahmia dark web is noisy (0.60–0.65). SpamHaus is authoritative (0.90+).
- **Corroboration:** When two independent providers agree, module confidence should be elevated.
- **Recency:** Breach data from 2015 should carry lower confidence than a fresh stealer log.
- **Practical rule:** Start with the provider's own confidence value, document it, add `# TODO: calibrate after first 1000 scans`. Don't over-engineer before you have real data.

### Phase 5 — Signal type naming review

Once you have a draft table, paste all `signal_type` values into AI and ask it to identify duplicates, inconsistencies, and naming antipatterns. You want `open_port_rdp` not `rdp_open` and `rdp_port_exposed` coexisting.

---

## The Full Pipeline for a New Signal

```
Plain-language threat description
  → Signal table (signal_type, category, severity, entity_type, providers)
  → provider/client.py — fetch, parse, return raw schema
  → modules/rules.py — severity decision logic
  → modules/mapper.py — converts to SignalCreate
  → SignalRepository.upsert() — stores/deduplicates
  → correlation/rules/ — pattern detection across signals
  → scoring/calculators/ — weighted deduction
  → remediation/engine.py — playbook mapping
```

---

## Current Status

- STRIPPED comment harvest: **complete**
- First-pass signal registry: **built**
- Remaining: complete provider research packets → synthesize canonical signal registry → freeze implementation-ready rules before Stage 6
- ~60 providers return pure INFO (no severity row needed)
- Five providers with conditional severity logic to preserve: `breachdirectory`, `greynoise`, `virustotal`, `threatjammer`, `honeypot`

---

## See Also

- [[Provider Schemas]] — what each provider actually returns
- [[Provider Module Map]] — which providers feed which modules
- [[Extending the Platform]] — how to implement each module once signals are defined
- [[../Archive/MVP Build 2026/pre-stage-06-signal-registry-handoff|Pre-Stage-6 Handoff]] — required synthesis step between research and Stage 6
- [[../Architecture/section-08-signal-model|§8 Signal Model]] — the Signal data structure
- [[../Architecture/section-20-domain-breakdown|§20 Domain Breakdown]] — all module domains
