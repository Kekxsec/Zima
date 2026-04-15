---
title: "prompt / cloud / chrome_web_store_api"
aliases: ["chrome_web_store_api", "chrome_web_store_api prompt", "chrome_web_store_api research prompt"]
tags: [zima, research, prompts, provider-research, cloud, chrome_web_store_api, graph_exclude]
type: provider_research_prompt
provider: chrome_web_store_api
provider_category: cloud
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
| entity_type  | string              | Examples: email / domain / ip / hostname / username / phone / hash / url / account / company / repository / cloud_resource / browser_extension / browser_profile / device |
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
- Base severity on my platform’s calibration guide, not the provider’s own score/label unless the provider field directly evidences one of my severity definitions.
- Do not assign final production confidence based on AI judgment alone. Instead provide source-reliability notes, freshness considerations, corroboration opportunities, and calibration TODOs.
- Distinguish between true findings and enrichment-only/context fields.
- Do not invent field names, enum values, response shapes, or trigger conditions. If unclear, mark as unknown or inferred.
- Prefer stable, implementation-worthy signal types. Do not create unnecessary vendor-specific variants if they map to the same internal concept.

---

## Provider Under Research

- Provider name: chrome_web_store_api
- Provider category: cloud
- Provider website / API docs URL: Chrome Web Store / related API surface
- Documentation / repo URL: chrome-webstore-api package or equivalent maintained source
- Target module(s) from my provider map: extension_risk, browser_inventory
- Build priority / tier: 2 / Plus
- Provider role: enrichment_only
- Tool type: extension_metadata_source
- Primary browser use case: remote lookup of Chrome extension metadata for inventory enrichment
- Browser support: chrome
- Important provider-specific cautions:
  - Validate whether this is official, semi-official, unofficial, or package-mediated access to Chrome Web Store metadata.
  - Metadata enrichment is not the same as local extension detection.
  - Be explicit about dependency risk if the access path relies on scraping, reverse-engineered endpoints, or non-contractual package behavior.
  - Confirm whether extension permissions, category, publisher/developer data, ratings, install counts, and update metadata are reliably available or only partially exposed.
  - If documentation is thin or unofficial, clearly separate documented facts from inferred package behavior.
- Provider-specific research focus:
  - Determine whether this provider can produce any standalone module-level signals at all, or whether it should remain strictly enrichment-only.
  - Determine whether it meaningfully supports `extension_risk`, `browser_inventory`, or both.
  - Determine whether any returned metadata is strong enough to drive module gating logic, but do not force signals if the provider is only contextual.

---

## Research Instructions

Use official provider documentation, official API references, official example responses, official OpenAPI specs, official Chrome Web Store documentation, and provider-maintained SDK/docs as primary sources. Use third-party sources only to fill gaps, and label them clearly.

For every important claim about schema, trigger logic, enums, authentication, limits, package behavior, or endpoint stability, cite the source. Clearly label whether each trigger or field is:
- documented
- derived from documented fields
- inferred from examples only
- unclear

Research at the module boundary: for each target module, decide whether the provider contributes a direct signal, only enrichment, only utility output, or is out of scope.

Important provider-specific research requirements:
- determine whether the API path is official, semi-official, unofficial, or package-mediated
- document required credentials, metadata fields, output schema, rate limits, and whether extension permissions, category, publisher, ratings, install counts, and related metadata are reliably available
- be explicit about where this helps Zima and where it introduces dependency, maintenance, or breakage risk
- distinguish clearly between:
  - local extension presence or detection
  - remotely retrievable store metadata
  - inferred risk posture based on store metadata alone
- do not invent standalone extension-risk signals unless the available metadata and module logic justify them

Identify all relevant endpoints, methods, package calls, scraping paths, or output artifacts for this provider and classify each as:
- direct_signal_input
- enrichment_only
- utility_only
- out_of_scope

Important: stay scoped to this provider only. Do not generalize from adjacent browser-extension intelligence providers unless the docs explicitly share the same backend/schema.

If the provider is effectively a wrapper around undocumented or unstable access paths, say that explicitly and capture the implementation risk.

---

## Tasks

Apply the full workflow in [[../../../provider-research-protocol|Provider Research Protocol]].

### 1) API Surface Appendix
For each relevant endpoint, package method, scraping path, or output artifact, document:
- endpoint name/path, package method name, or artifact name
- purpose
- supported entity_type(s)
- auth requirements
- top-level response fields and types
- nested objects/arrays and their fields
- which fields are always present vs optional vs conditional
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
- provider method(s), endpoint(s), package calls, or artifacts used
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
- exact trigger_condition using actual field names
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

Important provider-specific constraint:
- metadata-only extension lookups should normally trend toward `info` unless there is strong documented evidence that a returned field maps to a real Zima risk condition
- do not overstate severity based on popularity metrics, ratings, or publisher fields alone

### 5) Confidence Guidance
Do not output final production confidence values unless they are already fixed by authoritative project docs. Instead, for each signal type or module use-case, provide:
- source_reliability notes
- freshness / staleness considerations
- corroboration opportunities
- suggested calibration TODOs

### 6) Tags
For each signal type, suggest 2-5 applicable tags from:
breach, stealer_log, plaintext_password, exposed_secret, pii_exposure, phishing, malware, c2, botnet, spam, proxy, tor, vpn, data_broker, dark_web, credential_stuffing, open_port, misconfiguration, threat_actor, ransomware, typosquat, lookalike, dmarc_fail, spf_fail

If no standalone signals are justified, omit signal tags and state that the provider is enrichment-only.

### 7) Implementation Notes
Capture mapper/rules concerns that would matter during build-out:
- field paths that must survive parsing
- null / empty / no-hit behavior
- rate limits, billing, licensing, or premium-tier constraints
- deduplication keys or natural identifiers
- raw evidence worth storing for remediation or audit
- what belongs in provider client vs module mapper vs correlation layer
- package-wrapper or scraping fragility risks
- fallback behavior if metadata lookups fail or become unavailable

---

## Required Output

### A. API Surface Appendix
Provide a structured per-endpoint, per-method, per-package-call, or per-artifact appendix first.

### B. Module Mapping Table
Return a markdown table first:

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|

### C. Signal Contract Table
Return a markdown table with one row per module-level signal contract:

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Where:
- severity_is_conditional = yes / no
- conditional_rule = plain-English logic
- trigger_condition = actual field-based logic
- evidence_status = documented / derived / inferred / unclear
- finding_kind = `true_finding` or `contextual_enrichment`
- evidence_fields = raw provider fields worth preserving in signal evidence
- enrichment_fields = fields worth storing alongside the signal but that should not themselves create a new signal
- summary_template = short human-readable sentence template for the mapper to emit
- citation_refs = source URLs or doc references that justify the row
- notes = freshness limits, coverage gaps, quirks, rate limits, paid-tier differences, reliability caveats

If there are no standalone signals for this provider, return an empty signal table and explain why in the module mapping table and summary.

### D. Confidence Guidance
Return a short markdown table:

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|

### E. Provider Summary
After the table, add:
1. strongest usable enrichment fields
2. strongest signal types, if any
3. what the provider should not be used for
4. API/auth/rate-limit/licensing/package-stability implementation cautions
5. whether this provider should be treated as signal-producing, enrichment-only, utility-only, or deferred in the current Zima stage

### F. Structured JSON
After the markdown report, provide a JSON object suitable for programmatic extraction with keys:
- `provider`
- `provider_category`
- `provider_role`
- `module_mappings`
- `signal_contracts`
- `confidence_guidance`

If any required detail is unavailable, use `unknown` rather than guessing.

If this prompt is used outside Obsidian, include the contents of `Research/provider-research-protocol.md` alongside this prompt before running the research task.
