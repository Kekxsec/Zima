---
title: "prompt / tools / osquery"
aliases: ["osquery", "osquery prompt", "osquery research prompt"]
tags: [zima, research, prompts, provider-research, tools, osquery, graph_exclude]
type: provider_research_prompt
provider: osquery
provider_category: tools
obsidianUIMode: preview
kind: artifact
status: not_started
llm_include: false
code_scope: backend
---
Research > Zima Research > provider workspace
## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

Primary goal:
- determine how this provider should be used by each target module
- identify which provider outputs create standalone signals, which are enrichment-only, and which are utility-only
- define field-level trigger logic, severity rules, evidence fields, and mapper notes that can be carried directly into `modules/*/rules.py` and `modules/*/mapper.py`

My platform's normalized signal schema includes:

| Field        | Type                | Notes |
|--------------|---------------------|-------|
| signal_type  | string (snake_case) | Internal name, e.g. `credential_breach_found` |
| category     | string              | Use the best-fit Zima category/domain for the module. Common examples: `identity_security`, `account_security`, `network_security`, `domain_security`, `threat_intel`, `dark_web`, `privacy`, `cloud_security`, `secrets`, `saas`. Do not force a worse category just to match this example list. |
| severity     | string              | critical / high / medium / low / info |
| confidence   | string              | Final `high` / `medium` / `low` is calibrated later from real data. In this research pass, provide confidence guidance, not a guessed production value. |
| entity_type  | string              | Examples: email / domain / ip / hostname / username / phone / hash / url / account / company / repository / cloud_resource |
| source       | string              | The module that emits the signal, not the raw provider endpoint name |
| summary      | string              | One-sentence signal summary template |
| evidence     | object              | Raw provider fields worth storing for audit, remediation, and deduplication |
| tags         | list[string]        | Domain and finding tags, e.g. `["breach", "stealer_log", "plaintext_password"]` |

Severity calibration guide (do not deviate without strong justification):
- critical: direct credential exposure, plaintext passwords, active stealer logs, live malware C2
- high: confirmed breach, exposed PII, verified malicious infrastructure, active threat actor attribution
- medium: suspicious activity, unverified breach, reputation degradation, passive threat indicators
- low: informational findings with mild risk, historical data with low recency confidence
- info: pure enrichment/context with no standalone risk (e.g. WHOIS data, ASN lookup)

Important interpretation rules:
- Research at the module boundary. A provider endpoint is not a finished signal until a target module decides it is.
- One provider may feed multiple modules; keep module decisions separate.
- Distinguish four classes of provider output: `direct_signal_input`, `enrichment_only`, `utility_only`, and `out_of_scope`.
- Base severity on my platform's calibration guide, not the provider's own score/label unless the provider field directly evidences one of my severity definitions.
- Do not assign final production confidence based on AI judgment alone. Instead provide source-reliability notes, freshness considerations, corroboration opportunities, and calibration TODOs.
- Distinguish between true findings and enrichment-only/context fields.
- Do not invent field names, enum values, response shapes, or trigger conditions. If unclear, mark as unknown or inferred.
- Prefer stable, implementation-worthy signal types. Do not create unnecessary vendor-specific variants if they map to the same internal concept.

---

## Provider Under Research

- Provider name: osquery
- Provider category: tools
- Provider website / API docs URL: https://osquery.io — docs at https://osquery.readthedocs.io/en/stable/
- Target module(s) from my provider map: `os_security`, `patch_status`, `software_vulnerability`, `extension_risk`, `browser_configuration`
- Build priority / tier: P0 / Core
- Provider role: utility_only or direct_signal_input — must be determined per table
- Tool type: endpoint_agent (local SQL-based query interface)
- OS support: macOS, Windows, Linux
- Schema hints already captured in my notes:
  - likely provider method(s): SQL queries against osquery virtual tables
  - likely provider-side category label(s): host_inventory, device_posture
  - likely supported entity type(s): device (host-level)
  - rough provider confidence note from my research scaffold: high for factual inventory — reads directly from OS
- Important provider-specific cautions:
  - osquery is an inventory/posture COLLECTOR, not a vulnerability scanner. It reports facts. Whether those facts constitute a risk signal is the module's decision.
  - Requires local installation, may need elevated privileges for some tables.
  - Some tables are OS-specific. Document platform availability for every table investigated.
  - Chromium extension tables (`chrome_extensions`) have stronger coverage than Firefox (`firefox_addons`). Document the gap.
  - osquery does not assign severity, risk scores, or security verdicts. All severity comes from Zima module logic.
  - Some outputs are `utility_only` (e.g. software inventory feeding trivy/grype), some are `direct_signal_input` (e.g. `disk_encryption` table producing a `disk_encryption_disabled` signal).
- My first-pass severity assessment:
  - Disk encryption disabled: high
  - Firewall disabled: high
  - OS significantly out of date: high
  - OS mildly out of date: medium
  - Software inventory: info (utility for vuln scanning)
  - Browser extension inventory: info (utility for extension risk module)

---

## Research Instructions

Use official provider documentation, official API references, official OpenAPI specs, official example responses, and provider-maintained SDK/docs as primary sources. Use third-party sources only to fill gaps, and label them clearly.

For every important claim about schema, trigger logic, enums, authentication, or limits, cite the source. Clearly label whether each trigger is:
- documented
- derived from documented fields
- inferred from examples only
- unclear

Research at the module boundary: for each target module, decide whether the provider contributes a direct signal, only enrichment, only utility output, or is out of scope.

If the provider is a local tool, utility parser, or alerting service, say that explicitly and do not invent standalone signals just to fill the table.

Identify all relevant endpoints, methods, or output artifacts for this provider and classify each as:
- direct_signal_input
- enrichment_only
- utility_only
- out_of_scope

Important: stay scoped to this provider only. Do not generalize from adjacent providers unless the docs explicitly share the same backend/schema.

---

## Tasks

### 1) Tool/API Surface Appendix
Investigate and document the following osquery virtual tables, grouped by target module:

**For os_security module:**
- `os_version` — OS name, version, build, platform
- `disk_encryption` (cross-platform) / `bitlocker_info` (Windows) / `filevault2_status` (macOS) — encryption status per volume
- `alf` (macOS Application Layer Firewall) / `iptables_rules` (Linux) / `windows_firewall_rules` — firewall state and rules
- `system_info` — hardware UUID, hostname, CPU, RAM
- `screenlock` — screen lock timeout/enabled state
- `sip_config` (macOS) — System Integrity Protection status
- `gatekeeper` (macOS) — Gatekeeper enabled/disabled
- `secureboot` (Windows/Linux) — Secure Boot state

**For patch_status module:**
- `os_version` — current OS version for staleness comparison
- `windows_updates` / `windows_optional_features` — installed/pending updates on Windows
- `apt_sources` / `deb_packages` (Debian/Ubuntu) — package versions
- `homebrew_packages` (macOS) — installed Homebrew package versions

**For software_vulnerability module:**
- `programs` (Windows) / `apps` (macOS) / `deb_packages` / `rpm_packages` / `homebrew_packages` — installed software inventory
- Note: osquery does NOT do CVE matching. This output feeds trivy/grype for vulnerability scanning.

**For extension_risk module:**
- `chrome_extensions` — Chrome/Chromium extension inventory with ID, name, version, permissions, path, enabled state
- `firefox_addons` — Firefox add-on inventory (document field coverage differences vs Chrome)
- `safari_extensions` (macOS) — Safari extension inventory

**For browser_configuration module:**
- `chrome_extension_content_scripts` — content script URLs per extension
- Any browser preference/policy tables if they exist

For each relevant table, document:
- table name
- purpose
- supported entity_type(s)
- auth or execution requirements (root/admin needed?)
- platform availability (macOS / Windows / Linux)
- top-level response fields and types
- nested objects/arrays and their fields
- which fields are always present vs optional vs conditional vs platform-specific
- enum values/status values where documented
- response variants for:
  - successful hit
  - successful no-hit
  - partial/limited result
  - common error cases
- important example response excerpts, if available
- citation_refs

### 2) Module Mapping Appendix
For each target module, document:
- module name
- provider method(s), endpoint(s), or artifacts used
- classification: direct_signal_input / enrichment_only / utility_only / out_of_scope
- why the module should or should not consume it
- important gating logic before signal creation
- source module name to use in emitted signals

### 3) Signal Contract Table
Only create rows for standalone signals that should actually be emitted by a module.

For each signal row, provide:
- module
- source
- provider
- provider_method
- snake_case signal_type
- category
- entity_type
- finding_kind: true_finding / contextual_enrichment
- exact trigger_condition using actual API field names
- evidence_fields to persist
- enrichment_fields worth storing but not promoting into separate signals
- summary_template
- evidence_status: documented / derived / inferred / unclear

If the provider should not emit standalone signals for a target module, say so explicitly and leave it out of the signal table.

### 4) Severity Rules
For each signal row:
- assign severity
- explain why using my calibration guide
- identify conditional severity logic if applicable
- assess whether my first-pass assessment is correct

### 5) Confidence Guidance
Do not output final production confidence values. For each signal type or module use-case, provide:
- source_reliability notes
- freshness / staleness considerations
- corroboration opportunities
- suggested calibration TODOs

### 6) Tags
For each signal type, suggest 2-5 applicable tags from:
breach, stealer_log, plaintext_password, exposed_secret, pii_exposure, phishing, malware, c2, botnet, spam, proxy, tor, vpn, data_broker, dark_web, credential_stuffing, open_port, misconfiguration, threat_actor, ransomware, typosquat, lookalike, dmarc_fail, spf_fail

### 7) Implementation Notes
Capture mapper/rules concerns that would matter during build-out:
- field paths that must survive parsing
- null / empty / no-hit behavior
- rate limits, billing, licensing, or premium-tier constraints
- deduplication keys or natural identifiers
- raw evidence worth storing for remediation or audit
- what belongs in provider client vs module mapper vs correlation layer

Additionally for osquery:
- Document which tables require root/admin privileges vs unprivileged access
- Document cross-platform gaps (tables that exist on one OS but not another)
- Document invocation modes: `osqueryi` (interactive) vs `osqueryd` (daemon) vs `--json` flag for machine-readable output
- Clarify whether Zima should use daemon mode or on-demand one-shot queries for a periodic audit use case
- Document the `--json` output format so the provider client knows what to parse

---

## Required Output

### A. Tool/API Surface Appendix
Provide a structured per-table appendix first, grouped by target module.

### B. Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|

### C. Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Where:
- severity_is_conditional = yes / no
- conditional_rule = plain-English logic
- trigger_condition = actual API/tool field-based logic
- evidence_status = documented / derived / inferred / unclear
- finding_kind = `true_finding` or `contextual_enrichment`

If there are no standalone signals for this provider, return an empty signal table and explain why.

### D. Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|

### E. Provider Summary
1. strongest signal types (or strongest utility contributions)
2. what the provider should not be used for
3. API/auth/rate-limit/licensing or privilege cautions
4. whether this provider should be treated as signal-producing, enrichment-only, utility-only, or deferred

### F. Structured JSON
```json
{
  "provider": "osquery",
  "provider_category": "tools",
  "provider_role": "unknown — to be determined",
  "module_mappings": [],
  "signal_contracts": [],
  "confidence_guidance": []
}
```

If any required detail is unavailable, use `"unknown"` rather than guessing.
