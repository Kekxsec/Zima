---
title: "prompt / tools / trivy"
aliases: ["trivy", "trivy prompt", "trivy research prompt"]
tags: [zima, research, prompts, provider-research, tools, trivy, graph_exclude]
type: provider_research_prompt
provider: trivy
provider_category: tools
obsidianUIMode: preview
kind: artifact
status: not_started
llm_include: false
code_scope: backend
---
## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic tool summary.

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
- Research at the module boundary. A provider output is not a finished signal until a target module decides it is.
- One provider may feed multiple modules; keep module decisions separate.
- Distinguish four classes of provider output: `direct_signal_input`, `enrichment_only`, `utility_only`, and `out_of_scope`.
- Base severity on my platform's calibration guide, not the provider's own score/label unless the provider field directly evidences one of my severity definitions.
- Do not assign final production confidence based on AI judgment alone. Instead provide source-reliability notes, freshness considerations, corroboration opportunities, and calibration TODOs.
- Distinguish between true findings and enrichment-only/context fields.
- Do not invent field names, enum values, response shapes, or trigger conditions. If unclear, mark as unknown or inferred.
- Prefer stable, implementation-worthy signal types. Do not create unnecessary vendor-specific variants if they map to the same internal concept.

---

## Provider Under Research

- Provider name: trivy
- Provider category: tools
- Provider website / API docs URL: https://trivy.dev
- Documentation / repo URL: https://github.com/aquasecurity/trivy
- Target module(s) from my provider map: `software_vulnerability`
- Build priority / tier: 3 / Pro
- Provider role: local_tool_or_deferred
- Tool type: vulnerability_scanner
- Primary device use case: local filesystem and package CVE scanning
- OS support: linux, macos, windows
- Important provider-specific cautions:
  - Requires vulnerability DB sync or periodic offline update strategy.
  - Better as enrichment on top of inventory data than as the sole device collector.
  - Scope this research to local filesystem, package, and host-adjacent scan modes relevant to endpoint/software vulnerability detection.
  - Separate raw vulnerability findings from package inventory, metadata, and posture/context fields.
  - Do not treat every Trivy scanner family as automatically in scope; explicitly classify each relevant mode as direct signal input, enrichment-only, utility-only, or out of scope for `software_vulnerability`.

---

## Research Instructions

Use official provider documentation, official CLI references, official schema/output examples, official repository docs, and provider-maintained documentation as primary sources. Use third-party sources only to fill gaps, and label them clearly.

For every important claim about schema, trigger logic, scan modes, JSON fields, DB update behavior, supported ecosystems, or output semantics, cite the source. Clearly label whether each trigger is:
- documented
- derived from documented fields
- inferred from examples only
- unclear

Research at the module boundary: for each target module, decide whether the provider contributes a direct signal, only enrichment, only utility output, or is out of scope.

Because this provider is a local CLI tool, explicitly document:
- invocation surface relevant to Zima
- local execution requirements
- database update requirements
- offline / air-gapped considerations
- JSON output structure and field stability
- which findings are actual vulnerability matches vs contextual package/inventory data

Identify all relevant commands, modes, scanners, and output artifacts for this provider and classify each as:
- direct_signal_input
- enrichment_only
- utility_only
- out_of_scope

Important: stay scoped to Trivy only. Do not generalize from adjacent scanners unless the official docs explicitly compare or share behavior.

Important for this research pass:
- Document filesystem/package scan modes, JSON fields, DB update model, and supported ecosystems.
- Separate raw vulnerability matches from host posture and inventory data.
- Treat provider-native severity as an input field, not an automatic Zima severity.
- Focus on implementation-grade mapper/rules implications, not marketing-level capability descriptions.

---

## Tasks

Apply the full workflow in [[../../../provider-research-protocol|Provider Research Protocol]].

### 1) Tool/API Surface Appendix
Document the Trivy surface relevant to `software_vulnerability`, especially local and host-adjacent scan paths.

At minimum, investigate and document:

**Relevant scan modes / commands**
- filesystem scanning
- root filesystem scanning, if distinct and relevant
- repository or directory scanning only if it materially overlaps with endpoint/package vulnerability use cases
- package vulnerability detection behavior
- installed-language/package ecosystem detection behavior
- JSON output modes and schema structure
- severity filtering, ignore handling, and scanner selection flags if relevant to downstream signal creation
- DB update / cache commands and offline update workflow

**For each relevant command or mode, document:**
- command / mode name
- purpose
- supported entity_type(s)
- execution requirements / privileges
- supported OS behavior (linux / macos / windows)
- required DBs or metadata sources
- output fields and types
- which fields are always present vs optional vs mode-specific
- whether the mode produces direct vulnerability findings, enrichment/context only, utility data, or mixed output

**Document response / result variants for:**
- successful hit (vulnerabilities found)
- successful no-hit (scan completed, no vulnerabilities)
- partial/limited result (e.g. unsupported lockfile, missing DB, partial package detection)
- common error cases (DB missing, cache stale, unsupported target, permission failure, parser failure)

**Document JSON schema details important to implementation, including where applicable:**
- top-level metadata
- scan target identifier fields
- result grouping structure
- vulnerability arrays
- package / installed component fields
- CVE / advisory identifiers
- severity / status / fixed-version fields
- installed-version / package-name / package-type fields
- layer / path / class / type / target fields
- references, titles, descriptions, primary URLs, CVSS-related fields
- vendor vs NVD severity distinctions if present
- fields that are useful only for evidence vs useful for signal triggers

### 2) Module Mapping Appendix
For each target module, document:
- module name
- provider command(s), mode(s), or artifacts used
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
- exact trigger_condition using actual tool JSON field names
- evidence_fields to persist
- enrichment_fields worth storing but not promoting into separate signals
- summary_template
- evidence_status: documented / derived / inferred / unclear

Important:
- Raw package inventory, scan metadata, and cache/update metadata should not automatically become standalone signals unless there is a strong module-boundary reason.
- If Trivy produces both vulnerability findings and inventory/context in the same result set, separate them clearly.
- If the provider should not emit standalone signals for a given output type, say so explicitly and leave it out of the signal table.

### 4) Severity Rules
For each signal row:
- assign severity
- explain why using my calibration guide
- identify conditional severity logic if applicable

Important:
- Trivy's own severity labels are not automatically Zima severities.
- Only elevate severity when the finding semantics justify it under my calibration guide.
- Explain whether Zima should map provider severity directly, partially, or only as one input among others.

### 5) Confidence Guidance
Do not output final production confidence values. For each signal type or module use-case, provide:
- source_reliability notes
- freshness / staleness considerations
- corroboration opportunities
- suggested calibration TODOs

Important:
- include DB freshness and offline-cache staleness as first-class confidence considerations
- include package detection completeness / parser coverage as a confidence consideration
- note where filesystem/package scan coverage is inherently incomplete compared to full asset inventory + SBOM-backed correlation

### 6) Tags
For each signal type, suggest 2-5 applicable tags from:
breach, stealer_log, plaintext_password, exposed_secret, pii_exposure, phishing, malware, c2, botnet, spam, proxy, tor, vpn, data_broker, dark_web, credential_stuffing, open_port, misconfiguration, threat_actor, ransomware, typosquat, lookalike, dmarc_fail, spf_fail

If none fit well for software/package vulnerabilities, say so explicitly rather than forcing weak tags.

### 7) Implementation Notes
Capture mapper/rules concerns that would matter during build-out:
- field paths that must survive parsing
- null / empty / no-hit behavior
- DB update behavior, cache location, offline update workflow, and staleness handling
- rate limits, licensing, or packaging constraints if relevant
- deduplication keys or natural identifiers
- raw evidence worth storing for remediation or audit
- what belongs in provider client vs module mapper vs correlation layer

Additionally for Trivy:
- define which Trivy commands Zima should support first for endpoint-oriented `software_vulnerability`
- document the canonical raw output schema Zima should preserve before normalization
- identify the minimum fields required to produce a stable software vulnerability signal
- identify fields that should be stored only for remediation context
- document how to handle multiple findings for the same package/CVE across repeated scans
- document how DB freshness should affect downstream confidence guidance or scan validity
- explain when Trivy should be treated as a primary finding source vs enrichment on top of existing software/package inventory
- explicitly separate vulnerability findings from package inventory and from non-vulnerability scanner families

---

## Required Output

### A. Tool/API Surface Appendix
Provide a structured appendix of relevant Trivy commands, modes, JSON structures, DB/update behavior, and supported ecosystems for the `software_vulnerability` module.

### B. Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|

### C. Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Where:
- severity_is_conditional = yes / no
- conditional_rule = plain-English logic
- trigger_condition = actual tool field-based logic
- evidence_status = documented / derived / inferred / unclear
- finding_kind = `true_finding` or `contextual_enrichment`

If there are no standalone signals for this provider, return an empty signal table and explain why.

### D. Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|

### E. Provider Summary
1. strongest signal types (or strongest utility contributions)
2. what the provider should not be used for
3. API/auth/rate-limit/licensing, local execution, DB sync, or privilege cautions
4. whether this provider should be treated as signal-producing, enrichment-only, utility-only, deferred, or mixed depending on mode

### F. Structured JSON
```json
{
  "provider": "trivy",
  "provider_category": "tools",
  "provider_role": "local_tool_or_deferred",
  "module_mappings": [],
  "signal_contracts": [],
  "confidence_guidance": []
}
