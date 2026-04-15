---
title: "prompt / darkweb / acuris_stolen_identities"
aliases: ["acuris_stolen_identities", "acuris_stolen_identities prompt", "acuris_stolen_identities research prompt"]
tags: [zima, research, prompts, provider-research, darkweb, acuris_stolen_identities, graph_exclude]
type: provider_research_prompt
provider: acuris_stolen_identities
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

## Provider Under Research

- Provider name: acuris_stolen_identities
- Provider category: darkweb
- Provider website / API docs URL: https://iongroup.com
- Documentation / repo URL: https://iongroup.com
- Target module(s) from my provider map: breach_monitor, credential_exposure, alias_correlation
- Build priority / tier: 4 / Business
- Provider role: signal_producer
- Schema hints already captured in my notes:
  - provider_type: commercial_api
  - identity_use_case: compromised identity and pii search on dark web
  - supported_entity_type(s): name, ssn, address, passport, email, domain, username, password
- Important provider-specific cautions:
  - Large-enterprise and insurer-oriented commercial product.
  - Verify whether there is an exposed API or only product-level documentation.

## Research Instructions

- Use official vendor materials as primary sources.
- Confirm API availability, auth model, searchable fields, response schemas, and evidence artifacts.
- Separate breach-style records from marketplace, fraud, and identity-theft signals.
- Avoid relying on marketing metrics without implementation detail.

## Tasks

### 1. API Surface Appendix

- Document searchable identity artifacts and any JSON or export schemas.

### 2. Module Mapping

- Map usable outputs into breach, credential, and alias workflows.

### 3. Signal Contracts

- Define only implementation-worthy signals with clear evidentiary fields.
