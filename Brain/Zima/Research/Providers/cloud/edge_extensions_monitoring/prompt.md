---
title: "prompt / cloud / edge_extensions_monitoring"
aliases: ["edge_extensions_monitoring", "edge extensions monitoring prompt", "edge_extensions_monitoring research prompt"]
tags: [zima, research, prompts, provider-research, cloud, edge_extensions_monitoring, graph_exclude]
type: provider_research_prompt
provider: edge_extensions_monitoring
provider_category: cloud
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: edge_extensions_monitoring
- Provider category: cloud
- Provider website / API docs URL: Microsoft Docs
- Documentation / repo URL: Edge Extensions Monitoring docs
- Target module(s) from my provider map: extension_risk, extension_metadata
- Build priority / tier: 4 / Business
- Provider role: enrichment_provider
- Tool type: commercial_api
- Primary browser use case: managed Edge extension inventory and usage aggregation
- Browser support: edge on managed windows environments
- Important provider-specific cautions:
  - Preview/admin-centric feature set.
  - Aggregated telemetry may not replace local extension evidence.

## Research Instructions

- Use official Microsoft docs as primary sources.
- Document prerequisites, admin controls, extension inventory fields, and whether data is tenant-wide or device-specific.
- Be explicit about preview limitations and Windows/Edge-only scope.
