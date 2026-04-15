---
title: "prompt / darkweb / robin"
aliases: ["robin", "robin prompt", "robin research prompt"]
tags: [zima, research, prompts, provider-research, darkweb, robin, graph_exclude]
type: provider_research_prompt
provider: robin
provider_category: darkweb
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

- Provider name: robin
- Provider category: darkweb
- Provider website / API docs URL: https://github.com/apurvsinghgautam/robin
- Target module(s) from my provider map: darkweb_identity_monitor, threat_actor_mentions
- Build priority / tier: 3 / Plus
- Provider role: local_tool_or_deferred
- Schema hints already captured in my notes:
  - likely provider method(s): search_darkweb(query), scrape_result(url), summarize_investigation(run)
  - likely provider-side category label(s): darkweb_osint, investigation
  - likely supported entity type(s): email, username, domain, company, url, keyword
  - rough provider confidence note from my research scaffold: unknown
- Important provider-specific cautions:
- This is a local dark web OSINT tool that depends on Tor and optional LLM providers.
- Distinguish search-engine results, scraped page content, and AI-generated summaries.
- Treat AI summaries as analyst assistance, not direct findings, unless backed by source evidence.
- My first-pass severity assessment:
- Likely better for enrichment and investigator workflows than direct production alerts unless its raw search and scrape outputs are structured enough to map cleanly.

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
For each target module, classify the provider output as:
- `direct_signal_input`
- `enrichment_only`
- `utility_only`
- `out_of_scope`

### 3) Signal Contract Appendix
Define only the signal contracts that are stable and implementation-worthy. If the tool is mostly analyst workflow support, say so explicitly.
