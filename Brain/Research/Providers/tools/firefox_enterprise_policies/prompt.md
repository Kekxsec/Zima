---
title: "prompt / tools / firefox_enterprise_policies"
aliases: ["firefox_enterprise_policies", "firefox enterprise policies prompt", "firefox_enterprise_policies research prompt"]
tags: [zima, research, prompts, provider-research, tools, firefox_enterprise_policies, graph_exclude]
type: provider_research_prompt
provider: firefox_enterprise_policies
provider_category: tools
obsidianUIMode: preview
kind: artifact
status: not_started
llm_include: false
code_scope: backend
---
Research > Zima Research > provider workspace

### Context

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
| source       | string              | The module that emits the signal, not the raw provider key or storage path |
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
- Base severity on my platform's calibration guide, not the provider's own label unless the provider field directly evidences one of my severity definitions.
- Do not assign final production confidence based on AI judgment alone. Instead provide source-reliability notes, freshness considerations, corroboration opportunities, and calibration TODOs.
- Distinguish between true findings and enrichment-only/context fields.
- Do not invent field names, enum values, response shapes, or trigger conditions. If unclear, mark as unknown or inferred.
- Prefer stable, implementation-worthy signal types. Do not create unnecessary vendor-specific variants if they map to the same internal concept.

---

## Provider Under Research

- Provider name: firefox_enterprise_policies
- Provider category: tools
- Provider website / API docs URL: Mozilla policy templates
- Documentation / repo URL: Firefox Policy List
- Target module(s) from my provider map: `browser_configuration`
- Build priority / tier: 2 / Plus
- Provider role: local_tool_or_deferred
- Tool type: browser_policy_source
- Primary browser use case: inspect enforced Firefox browser policies for tracking, cookies, updates, and extension controls
- Browser support: firefox
- Important provider-specific cautions:
  - Policy files may not exist on unmanaged endpoints.
  - File locations and registry use vary by OS.
  - Scope this research to local policy discovery and parsing relevant to browser configuration evidence on managed devices.
  - Distinguish configured policy presence from effective browser behavior where precedence, policy support, or platform differences may apply.
  - Focus on direct policy evidence that can be read locally, not general admin guidance or deployment recommendations.
  - Do not assume every documented policy is implemented identically across all Firefox versions or operating systems.
  - Prefer evidence from authoritative local policy stores over explanatory admin text when deciding implementation logic.

---

## Research Instructions

Use official Mozilla documentation, official Firefox policy templates, official Firefox enterprise/admin documentation, official policy lists, and provider-maintained documentation as primary sources. Use third-party sources only to fill gaps, and label them clearly.

For every important claim about policy locations, key names, supported OS storage, value types, precedence, scope, or parseable artifacts, cite the source. Clearly label whether each trigger is:
- documented
- derived from documented fields
- inferred from examples only
- unclear

Research at the module boundary: for each target module, decide whether the provider contributes a direct signal, only enrichment, only utility output, or is out of scope.

Because this provider is a local policy evidence source, explicitly document:
- where policies live on each supported OS
- how policy namespaces/paths differ by OS and policy mechanism
- which policy keys are stable and parseable enough for normalization
- which policy keys produce direct configuration evidence vs only contextual/admin metadata
- how to distinguish mandatory/enforced policy from default or unmanaged state where supported
- how to handle policy absence, partial policy presence, and OS/version-specific unsupported keys

Identify all relevant storage artifacts, namespaces, policy families, and output artifacts for this provider and classify each as:
- direct_signal_input
- enrichment_only
- utility_only
- out_of_scope

Important: stay scoped to Firefox enterprise/browser policy sources only. Do not generalize from Chromium or other browser policy systems unless the docs explicitly compare behavior.

Important for this research pass:
- Document where policies live on each OS, which keys matter, and which settings map cleanly into Zima signals.
- Focus on direct configuration evidence, not general policy documentation.
- Treat browser policy values as input evidence, not automatic Zima severity.
- Prefer actual stored/effective policy artifacts over explanatory documentation when deciding implementation logic.

---

## Tasks

Apply the full workflow in [[../../../provider-research-protocol|Provider Research Protocol]].

### 1) Tool/API Surface Appendix
Document the Firefox enterprise policy surface relevant to `browser_configuration`.

At minimum, investigate and document:

**Relevant policy storage / discovery artifacts**
- Windows registry locations for Firefox policy stores, where documented
- macOS plist / managed preferences locations and namespaces, where documented
- Linux policy file locations and formats, where documented
- Firefox-specific policy namespaces, policy file names, and path differences
- any official browser-internal inspection surfaces that are useful for validation only if documented and relevant
- policy precedence and scope, if documented (machine vs user, mandatory vs recommended/default behavior, etc.)

**Relevant policy families / key groups**
- extension control policies
- extension installation allow/block/force-install controls, where supported
- extension restrictions, install source restrictions, or related controls, where supported
- cookies / site data / third-party cookie controls
- privacy / tracking protection / telemetry / browsing data controls, where officially documented for Firefox policies
- update, safe browsing, password-manager, and privacy-adjacent settings only if they map cleanly to `browser_configuration`
- any policy families that are tempting but should remain out of scope for this module

**For each relevant artifact, key family, or policy source, document:**
- artifact / key family name
- purpose
- supported entity_type(s)
- execution requirements / privileges
- supported OS behavior (Windows / macOS / Linux)
- supported browser behavior (Firefox only, including any ESR considerations if documented)
- data format and field/value types
- which fields are always present vs optional vs version-specific
- whether the artifact produces direct configuration evidence, mixed evidence, enrichment/context only, or utility data only
- whether the artifact is stable enough for parser-driven normalization

**Document result variants for:**
- policies present and parseable
- no policies present
- partial policy presence
- browser installed but policy source absent
- policy source present but values unsupported by current browser version
- common error cases (permission denied, malformed policy file, registry read failure, plist parse failure, namespace mismatch)

**Document schema/details important to implementation, including where applicable:**
- browser/vendor identifier
- OS-specific storage path / registry path / plist domain / file path
- policy key name
- policy value type
- effective scope (machine vs user, if documented)
- enforced vs unmanaged/default distinction, if documented
- list/dict/scalar value shapes
- extension IDs, install URLs, domains, allow/block lists, cookie settings, tracking/privacy flags
- fields that are useful only for evidence vs fields usable for signal triggers
- free-text policy descriptions that should not be treated as data fields

### 2) Module Mapping Appendix
For each target module, document:
- module name
- provider artifact(s), policy source(s), or key families used
- classification: direct_signal_input / enrichment_only / utility_only / out_of_scope
- why the module should or should not consume it
- important gating logic before signal creation
- source module name to use in emitted signals

For this provider, pay special attention to:
- `browser_configuration`: primary target module
- direct configuration evidence around enforced extension, cookie, tracking, telemetry, and privacy-related policies
- which policy keys should remain enrichment-only because they are too generic, low-risk, or too Firefox-version-specific for clean normalization

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
- exact trigger_condition using actual policy key names and value logic
- evidence_fields to persist
- enrichment_fields worth storing but not promoting into separate signals
- summary_template
- evidence_status: documented / derived / inferred / unclear

Important:
- Do not turn all enterprise policy presence into standalone signals.
- Only create signals where a policy state meaningfully represents a risky, restrictive, or security-relevant browser configuration condition.
- Distinguish absence of policy from insecure policy unless the official docs support a clear interpretation.
- If a policy family provides both direct evidence and supporting metadata, separate them clearly.
- If the provider should not emit standalone signals for a given policy family, say so explicitly and leave it out of the signal table.

### 4) Severity Rules
For each signal row:
- assign severity
- explain why using my calibration guide
- identify conditional severity logic if applicable

Important:
- Most Firefox enterprise policy findings will likely be `low` or `info`, unless a policy directly weakens browser security or privacy in a materially meaningful way.
- Policy existence alone is not automatically risky.
- Conservative severity assignment is preferred for configuration evidence.
- Explain whether Zima should map specific risky configurations directly, partially, or only after additional corroboration.

### 5) Confidence Guidance
Do not output final production confidence values. For each signal type or module use-case, provide:
- source_reliability notes
- freshness / staleness considerations
- corroboration opportunities
- suggested calibration TODOs

Important:
- locally read enforced policies may have high source reliability when parsed directly from authoritative OS/browser policy stores
- effective-behavior confidence may be lower than configured-policy confidence when browser support, precedence, or version applicability is ambiguous
- absence of policy is weaker evidence than presence of explicit policy
- corroboration may include Firefox internal policy inspection, extension inventory, browser settings inspection, or endpoint telemetry

### 6) Tags
For each signal type, suggest 2-5 applicable tags from:
breach, stealer_log, plaintext_password, exposed_secret, pii_exposure, phishing, malware, c2, botnet, spam, proxy, tor, vpn, data_broker, dark_web, credential_stuffing, open_port, misconfiguration, threat_actor, ransomware, typosquat, lookalike, dmarc_fail, spf_fail

If none fit well for a policy-derived signal, say so explicitly rather than forcing weak tags. `misconfiguration` will likely be the strongest fit when applicable.

### 7) Implementation Notes
Capture mapper/rules concerns that would matter during build-out:
- field paths that must survive parsing
- null / empty / no-hit behavior
- OS-specific storage differences
- policy precedence / enforced-vs-default interpretation issues
- parse safety for registry / plist / policy file artifacts
- deduplication keys or natural identifiers
- raw evidence worth storing for remediation or audit
- what belongs in provider client vs module mapper vs correlation layer
- how to normalize the same policy concept across supported Firefox policy mechanisms

Additionally for `firefox_enterprise_policies`:
- define which Firefox channels Zima should support first, if version/channel differences matter
- define the canonical raw output schema Zima should preserve before normalization
- identify the minimum fields required to produce a stable `browser_configuration` signal
- identify which policy keys map cleanly into normalized signals vs which should remain enrichment-only
- document how to handle policy absence vs explicit disable/enable states
- document how to handle list-valued and object-valued policies such as blocklists, allowlists, install controls, and site-specific policy structures
- explain when this provider should be treated as a primary evidence source vs a corroborating configuration source
- explicitly separate direct policy evidence, browser support metadata, and admin guidance text

---

## Required Output

### A. Tool/API Surface Appendix
Provide a structured appendix of relevant Firefox policy storage locations, namespaces, key families, value types, and parseability considerations for the target module.

### B. Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|

### C. Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Where:
- severity_is_conditional = yes / no
- conditional_rule = plain-English logic
- trigger_condition = actual policy-key-based logic
- evidence_status = documented / derived / inferred / unclear
- finding_kind = `true_finding` or `contextual_enrichment`

If there are no standalone signals for a policy family, OS, or Firefox scope, return an empty portion of the signal table for that scope and explain why.

### D. Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|

### E. Provider Summary
1. strongest signal types (or strongest utility contributions)
2. what the provider should not be used for
3. local execution, privilege, storage, version, or OS-support cautions
4. whether this provider should be treated as signal-producing, enrichment-only, utility-only, deferred, or mixed depending on artifact and policy family

### F. Structured JSON
```json
{
  "provider": "firefox_enterprise_policies",
  "provider_category": "tools",
  "provider_role": "local_tool_or_deferred",
  "module_mappings": [],
  "signal_contracts": [],
  "confidence_guidance": []
}
```

If this prompt is used outside Obsidian, include the contents of `Research/provider-research-protocol.md` alongside this prompt before running the research task.
