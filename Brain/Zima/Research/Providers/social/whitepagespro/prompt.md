---
title: "prompt / social / whitepagespro"
aliases: ["whitepagespro", "whitepagespro prompt", "whitepagespro research prompt"]
tags: [zima, research, prompts, provider-research, social, whitepagespro, graph_exclude]
type: provider_research_prompt
provider: whitepagespro
provider_category: social
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: whitepagespro
- Provider category: social
- Provider website / API docs URL: https://pro.whitepages.com
- Documentation / repo URL: https://pro.whitepages.com
- Target module(s) from my provider map: alias_correlation, domain_identity_correlation, phone_exposure
- Build priority / tier: 3 / Pro
- Provider role: enrichment_provider
- Schema hints already captured in my notes:
  - provider_type: saas_api
  - identity_use_case: identity verification and cross-matching of name, phone, address, email, and ip
  - supported_entity_type(s): name, phone, address, email, ip
- Important provider-specific cautions:
  - Paid verification service rather than a breach dataset.
  - Strong fit for cross-checking and identity proofing, but likely enrichment-first.

## Research Instructions

- Use official vendor docs as primary sources.
- Confirm API products, request fields, verification outputs, and confidence or risk fields.
- Separate identity-proofing outputs from breach or exposure findings.
- Do not turn verification scores into direct risk without documented basis.

## Tasks

### 1. API Surface Appendix

- Document identity-check and lookup endpoints relevant to Zima.

### 2. Module Mapping

- Focus on alias correlation, domain-linked identity resolution, and structured phone cross-checks.

### 3. Signal Contracts

- Likely enrichment-heavy; define direct signals only when raw evidence supports them.
