---
title: "prompt / tools / get_browser_extension_info"
aliases: ["get_browser_extension_info", "get_browser_extension_info prompt", "get_browser_extension_info research prompt"]
tags: [zima, research, prompts, provider-research, tools, get_browser_extension_info, graph_exclude]
type: provider_research_prompt
provider: get_browser_extension_info
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

- Provider name: get_browser_extension_info
- Provider category: tools
- Provider website / API docs URL: https://github.com/nicholasgasior/browser-extension-metadata or similar — this normalises extension metadata after discovery
- Target module(s) from my provider map: `extension_risk`
- Build priority / tier: P0 / Core
- Provider role: enrichment_only — enriches extension inventory with normalised metadata
- Tool type: local_enrichment
- Browser support: Chrome, Firefox, Edge
- Schema hints already captured in my notes:
  - likely provider method(s): parse extension manifest.json, extract permissions, content scripts, update URLs
  - likely provider-side category label(s): extension_metadata
  - likely supported entity type(s): device (host-level)
  - rough provider confidence note from my research scaffold: high — parses factual manifest data
- Important provider-specific cautions:
  - This component takes raw extension data (from browser_extension_detector or osquery) and normalises it into a structured metadata format.
  - Key output: permissions list, content script URLs, background page presence, update URL, author, store listing URL.
  - The permission list is the most security-relevant output — permissions like `<all_urls>`, `tabs`, `webRequest`, `cookies`, `clipboardRead` are risk indicators.
  - This provider does NOT make risk decisions. It provides structured data that the extension_risk module uses to assess risk.
  - Sits in the pipeline between browser_extension_detector (discovery) and extension_risk module (risk assessment).
- My first-pass severity assessment:
  - This provider is enrichment_only. No standalone signals. It normalises metadata that the extension_risk module consumes to produce signals.

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
This is a Zima-internal enrichment component. Instead of API endpoints, investigate and document:

**Chrome extension manifest permission model:**
- Manifest v2 permissions model: `permissions`, `optional_permissions`
- Manifest v3 permissions model: `permissions`, `optional_permissions`, `host_permissions`
- Full list of Chrome permission strings and what each grants access to
- Which permissions are security-sensitive and why:
  - `<all_urls>` / broad host permissions — full page access
  - `tabs` — can read tab URLs and titles
  - `webRequest` / `webRequestBlocking` — can intercept/modify network requests
  - `cookies` — can read/write cookies for any permitted domain
  - `clipboardRead` / `clipboardWrite` — clipboard access
  - `nativeMessaging` — can communicate with native applications
  - `debugger` — full DevTools protocol access
  - `management` — can manage other extensions
  - `proxy` — can control proxy settings
  - `downloads` — can initiate and manage downloads
  - `history` — can read browsing history
  - `bookmarks` — can read/modify bookmarks
  - `identity` — can access user identity
  - `storage` — local/sync storage (generally benign)

**Firefox WebExtension permission model:**
- How Firefox permissions map to/differ from Chrome permissions
- Firefox-specific permissions or restrictions
- `manifest.json` differences between Chrome and Firefox

**Normalised metadata output schema:**
- Define what the normalised extension metadata object should look like after enrichment:
  - extension_id (string)
  - name (string)
  - version (string)
  - description (string)
  - author (string)
  - browser (string: chrome/firefox/edge/brave/safari)
  - manifest_version (int: 2 or 3)
  - permissions (list[string])
  - optional_permissions (list[string])
  - host_permissions (list[string]) — manifest v3
  - content_scripts (list[object]: matches, js, css, run_at)
  - background (object: scripts/service_worker, persistent)
  - update_url (string)
  - homepage_url (string)
  - store_url (string) — derived from extension_id + browser
  - enabled (bool)
  - install_path (string)

**Store URL derivation:**
- Chrome Web Store URL pattern from extension ID
- Firefox AMO URL pattern from extension ID
- Edge Add-ons URL pattern from extension ID

For each enrichment method, document:
- method name
- purpose
- supported entity_type(s)
- input requirements (what data from browser_extension_detector)
- output fields and types
- which fields are always present vs optional vs browser-specific
- citation_refs (Chrome extension docs, Mozilla WebExtension docs)

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

Additionally for get_browser_extension_info:
- Define the interface contract between browser_extension_detector (upstream) and this component
- Define the interface contract between this component and extension_risk module (downstream)
- Document which manifest fields are required vs optional across browsers
- Document how to handle extensions with missing or malformed manifest.json
- Document permission risk tiers that the extension_risk module should use (this component provides the data; the module applies the logic)

---

## Required Output

### A. Tool/API Surface Appendix
Provide a structured appendix of the permission model, manifest fields, and normalised output schema.

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
  "provider": "get_browser_extension_info",
  "provider_category": "tools",
  "provider_role": "unknown — to be determined",
  "module_mappings": [],
  "signal_contracts": [],
  "confidence_guidance": []
}
```

If any required detail is unavailable, use `"unknown"` rather than guessing.
