---
title: "prompt / tools / lynis"
aliases: ["lynis", "lynis prompt", "lynis research prompt"]
tags: [zima, research, prompts, provider-research, tools, lynis, graph_exclude]
type: provider_research_prompt
provider: lynis
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
| source       | string              | The module that emits the signal, not the raw provider command or check ID |
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

- Provider name: lynis
- Provider category: tools
- Provider website / API docs URL: https://cisofy.com/lynis
- Documentation / repo URL: https://github.com/CISOfy/lynis
- Target module(s) from my provider map: `os_security`, `software_vulnerability`, `patch_status`
- Build priority / tier: 2 / Plus
- Provider role: local_tool_or_deferred
- Tool type: local_cli
- Primary device use case: security audit and compliance scanning
- OS support: linux, macos, bsd
- Important provider-specific cautions:
  - Text-first output and audit-style checks may be harder to normalize.
  - Better for point-in-time audits than continuous lightweight posture collection.
  - Scope this research to local CLI usage relevant to host security auditing, patch/update visibility, and any software-vulnerability-adjacent checks actually supported by official docs.
  - Distinguish audit recommendations, suggestions, and score changes from directly evidenced findings.
  - Do not assume that every warning, suggestion, or hardening recommendation should become a standalone signal.
  - Treat compliance/audit framing separately from concrete host-state evidence.

---

## Research Instructions

Use official provider documentation, official CLI references, official repository docs, official report-format documentation, and provider-maintained documentation as primary sources. Use third-party sources only to fill gaps, and label them clearly.

For every important claim about CLI artifacts, report formats, scoring/findings model, check IDs, parseable fields, exit behavior, or normalization-safe outputs, cite the source. Clearly label whether each trigger is:
- documented
- derived from documented fields
- inferred from examples only
- unclear

Research at the module boundary: for each target module, decide whether the provider contributes a direct signal, only enrichment, only utility output, or is out of scope.

Because this provider is a local audit CLI, explicitly document:
- invocation surface relevant to Zima
- local execution and privilege requirements
- output artifacts and formats
- what can be parsed safely and stably
- what is recommendation text only vs concrete evidence
- how point-in-time audit results should be interpreted for ongoing signal generation

Identify all relevant commands, modes, report artifacts, and output files for this provider and classify each as:
- direct_signal_input
- enrichment_only
- utility_only
- out_of_scope

Important: stay scoped to Lynis only. Do not generalize from adjacent hardening or compliance tools unless the official docs explicitly compare behavior.

Important for this research pass:
- Document CLI artifacts, report formats, scoring/findings model, and what can be parsed safely.
- Distinguish audit recommendations from direct evidence fields.
- Treat provider-native scores, warnings, and suggestions as inputs to analysis, not automatic Zima severities.
- Focus on implementation-grade mapper/rules implications, not generic hardening advice.

---

## Tasks

Apply the full workflow in [[../../../provider-research-protocol|Provider Research Protocol]].

### 1) Tool/API Surface Appendix
Document the Lynis surface relevant to `os_security`, `software_vulnerability`, and `patch_status`.

At minimum, investigate and document:

**Relevant CLI commands / artifacts**
- primary audit commands relevant to local system auditing
- report file(s), log file(s), data file(s), or machine-readable output artifacts
- test/check identifiers and categories, if exposed
- hardening index / score outputs
- warnings, suggestions, notices, or other finding classes
- profile/customization options only if they materially affect output interpretation
- exit codes or status behavior, if documented
- update/version-check behavior, if relevant to operational use

**For each relevant command, mode, or artifact, document:**
- command / mode / artifact name
- purpose
- supported entity_type(s)
- execution requirements / privileges
- supported OS behavior (linux / macos / bsd)
- output fields and types
- which fields are always present vs optional vs version-specific
- whether the mode/artifact produces direct host-state evidence, recommendations only, mixed output, or utility data only
- whether the artifact is stable enough for parser-driven normalization

**Document result variants for:**
- successful audit with concrete findings
- successful audit with only recommendations / no actionable findings
- successful audit with score only / minimal output
- partial or limited result (missing privileges, unsupported platform sections, skipped tests)
- common error cases (permission issues, unsupported OS area, missing dependencies, incomplete logs, parse ambiguity)

**Document schema/details important to implementation, including where applicable:**
- top-level report metadata
- host/target identification fields
- check/test identifiers
- categories/groups
- warnings / suggestions / findings structure
- score / hardening index fields
- plugin or test result codes
- package/update-related fields
- kernel/system configuration evidence fields
- service/network/configuration evidence fields
- timestamps, version, profile, and environment metadata
- fields that are useful only for evidence vs fields usable for signal triggers
- free-text recommendation fields that should not be treated as direct evidence without corroboration

### 2) Module Mapping Appendix
For each target module, document:
- module name
- provider command(s), mode(s), or artifacts used
- classification: direct_signal_input / enrichment_only / utility_only / out_of_scope
- why the module should or should not consume it
- important gating logic before signal creation
- source module name to use in emitted signals

Pay specific attention to:
- `os_security`: likely host hardening and misconfiguration evidence, if concrete enough
- `patch_status`: only if Lynis exposes actionable package/update/patch evidence rather than generic recommendations
- `software_vulnerability`: only if official docs support vulnerability-relevant evidence; otherwise classify as enrichment-only or out_of_scope

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
- exact trigger_condition using actual CLI/report field names where possible
- evidence_fields to persist
- enrichment_fields worth storing but not promoting into separate signals
- summary_template
- evidence_status: documented / derived / inferred / unclear

Important:
- Do not turn generic hardening suggestions into standalone signals unless there is a concrete, parseable state/evidence field behind them.
- Distinguish recommendation text from direct evidence.
- If Lynis produces both concrete evidence and free-text remediation guidance in the same artifact, separate them clearly.
- If the provider should not emit standalone signals for a given output type or target module, say so explicitly and leave it out of the signal table.

### 4) Severity Rules
For each signal row:
- assign severity
- explain why using my calibration guide
- identify conditional severity logic if applicable

Important:
- Lynis scores, warnings, and suggestion levels are not automatically Zima severities.
- Only elevate severity when the underlying finding semantics justify it under my calibration guide.
- Explain whether Zima should map Lynis finding classes directly, partially, or only as one input among others.
- Be conservative where the output is audit guidance rather than proof of exploitable or risky state.

### 5) Confidence Guidance
Do not output final production confidence values. For each signal type or module use-case, provide:
- source_reliability notes
- freshness / staleness considerations
- corroboration opportunities
- suggested calibration TODOs

Important:
- direct local checks may have high source reliability for point-in-time host state
- recommendation-style outputs have lower evidentiary quality unless tied to concrete fields
- point-in-time audit data may become stale quickly for continuously changing host posture
- include corroboration opportunities such as package manager inspection, system config inspection, osquery, or other host telemetry

### 6) Tags
For each signal type, suggest 2-5 applicable tags from:
breach, stealer_log, plaintext_password, exposed_secret, pii_exposure, phishing, malware, c2, botnet, spam, proxy, tor, vpn, data_broker, dark_web, credential_stuffing, open_port, misconfiguration, threat_actor, ransomware, typosquat, lookalike, dmarc_fail, spf_fail

If none fit well for Lynis-derived signals, say so explicitly rather than forcing weak tags. `misconfiguration` will likely be the strongest fit when applicable.

### 7) Implementation Notes
Capture mapper/rules concerns that would matter during build-out:
- field paths that must survive parsing
- null / empty / no-hit behavior
- report/log parsing safety and version drift risks
- text-first output normalization constraints
- deduplication keys or natural identifiers
- raw evidence worth storing for remediation or audit
- what belongs in provider client vs module mapper vs correlation layer
- privilege/runtime constraints and their effect on incomplete audits
- whether this tool is suitable for scheduled collection, ad hoc audits, or deferred/manual execution only

Additionally for Lynis:
- define which Lynis commands/artifacts Zima should support first
- identify the most stable machine-readable artifacts, if any
- document the canonical raw output schema Zima should preserve before normalization
- identify the minimum fields required to produce a stable `os_security` or `patch_status` signal
- identify which Lynis outputs should remain enrichment-only because they are recommendation text rather than evidence
- document how to handle repeated findings across repeated audits
- explain when Lynis should be treated as a primary finding source vs a corroborating audit tool
- explicitly separate direct evidence, recommendations, score outputs, and compliance-style observations

---

## Required Output

### A. Tool/API Surface Appendix
Provide a structured appendix of relevant Lynis commands, report/log/data artifacts, scoring/findings behavior, and parseability considerations for the target modules.

### B. Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|

### C. Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Where:
- severity_is_conditional = yes / no
- conditional_rule = plain-English logic
- trigger_condition = actual CLI/report field-based logic
- evidence_status = documented / derived / inferred / unclear
- finding_kind = `true_finding` or `contextual_enrichment`

If there are no standalone signals for a module or output type, return an empty portion of the signal table for that scope and explain why.

### D. Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|

### E. Provider Summary
1. strongest signal types (or strongest utility contributions)
2. what the provider should not be used for
3. local execution, privilege, parsing, or output-stability cautions
4. whether this provider should be treated as signal-producing, enrichment-only, utility-only, deferred, or mixed depending on artifact and module

### F. Structured JSON
```json
{
  "provider": "lynis",
  "provider_category": "tools",
  "provider_role": "local_tool_or_deferred",
  "module_mappings": [],
  "signal_contracts": [],
  "confidence_guidance": []
}
