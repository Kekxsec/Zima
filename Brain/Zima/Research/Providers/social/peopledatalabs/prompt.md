---
title: "prompt / social / peopledatalabs"
aliases: ["peopledatalabs", "peopledatalabs prompt", "peopledatalabs research prompt"]
tags: [zima, research, prompts, provider-research, social, peopledatalabs, graph_exclude]
type: provider_research_prompt
provider: peopledatalabs
provider_category: social
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: peopledatalabs
- Provider category: social
- Provider website / API docs URL: https://www.peopledatalabs.com
- Documentation / repo URL: https://docs.peopledatalabs.com
- Target module(s) from my provider map: alias_correlation, domain_identity_correlation
- Build priority / tier: 4 / Business
- Provider role: enrichment_provider
- Schema hints already captured in my notes:
  - provider_type: saas_api
  - identity_use_case: person lookup and enrichment for alias correlation
  - supported_entity_type(s): name, email, phone, social handle, employer
- Important provider-specific cautions:
  - Commercial enrichment API with licensing requirements.
  - Prioritize identity-resolution evidence and avoid overclaiming certainty on profile linkage.

## Research Instructions

- Use official docs as primary sources.
- Confirm enrichment endpoints, matching semantics, confidence fields, and response schema.
- Separate enrichment-only identity resolution from any direct risk signals.
- Do not confuse marketing counts with implementation-ready evidence.

## Tasks

### 1. API Surface Appendix

- Document person-enrichment and search artifacts relevant to Zima.

### 2. Module Mapping

- Focus on alias correlation and domain-linked identity resolution.

### 3. Signal Contracts

- Likely enrichment-heavy; define direct signals only if supported by explicit documented evidence.
