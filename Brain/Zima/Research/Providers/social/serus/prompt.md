---
title: "prompt / social / serus"
aliases: ["serus", "serus prompt", "serus research prompt"]
tags: [zima, research, prompts, provider-research, social, serus, graph_exclude]
type: provider_research_prompt
provider: serus
provider_category: social
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

- Provider name: serus
- Provider category: social
- Provider website / API docs URL: https://www.serus.ai/ — check https://www.serus.ai/blog and any /api, /docs, /developers paths; also check https://app.serus.ai for any API key or developer portal
- Target module(s) from my provider map: `data_broker_exposure`, `public_profile_scan`, `darkweb_identity_monitor`
- Build priority / tier: P1 / Core-Plus boundary
- Provider role: unknown — must be determined; likely `signal_producer` if a usable API exists, otherwise `deferred`
- Schema hints already captured in my notes:
  - likely provider method(s): unknown — search for scan/lookup/monitor endpoints
  - likely provider-side category label(s): dark web exposure, surface web exposure, data broker exposure
  - likely supported entity type(s): email, name, phone, domain
  - rough provider confidence note from my research scaffold: unknown
- Important provider-specific cautions:
  - **API existence is unconfirmed.** Public search results show no developer API documentation as of early 2026. This is the most critical research question: does Serus expose a REST API, webhook, or any programmatic interface? If not, classify as `deferred` regardless of data quality.
  - Serus.ai (Stockholm, privacy platform) is a different company from serus.io (document processing). Research only serus.ai.
  - The platform is relatively new (domain registered ~2025). API stability, documentation quality, and long-term availability are unknown risks that must be explicitly assessed.
  - Serus focuses on three distinct exposure types — dark web, surface web, and data broker. These likely warrant separate module classifications because they carry different severities and remediation paths. Do not collapse them into a single signal.
  - The platform also detects fake accounts, AI-generated impersonations, and deepfakes. Research whether these outputs are accessible via API and whether they are relevant to Zima's current module set.
  - If Serus offers a monitoring/webhook model (alerts when new exposure is found) rather than a synchronous scan API, that changes the integration pattern. Document this explicitly.
- My first-pass severity assessment:
  - Dark web credential exposure: critical / high (aligns with existing `darkweb_identity_monitor` severity guidance)
  - Data broker exposure (PII indexed by people-search sites): medium / low depending on sensitivity of exposed fields
  - Surface web exposure (public profiles, unauthorized content): medium / low / info depending on finding type
  - Fake account / deepfake detection: medium (novel risk, not yet mapped to a Zima module — flag as out of scope for current build if no existing module fits)

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

**Critical first step:** Before researching signals and schema, confirm whether Serus exposes a developer-accessible API at all. If no API exists, return a short finding that documents the integration gap and end the research there. Do not proceed to signal design for a provider with no programmatic access.

---

## Tasks

### 1) API Surface Appendix

First, determine API availability:
- Does Serus expose a REST API, GraphQL API, or webhook system?
- Is there a developer portal, API key issuance, or documentation site?
- Are there any SDK packages (PyPI, npm, etc.)?
- Is there a partner or enterprise tier that unlocks API access?
- What pricing model gates API access?

If an API exists, for each relevant endpoint, method, or output artifact document:
- endpoint name/path
- purpose
- supported entity_type(s) — email, name, phone, domain, or other
- auth or execution requirements
- top-level response fields and types
- nested objects/arrays and their fields
- which fields are always present vs optional vs conditional vs premium-only
- enum values/status values where documented
- response variants for:
  - successful hit (exposure found)
  - successful no-hit (no exposure)
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

Target modules to evaluate:
- `data_broker_exposure` (privacy domain) — for surface web / people-search exposure findings
- `public_profile_scan` (privacy domain) — for publicly indexed personal profiles and social presence
- `darkweb_identity_monitor` (darkweb domain) — for dark web credential or PII exposure findings

Also assess whether any Serus outputs are relevant to:
- `identity_widely_exposed` (identity domain) — broad cross-surface exposure score
- Any new module that Serus might warrant if its fake account / AI impersonation detection is accessible via API

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

Consider the following distinctions for Serus specifically:
- dark web exposure with credentials present vs. PII-only exposure vs. mere mention
- data broker exposure: differentiate by field sensitivity (SSN/DOB/address vs. name/email only)
- surface web exposure: differentiate by risk relevance (fake impersonation account vs. public profile indexed normally)

### 5) Confidence Guidance

Do not output final production confidence values. For each signal type or module use-case, provide:
- source_reliability notes — how trustworthy is Serus's detection relative to established providers like HIBP or HudsonRock?
- freshness / staleness considerations — does Serus monitor continuously, batch-scan, or provide point-in-time results?
- corroboration opportunities — which other Zima providers could confirm or elevate a Serus finding?
- suggested calibration TODOs

### 6) Tags

For each signal type, suggest 2–5 applicable tags from:
breach, stealer_log, plaintext_password, exposed_secret, pii_exposure, phishing, malware, c2, botnet, spam, proxy, tor, vpn, data_broker, dark_web, credential_stuffing, open_port, misconfiguration, threat_actor, ransomware, typosquat, lookalike, dmarc_fail, spf_fail

### 7) Implementation Notes

Capture mapper/rules concerns that would matter during build-out:
- field paths that must survive parsing
- null / empty / no-hit behavior
- rate limits, billing, licensing, or subscription constraints
- deduplication keys or natural identifiers
- raw evidence worth storing for remediation or audit
- what belongs in provider client vs module mapper vs correlation layer
- whether a monitoring/webhook model requires a different architectural pattern than a synchronous scan

---

## Required Output

### A. API Surface Appendix

Begin with an explicit answer to: **does Serus expose a usable developer API?**

If yes, provide a structured per-endpoint appendix.
If no, document what integration paths do or do not exist and recommend a classification of `deferred`.

### B. Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|

### C. Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Where:
- severity_is_conditional = yes / no
- conditional_rule = plain-English logic
- trigger_condition = actual API field-based logic
- evidence_status = documented / derived / inferred / unclear
- finding_kind = `true_finding` or `contextual_enrichment`

If there are no standalone signals for this provider, return an empty signal table and explain why.

### D. Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|

### E. Provider Summary

1. strongest signal types (or reason for deferral)
2. what the provider should not be used for
3. API/auth/rate-limit/licensing or subscription cautions
4. whether this provider should be treated as signal-producing, enrichment-only, utility-only, or deferred at the current Zima stage
5. recommended wave placement: confirm P1 or suggest adjustment based on API maturity

### F. Structured JSON

```json
{
  "provider": "serus",
  "provider_category": "social",
  "provider_role": "unknown — to be determined",
  "module_mappings": [],
  "signal_contracts": [],
  "confidence_guidance": []
}
```

If any required detail is unavailable, use `"unknown"` rather than guessing.
