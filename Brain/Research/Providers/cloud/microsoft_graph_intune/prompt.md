---
title: "prompt / cloud / microsoft_graph_intune"
aliases: ["microsoft_graph_intune", "microsoft graph intune prompt", "microsoft_graph_intune research prompt"]
tags: [zima, research, prompts, provider-research, cloud, microsoft_graph_intune, graph_exclude]
type: provider_research_prompt
provider: microsoft_graph_intune
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

- Provider name: microsoft_graph_intune
- Provider category: cloud
- Provider website / API docs URL: https://learn.microsoft.com/graph
- Documentation / repo URL: Microsoft Graph Intune API docs
- Target module(s) from my provider map: os_security, patch_status, disk_encryption_check
- Build priority / tier: 4 / Business
- Provider role: enrichment_provider
- Tool type: commercial_api
- Primary device use case: managed device inventory, compliance, and encryption posture
- OS support: windows, macos, android, ios
- Important provider-specific cautions:
  - Requires Intune licensing and managed devices.
  - Cloud-side state may lag or differ from local reality.

## Research Instructions

- Use official Microsoft docs as primary sources.
- Document device, compliance, encryption, and update-related entities, auth scopes, and JSON schemas.
- Treat this as enrichment for managed environments rather than a universal device collector.
