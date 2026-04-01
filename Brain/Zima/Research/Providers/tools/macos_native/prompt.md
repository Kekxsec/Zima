---
title: "prompt / tools / macos_native"
aliases: ["macos_native", "macos native prompt", "macos_native research prompt"]
tags: [zima, research, prompts, provider-research, tools, macos_native, graph_exclude]
type: provider_research_prompt
provider: macos_native
provider_category: tools
obsidianUIMode: preview
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

**Provider:** macos_native
**Category:** tools
**URL:** https://developer.apple.com — Apple CLI and system administration docs
**Tool type:** os_native_interface — built-in macOS commands
**OS support:** macOS only

**Target modules:** `os_security`, `patch_status`, `disk_encryption_check`, `firewall_status`

**Provider role:** direct_signal_input for posture checks, utility_only for inventory

**Build priority:** P0 / Core

**Cautions:**
Some commands require elevated privileges. No native vulnerability scanner. Output formats vary (plist, plain text, JSON via system_profiler -json).

**First-pass severity:**
- FileVault disabled = high
- firewall disabled = high
- SIP disabled = high
- Gatekeeper disabled = medium
- OS significantly out of date = high
- auto-updates disabled = medium

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

### 1) Tool Surface & Provider Research
Document these specific commands and their output:

- `fdesetup status` — FileVault encryption state
  - Exact output strings for enabled/disabled
  - Exit codes
  - Privilege requirements
- `defaults read /Library/Preferences/com.apple.alf globalstate` — firewall
  - Return values: 0 = off, 1 = on, 2 = block all incoming
  - Privilege requirements
- `csrutil status` — SIP (System Integrity Protection)
  - Exact output string for enabled/disabled
  - Behavior in recovery mode vs normal boot
- `spctl --status` — Gatekeeper
  - Exact output strings: "assessments enabled" / "assessments disabled"
  - Exit codes
- `system_profiler SPSoftwareDataType -json` — OS version
  - JSON schema: os_version, kernel_version, uptime, system_integrity_protection_enabled
  - Privilege requirements (none expected)
- `softwareupdate -l` — pending updates
  - Output format for available updates
  - How to distinguish security updates from feature updates
  - Timeout behavior (network dependency)
- `system_profiler SPApplicationsDataType -json` — installed apps
  - JSON schema per application entry
  - Performance considerations (can be slow)
- `defaults read /Library/Preferences/com.apple.SoftwareUpdate AutomaticCheckEnabled` — auto-update
  - Return values: 1 = enabled, 0 = disabled
  - Related keys: AutomaticDownload, CriticalUpdateInstall
- `pmset -g` — power management (screen lock related)
  - displaysleep, sleep values
  - How to determine if screen lock on wake is enabled

For each command, document:
- exact invocation
- output format and parsing strategy
- privilege requirements (user vs root)
- macOS version compatibility concerns
- error conditions and edge cases

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

Additionally:
- Document which commands need sudo and which do not. For commands that need sudo, document the fallback behavior when run without privileges.
- Output parsing strategy: for each command, specify whether parsing should be string matching, JSON parsing, plist parsing, or regex extraction.
- Handling of different macOS versions: document any commands whose output format or availability changed across macOS versions (especially Catalina 10.15+, Big Sur 11+, Monterey 12+, Ventura 13+, Sonoma 14+, Sequoia 15+).
- Document the relationship between this provider and the posture provider — macos_native provides the raw data, posture provides the abstraction layer.

---

## Required Output

### A. Tool Surface Appendix
Provide a structured per-command, per-artifact, or per-interface appendix.

### B. Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|

### C. Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Where:
- severity_is_conditional = yes / no
- conditional_rule = plain-English logic
- trigger_condition = actual field-based logic
- evidence_status = documented / derived / inferred / unclear
- finding_kind = `true_finding` or `contextual_enrichment`

If there are no standalone signals for this provider, return an empty signal table and explain why.

### D. Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|

### E. Provider Summary
1. strongest signal types (or strongest utility contributions)
2. what the provider should not be used for
3. installation / privilege / platform cautions
4. whether this provider should be treated as signal-producing, enrichment-only, utility-only, or deferred

### F. Structured JSON
After the markdown report, provide a JSON object with keys: `provider`, `provider_category`, `provider_role`, `module_mappings`, `signal_contracts`, `confidence_guidance`. Use `"unknown"` for unavailable details.
