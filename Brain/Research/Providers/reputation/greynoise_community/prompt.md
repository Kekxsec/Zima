---
title: "prompt / reputation / greynoise_community"
aliases: ["greynoise_community", "greynoise_community prompt", "greynoise_community research prompt"]
tags: [zima, research, prompts, provider-research, reputation, greynoise_community, graph_exclude]
type: provider_research_prompt
provider: greynoise_community
provider_category: reputation
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
- Base severity on my platform’s calibration guide, not the provider’s own score/label unless the provider field directly evidences one of my severity definitions.
- Do not assign final production confidence based on AI judgment alone. Instead provide source-reliability notes, freshness considerations, corroboration opportunities, and calibration TODOs.
- Distinguish between true findings and enrichment-only/context fields.
- Do not invent field names, enum values, response shapes, or trigger conditions. If unclear, mark as unknown or inferred.
- Prefer stable, implementation-worthy signal types. Do not create unnecessary vendor-specific variants if they map to the same internal concept.

---

## Provider Under Research

- Provider name: greynoise_community
- Provider category: reputation
- Provider website / API docs URL: https://docs.greynoise.io/docs/using-the-greynoise-community-api
- Target module(s) from my provider map: exposed_services, domain_reputation
- Build priority / tier: 2 / Plus
- Provider role: signal_producer
- Schema hints already captured in my notes:
  - likely provider method(s): get_noise(ip_address)
  - likely provider-side category label(s): ip_reputation
  - likely supported entity type(s): ip_address
  - rough provider confidence note from my research scaffold: 0.85
- Important provider-specific cautions:
- Use official docs as primary source.
- Treat provider labels/scores as inputs, not final Zima severity.
- Separate enrichment-only fields from true findings.
- My first-pass severity assessment:
- No provider-specific stripped note captured yet in the current notes.
- Assess severity only from documented fields and your platform calibration guide.

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

### 1) API Surface Appendix
For each relevant endpoint, method, or output artifact, document:
- endpoint name/path or CLI artifact name
- purpose
- supported entity_type(s)
- auth or execution requirements
- top-level response fields and types
- nested objects/arrays and their fields
- which fields are always present vs optional vs conditional vs premium-only
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
Do not output final production confidence values unless they are already fixed by authoritative project docs. Instead, for each signal type or module use-case, provide:
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

---

## Required Output

### A. API Surface Appendix
Provide a structured per-endpoint, per-method, or per-artifact appendix first.

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
- trigger_condition = actual API field-based logic
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
1. strongest signal types
2. what the provider should not be used for
3. API/auth/rate-limit/licensing implementation cautions
4. whether this provider should be treated as signal-producing, enrichment-only, utility-only, or deferred in the current Zima stage

### F. Structured JSON
After the markdown report, provide a JSON object suitable for programmatic extraction with keys:
- `provider`
- `provider_category`
- `provider_role`
- `module_mappings`
- `signal_contracts`
- `confidence_guidance`

If any required detail is unavailable, use `unknown` rather than guessing.
