---
title: "prompt / breach / enzoic"
aliases: ["enzoic", "enzoic prompt", "enzoic research prompt"]
tags: [zima, research, prompts, provider-research, breach, enzoic, graph_exclude]
type: provider_research_prompt
provider: enzoic
provider_category: breach
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: enzoic
- Provider category: breach
- Provider website / API docs URL: https://www.enzoic.com
- Documentation / repo URL: https://docs.enzoic.com
- Target module(s) from my provider map: credential_exposure, breach_monitor, username_exposure, alias_correlation
- Build priority / tier: 3 / Pro
- Provider role: signal_producer
- Schema hints already captured in my notes:
  - provider_type: commercial_api
  - identity_use_case: compromised password and credential screening with breach and PII alerts
  - supported_entity_type(s): email, username, password, phone, name, pii
- Important provider-specific cautions:
  - Paid proprietary API.
  - Confirm whether password checks, breach checks, and malware-log style exposure are separate artifacts.

## Research Instructions

- Use official docs as primary sources.
- Document auth, search methods, response fields, and any password-hash lookup semantics.
- Separate true credential exposure signals from enrichment-only identity data.
- Mark unclear or marketing-only claims as unknown.

## Tasks

### 1. API Surface Appendix

- Document endpoints, schemas, and examples for compromise and exposure checks.

### 2. Module Mapping

- Map likely outputs to credential, breach, username, and alias workflows.

### 3. Signal Contracts

- Define signals only where raw evidence is present and implementation-worthy.
