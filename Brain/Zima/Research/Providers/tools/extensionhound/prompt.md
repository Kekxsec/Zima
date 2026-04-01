---
title: "prompt / tools / extensionhound"
aliases: ["extensionhound", "extensionhound prompt", "extensionhound research prompt"]
tags: [zima, research, prompts, provider-research, tools, extensionhound, graph_exclude]
type: provider_research_prompt
provider: extensionhound
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic tool summary.

## Provider Under Research

- Provider name: extensionhound
- Provider category: tools
- Provider website / API docs URL: https://github.com/arsolutioner/ExtensionHound
- Documentation / repo URL: https://github.com/arsolutioner/ExtensionHound
- Target module(s) from my provider map: extension_risk, browser_inventory
- Build priority / tier: 3 / Pro
- Provider role: local_tool_or_deferred
- Tool type: local_cli
- Primary browser use case: extension-focused analysis and network-oriented forensics for Chromium-family browsers
- Browser support: chrome, edge, brave, opera
- Important provider-specific cautions:
  - More forensic/analytical than lightweight inventory collection.
  - External API dependencies may affect reproducibility and portability.

## Research Instructions

- Use repo materials as primary references.
- Document what local artifacts it parses, what enrichment APIs it relies on, what output it produces, and whether it is realistic for individual-launch productization.
- Separate deep analyst workflow value from automatable Zima signal value.
