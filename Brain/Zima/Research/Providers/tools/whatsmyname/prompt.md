---
title: "prompt / tools / whatsmyname"
aliases: ["whatsmyname", "whatsmyname prompt", "whatsmyname research prompt"]
tags: [zima, research, prompts, provider-research, tools, whatsmyname, graph_exclude]
type: provider_research_prompt
provider: whatsmyname
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

- Provider name: whatsmyname
- Provider category: tools
- Provider website / API docs URL: https://github.com/WebBreacher/WhatsMyName — also https://whatsmyname.app/
- Target module(s) from my provider map: `username_exposure`, `account_inventory`
- Build priority / tier: P1 / Core
- Provider role: utility_only or enrichment_only — username presence discovery feeds account inventory
- Tool type: local_tool (JSON site-definition dataset + checker)
- Schema hints already captured in my notes:
  - likely provider method(s): check(username) against a JSON database of site definitions
  - likely provider-side category label(s): username_enumeration, account_discovery
  - likely supported entity type(s): username
  - rough provider confidence note from my research scaffold: varies per site — some sites have reliable detection, others are ambiguous
- Important provider-specific cautions:
  - WhatsMyName is primarily a JSON dataset of site definitions (URL patterns + expected response indicators) rather than a hosted API.
  - The web app at whatsmyname.app provides a browser-based lookup, but for Zima integration the value is in the dataset and checker logic.
  - Username presence on a site does NOT prove account ownership — it proves the username is taken on that platform. Do not overstate findings.
  - False positive rate varies by site. Some sites return ambiguous responses. Document which detection methods are used (HTTP status, response body content, redirect behaviour).
  - Complements holehe (email-based account detection) and maigret (username-based, larger site list). Document how whatsmyname differs from maigret: dataset size, detection methodology, maintenance cadence, site categories.
- My first-pass severity assessment:
  - Username presence findings are info or low at best. They are account inventory enrichment, not security findings.
  - The value is in feeding the account inventory for cross-referencing with breach data, not in standalone signals.

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
Investigate and document the following aspects of WhatsMyName:

**JSON site definition dataset (`wmn-data.json`):**
- Full schema of the site definition format. Key fields per site entry:
  - `name` — site display name
  - `uri_check` — URL template with `{account}` placeholder for the username
  - `uri_pretty` — human-friendly profile URL template
  - `cat` — site category (e.g. social, gaming, tech, etc.)
  - `e_code` — expected HTTP status code when account EXISTS
  - `e_string` — expected string in response body when account EXISTS
  - `m_code` — expected HTTP status code when account is MISSING
  - `m_string` — expected string in response body when account is MISSING
  - `known` — list of known usernames for testing
  - Any additional fields (headers, cookies, POST data, etc.)
- How many sites are currently covered in the dataset
- Site categories available in the `cat` field
- How often the dataset is updated (maintenance cadence)

**Detection methods:**
- HTTP status code matching (`e_code` vs `m_code`)
- Response body content matching (`e_string` vs `m_string`)
- Redirect behaviour detection (if supported)
- How the tool handles timeouts, connection errors, and unexpected responses
- False positive mitigation strategies documented in the project

**Programmatic usage:**
- Python library usage (if available — check for `pip install whatsmyname` or similar)
- CLI usage and flags
- Raw HTTP request approach: reading `wmn-data.json` and implementing checks directly
- Output format per site check: found / not_found / error + associated metadata

**Comparison with adjacent tools:**
- How whatsmyname differs from maigret (dataset size, detection approach, output format)
- How whatsmyname differs from sherlock (similar tool, different dataset)
- Unique value proposition for Zima

For each method or artifact, document:
- method name or artifact name
- purpose
- supported entity_type(s)
- auth or execution requirements
- output fields and types
- which fields are always present vs optional
- enum values/status values where documented
- response variants for:
  - successful hit (username found on site)
  - successful no-hit (username not found on site)
  - error/ambiguous result
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

Additionally for whatsmyname:
- Document how to bundle or fetch the `wmn-data.json` dataset (vendored copy vs fetching from GitHub)
- Document rate limiting considerations when checking many sites in parallel
- Document how to handle sites that block automated requests (User-Agent requirements, CAPTCHAs)
- Define deduplication keys: (username, site_name) tuple
- Document how results feed into account_inventory for cross-referencing with breach data providers
- Clarify the licensing of the WhatsMyName dataset (CC BY-SA 4.0 or similar)

---

## Required Output

### A. Tool/API Surface Appendix
Provide a structured appendix of the dataset schema, detection methods, and programmatic usage.

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
  "provider": "whatsmyname",
  "provider_category": "tools",
  "provider_role": "unknown — to be determined",
  "module_mappings": [],
  "signal_contracts": [],
  "confidence_guidance": []
}
```

If any required detail is unavailable, use `"unknown"` rather than guessing.
