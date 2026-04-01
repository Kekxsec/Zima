---
title: "prompt / tools / malicious_extension_sentry"
aliases: ["malicious_extension_sentry", "malicious_extension_sentry prompt", "malicious_extension_sentry research prompt"]
tags: [zima, research, prompts, provider-research, tools, malicious_extension_sentry, graph_exclude]
type: provider_research_prompt
provider: malicious_extension_sentry
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

**Provider:** malicious_extension_sentry
**Category:** tools
**URL:** Zima-internal component or https://github.com/AcidMadrid/malicious-extensions-list (investigate actual source)
**Tool type:** local_matcher
**Browser support:** Chromium family primarily

**Target modules:** `extension_risk`

**Provider role:** direct_signal_input — matches installed extensions against known-malicious database

**Build priority:** P0 / Core

**Cautions:**
Known-bad detection only — does not assess unknown extensions. Effectiveness depends entirely on the quality and freshness of the malicious extension database. Must validate: list source, update cadence, false negative rate, how IDs are matched.

**First-pass severity:**
- Known malware extension installed = critical
- Known data-harvesting extension = high
- Known adware extension = medium

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

### 1) Tool Surface & Provider Research
Document the following about this provider:

**Malicious extension database:**
- What is the source database? Investigate https://github.com/AcidMadrid/malicious-extensions-list and any other sources.
- What format is the database in? (JSON, CSV, plain text list of IDs)
- How large is the database? (number of entries)
- How often is it updated? (commit frequency, last update date)
- Who maintains it? (individual, organization, community)
- What is the data provenance? (where do the entries come from — CWS takedowns, security research, user reports)

**Matching mechanism:**
- How does matching work? (extension ID exact match? regex? CRX hash? name match?)
- Is matching case-sensitive?
- What identifier format is used? (Chrome Web Store 32-char alphanumeric ID)
- Does it support Firefox add-on IDs or only Chrome extension IDs?
- Does it support Edge add-on IDs? (same as Chrome for Chromium-based Edge)

**Match output:**
- What metadata is returned per match? (threat type, severity, description, source URL, date added)
- Are there categories of malicious extensions? (malware, spyware, adware, coin miners, data harvesting, phishing, etc.)
- Does the database include severity or risk ratings per entry?
- Is there a description or reference URL per entry?

**Coverage and limitations:**
- What types of malicious extensions are covered?
- What is the estimated false negative rate? (extensions that are malicious but not in the database)
- Does it only cover extensions removed from CWS, or also side-loaded threats?
- How does it handle extensions that were malicious but have been updated to be benign?
- Version-aware matching? Or just by extension ID regardless of version?

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

Additionally:
- Database update strategy: how should Zima keep the malicious extension list current? (git pull on schedule, embedded snapshot, API fetch)
- Matching performance: for N installed extensions against M database entries, what is the lookup complexity? Should the database be loaded into a set/dict for O(1) lookups?
- Extension ID as deduplication key: the natural dedup key is (extension_id, browser_profile). Document how to construct this.
- False negative awareness: since this is known-bad only, the module should clearly communicate that a clean result does NOT mean the extension is safe. Document how the module should frame "no match" results.
- Integration with browser_extension_detector: this provider likely depends on another provider to enumerate installed extensions. Document the expected input format (list of extension IDs) and the upstream dependency.
- Severity mapping from database categories: if the database provides threat categories, document the mapping from database category to Zima severity.

---

## Required Output

### A. Tool Surface Appendix
Provide a structured per-command, per-artifact, or per-interface appendix.

### B. Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|

### C. Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Where:
- severity_is_conditional = yes / no
- conditional_rule = plain-English logic
- trigger_condition = actual field-based logic
- evidence_status = documented / derived / inferred / unclear
- finding_kind = `true_finding` or `contextual_enrichment`

If there are no standalone signals for this provider, return an empty signal table and explain why.

### D. Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|

### E. Provider Summary
1. strongest signal types (or strongest utility contributions)
2. what the provider should not be used for
3. installation / privilege / platform cautions
4. whether this provider should be treated as signal-producing, enrichment-only, utility-only, or deferred

### F. Structured JSON
After the markdown report, provide a JSON object with keys: `provider`, `provider_category`, `provider_role`, `module_mappings`, `signal_contracts`, `confidence_guidance`. Use `"unknown"` for unavailable details.
