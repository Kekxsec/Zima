---
title: "prompt / breach / hackcheck"
aliases: ["hackcheck", "hackcheck prompt", "hackcheck research prompt"]
tags: [zima, research, prompts, provider-research, breach, hackcheck, graph_exclude]
type: provider_research_prompt
provider: hackcheck
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

- Provider name: hackcheck
- Provider category: breach
- Provider website / API docs URL: https://hackcheck.woventeams.com
- Documentation / repo URL: https://hackcheck.woventeams.com/api/v4
- Target module(s) from my provider map: breach_monitor, username_exposure
- Build priority / tier: 1 / Core
- Provider role: signal_producer
- Schema hints already captured in my notes:
  - provider_type: free_api
  - identity_use_case: breach checks for email or username
  - supported_entity_type(s): email, username
- Important provider-specific cautions:
  - Likely outdated or static dataset; validate recency from primary sources.
  - Community or legacy HIBP-like coverage may limit reliability.

## Research Instructions

- Use official docs as primary sources.
- Confirm endpoint behavior, JSON schema, and any recency or maintenance signals.
- Separate historical utility from current production-grade signal value.
- Be explicit if the data appears stale.

## Tasks

### 1. API Surface Appendix

- Document the API surface and response variants.

### 2. Module Mapping

- Map email and username breach hits to Zima only if the evidence is still usable.

### 3. Signal Contracts

- Define signal contracts only if the underlying data source is still credible enough for use.
