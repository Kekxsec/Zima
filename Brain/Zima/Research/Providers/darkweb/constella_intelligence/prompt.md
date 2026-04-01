---
title: "prompt / darkweb / constella_intelligence"
aliases: ["constella_intelligence", "constella_intelligence prompt", "constella_intelligence research prompt"]
tags: [zima, research, prompts, provider-research, darkweb, constella_intelligence, graph_exclude]
type: provider_research_prompt
provider: constella_intelligence
provider_category: darkweb
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: constella_intelligence
- Provider category: darkweb
- Provider website / API docs URL: https://constella.ai
- Documentation / repo URL: https://constella.ai
- Target module(s) from my provider map: breach_monitor, credential_exposure, username_exposure, phone_exposure
- Build priority / tier: 4 / Business
- Provider role: signal_producer
- Schema hints already captured in my notes:
  - provider_type: saas_api
  - identity_use_case: identity-theft and dark-web monitoring with identity fraud alerts
  - supported_entity_type(s): names, government ids, cards, emails, domains, usernames, phones
- Important provider-specific cautions:
  - Likely partner or enterprise access only.
  - Marketing claims may exceed what the actual API exposes; verify actual response fields carefully.

## Research Instructions

- Use official product and API materials as primary sources.
- Confirm whether there is a documented API, export schema, or partner-only feed.
- Separate dark-web monitoring data from identity-resolution or fraud-scoring layers.
- Mark undocumented claims as unknown.

## Tasks

### 1. API Surface Appendix

- Document actual accessible endpoints or artifacts, if any.

### 2. Module Mapping

- Map breach, credential, username, and phone-related outputs to Zima where direct evidence exists.

### 3. Signal Contracts

- Define only signals grounded in documented raw evidence fields.
