---
title: "prompt / breach / spycloud"
aliases: ["spycloud", "spycloud prompt", "spycloud research prompt"]
tags: [zima, research, prompts, provider-research, breach, spycloud, graph_exclude]
type: provider_research_prompt
provider: spycloud
provider_category: breach
obsidianUIMode: preview
kind: artifact
status: not_started
llm_include: false
code_scope: backend
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: spycloud
- Provider category: breach
- Provider website / API docs URL: https://spycloud.com
- Documentation / repo URL: https://docs.spycloud.com
- Target module(s) from my provider map: breach_monitor, credential_exposure, phone_exposure, username_exposure
- Build priority / tier: 3 / Pro
- Provider role: signal_producer
- Schema hints already captured in my notes:
  - provider_type: commercial_api
  - identity_use_case: breach and dark-web monitoring of credentials and identity PII
  - supported_entity_type(s): email, phone, username, ip
- Important provider-specific cautions:
  - Enterprise-focused paid API with API key access.
  - Distinguish raw breach, malware, and recaptured credential data if the docs expose them separately.

## Research Instructions

- Use official product and API docs as primary sources.
- Identify searchable entities, response schema, auth model, rate limits, and evidence fields.
- Separate direct signal input from enrichment-only and utility-only outputs.
- Do not infer unsupported signal types from marketing copy alone.

## Tasks

### 1. API Surface Appendix

- Document all relevant endpoints and response shapes.
- Capture hit, no-hit, and error variants where documented.

### 2. Module Mapping

- Map breach, credential, username, and phone-related outputs to Zima modules.
- Note what should be deduplicated or correlated across identities.

### 3. Signal Contracts

- Define implementation-worthy signal types only.
- Keep vendor summaries and non-evidentiary scores as enrichment unless strongly documented.
