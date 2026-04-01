---
title: "prompt / social / pipl"
aliases: ["pipl", "pipl prompt", "pipl research prompt"]
tags: [zima, research, prompts, provider-research, social, pipl, graph_exclude]
type: provider_research_prompt
provider: pipl
provider_category: social
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: pipl
- Provider category: social
- Provider website / API docs URL: https://pipl.com
- Documentation / repo URL: https://pipl.com
- Target module(s) from my provider map: alias_correlation, domain_identity_correlation
- Build priority / tier: 4 / Business
- Provider role: enrichment_provider
- Schema hints already captured in my notes:
  - provider_type: saas_api
  - identity_use_case: identity resolution across names, phones, emails, usernames, and employers
  - supported_entity_type(s): name, address, email, phone, username, employer
- Important provider-specific cautions:
  - Paid commercial service with legal and accuracy considerations.
  - Confirm whether a current documented API exists and what fields are still supported.

## Research Instructions

- Use official vendor materials as primary sources.
- Confirm API availability, auth model, schema, confidence attributes, and usage constraints.
- Treat person-match and identity-linkage outputs as enrichment unless documented evidence supports stronger claims.
- Be explicit about jurisdiction or compliance constraints if documented.

## Tasks

### 1. API Surface Appendix

- Document the current person lookup or identity search artifacts relevant to Zima.

### 2. Module Mapping

- Focus on alias and domain-linked identity correlation.

### 3. Signal Contracts

- Define only direct signals that can be justified from raw evidence fields.
