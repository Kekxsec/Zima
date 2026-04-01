---
title: "prompt / cloud / defender_vm_api"
aliases: ["defender_vm_api", "defender vm api prompt", "defender_vm_api research prompt"]
tags: [zima, research, prompts, provider-research, cloud, defender_vm_api, graph_exclude]
type: provider_research_prompt
provider: defender_vm_api
provider_category: cloud
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: defender_vm_api
- Provider category: cloud
- Provider website / API docs URL: Microsoft Defender API docs
- Documentation / repo URL: BrowserExtensionsInventory docs
- Target module(s) from my provider map: extension_risk, extension_intel
- Build priority / tier: 4 / Business
- Provider role: enrichment_provider
- Tool type: commercial_api
- Primary browser use case: managed browser extension inventory, permissions, and risk context on Windows
- Browser support: edge, chrome, firefox on windows
- Important provider-specific cautions:
  - Requires Defender for Endpoint enablement and licensing.
  - Windows-focused despite multi-browser support.

## Research Instructions

- Use official Microsoft docs as primary sources.
- Document auth, BrowserExtensionsInventory schema, permission fields, and risk indicators.
- Distinguish inventory, permissions, and any risk scoring or classification fields.
