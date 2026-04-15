---
title: "prompt / breach / xposedornot"
aliases: ["xposedornot", "xposedornot prompt", "xposedornot research prompt"]
tags: [zima, research, prompts, provider-research, breach, xposedornot, graph_exclude]
type: provider_research_prompt
provider: xposedornot
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

- Provider name: xposedornot
- Provider category: breach
- Provider website / API docs URL: https://xposedornot.com
- Documentation / repo URL: https://xposedornot.com/api_doc
- Target module(s) from my provider map: breach_monitor, credential_exposure
- Build priority / tier: 2 / Core
- Provider role: signal_producer
- Schema hints already captured in my notes:
  - provider_type: free_api
  - identity_use_case: breach checks for emails and domains plus exposed password artifacts
  - supported_entity_type(s): email, domain, password_hash
- Important provider-specific cautions:
  - No-auth for some checks; API key for domain-oriented access.
  - Confirm data freshness, rate limits, and whether password exposure data is direct or derived.

## Research Instructions

- Use official docs as primary sources.
- Confirm endpoints, auth model, JSON schema, limits, and error responses.
- Separate email/domain breach presence from password-specific evidence.
- Do not assume parity with HIBP without documentation.

## Tasks

### 1. API Surface Appendix

- Document the REST API surface and machine-readable response formats.

### 2. Module Mapping

- Map breach and password-related outputs to Zima modules with clear gating logic.

### 3. Signal Contracts

- Define only stable signal contracts based on documented fields.
