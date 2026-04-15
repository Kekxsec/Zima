---
title: "provider research protocol"
tags: [zima, research, providers, protocol, graph_exclude]
type: provider_research_protocol
created: 2026-03-22
updated: 2026-03-22
kind: canonical
status: active
llm_include: true
code_scope: backend
---

[[../Zima|Zima]] · [[research|Research]]

# Provider Research Protocol

Use this protocol whenever a provider `prompt.md` is still in a short form and needs the full implementation-grade structure.

## Core Goal

Determine how a provider or local tool should be consumed by Zima modules and whether it should produce:

- `direct_signal_input`
- `enrichment_only`
- `utility_only`
- `out_of_scope`

## Required Research Questions

For every provider:

1. What is the real API / tool surface?
2. Which module(s) should consume it?
3. Which outputs justify standalone signals?
4. Which outputs are enrichment only?
5. Which raw fields must survive into signal evidence?
6. What are the auth / licensing / rate-limit / privilege constraints?
7. What belongs in the provider client versus module mapper versus correlation layer?

## Required Tasks

### 1. API or Tool Surface Appendix

Document:

- endpoint / command / artifact name
- purpose
- supported `entity_type` inputs
- auth or execution requirements
- response or output structure
- always-present vs optional vs conditional fields
- no-hit and error variants
- important schema examples
- citation refs

### 2. Module Mapping Table

Return:

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|

### 3. Signal Contract Table

Only create rows where the provider should actually emit standalone module-level signals.

Return:

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

### 4. Confidence Guidance

Return:

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|

### 5. Provider Summary

Capture:

1. strongest signal types
2. what the provider should not be used for
3. API/auth/rate-limit/licensing or privilege cautions
4. whether the provider is signal-producing, enrichment-only, utility-only, or deferred at the current stage

### 6. Structured JSON

Return JSON with:

- `provider`
- `provider_category`
- `provider_role`
- `module_mappings`
- `signal_contracts`
- `confidence_guidance`

## Decision Rules

- prefer module-level clarity over provider-level cleverness
- do not invent standalone signals for utility collectors
- do not treat public-search hits as proof of ownership
- treat local inventory collectors as utility-only unless they directly justify a risk signal
- use official docs and maintained repos as primary sources
- if something is unclear, mark it `unknown`
