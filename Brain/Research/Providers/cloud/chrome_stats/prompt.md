---
title: "prompt / cloud / chrome_stats"
aliases: ["chrome_stats", "chrome stats prompt", "chrome_stats research prompt"]
tags: [zima, research, prompts, provider-research, cloud, chrome_stats, graph_exclude]
type: provider_research_prompt
provider: chrome_stats
provider_category: cloud
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

- Provider name: chrome_stats
- Provider category: cloud
- Provider website / API docs URL: https://chrome-stats.com
- Documentation / repo URL: Chrome-Stats API docs
- Target module(s) from my provider map: extension_risk, extension_metadata
- Build priority / tier: 3 / Pro
- Provider role: enrichment_provider
- Tool type: commercial_api
- Primary browser use case: extension metadata, permissions, ratings, and risk context
- Browser support: chromium-based browsers
- Important provider-specific cautions:
  - Requires paid API access.
  - Risk scoring may be opaque; prefer raw evidence fields where available.

## Research Instructions

- Use official docs as primary sources.
- Document auth, extension lookup model, metadata fields, permissions, ratings, and risk indicators.
- Separate direct extension evidence from vendor scoring.
