---
title: "prompt / tools / browser_extension_detector"
aliases: ["browser_extension_detector", "browser extension detector prompt", "browser_extension_detector research prompt"]
tags: [zima, research, prompts, provider-research, tools, browser_extension_detector, graph_exclude]
type: provider_research_prompt
provider: browser_extension_detector
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

- Provider name: browser_extension_detector
- Provider category: tools
- Provider website / API docs URL: This is a Zima-internal component, not an external tool. Research should focus on what techniques exist for detecting installed browser extensions programmatically.
- Target module(s) from my provider map: `extension_risk`
- Build priority / tier: P0 / Core
- Provider role: utility_only — extension discovery feeds the extension_risk module
- Tool type: local_collector
- Browser support: Chrome, Edge, Firefox, Brave, Safari (investigate what's feasible per-platform)
- Schema hints already captured in my notes:
  - likely provider method(s): filesystem enumeration of browser profile directories
  - likely provider-side category label(s): extension_inventory
  - likely supported entity type(s): device (host-level collection)
  - rough provider confidence note from my research scaffold: high for factual inventory — reads directly from filesystem
- Important provider-specific cautions:
  - This is an internal Zima component that enumerates installed extensions from browser profile directories on the local filesystem.
  - Extension storage paths differ by browser and OS. Document all known paths.
  - Must handle multiple browser profiles per user.
  - Output is a raw extension inventory (extension ID, name, version, path, manifest data). Risk classification happens downstream in the extension_risk module.
  - This provider does NOT assess risk — it only discovers what's installed.
  - Safari extensions work differently (App Extensions via macOS). Document the gap.
  - Also consider overlap with osquery's `chrome_extensions`, `firefox_addons`, and `safari_extensions` tables. This component exists as a fallback or alternative when osquery is not installed.
- My first-pass severity assessment:
  - This provider is utility_only. It discovers extensions; it does not assess risk. No standalone signals expected.

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
This is a Zima-internal component. Instead of API endpoints, investigate and document the following:

**Browser profile directory paths per OS:**
- Chrome/Chromium profile paths on macOS, Windows, Linux
- Firefox profile paths on macOS, Windows, Linux (note: Firefox uses `profiles.ini` to locate profile directories)
- Edge profile paths on macOS, Windows, Linux
- Brave profile paths on macOS, Windows, Linux
- Safari extension paths (macOS only — App Extension model)

**Extension manifest structure:**
- Chrome/Chromium `manifest.json` structure and key fields (manifest v2 vs v3 differences)
- Firefox `manifest.json` structure (WebExtension format)
- Which fields are present in all browsers vs browser-specific
- Key fields to extract: extension ID, name, version, description, permissions, content_scripts, background scripts/service_worker, update_url, homepage_url, author, icons, enabled state

**Detection techniques:**
- Filesystem enumeration of extension directories
- How to determine if an extension is enabled vs disabled
- How to handle multiple browser profiles per user
- Whether `chrome://extensions` JSON export or direct filesystem reading is more reliable
- How to read Firefox's `extensions.json` or `addons.json` for addon state

**Output artifact:**
- Define the expected output schema for this component: a list of discovered extensions with browser, profile, extension_id, name, version, path, manifest_data, enabled_state

For each discovery method, document:
- method name
- purpose
- supported entity_type(s)
- auth or execution requirements (filesystem permissions needed)
- platform availability (macOS / Windows / Linux)
- output fields and types
- which fields are always present vs optional vs browser-specific
- response variants for:
  - successful hit (extensions found)
  - successful no-hit (no extensions / browser not installed)
  - partial/limited result (some browsers detected, others not)
  - common error cases (permission denied, locked profile)
- citation_refs (browser documentation, Chromium source, Mozilla docs)

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

Additionally for browser_extension_detector:
- Document filesystem permission requirements per OS (e.g. macOS Full Disk Access for Safari)
- Document how to handle locked browser profiles (browser currently running)
- Document the relationship to osquery's extension tables — when to prefer one over the other
- Define the canonical output schema that downstream consumers (get_browser_extension_info, extension_risk module) will expect
- Document how to detect which browsers are installed before attempting enumeration

---

## Required Output

### A. Tool/API Surface Appendix
Provide a structured per-browser, per-OS appendix of discovery paths and methods.

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
  "provider": "browser_extension_detector",
  "provider_category": "tools",
  "provider_role": "unknown — to be determined",
  "module_mappings": [],
  "signal_contracts": [],
  "confidence_guidance": []
}
```

If any required detail is unavailable, use `"unknown"` rather than guessing.
