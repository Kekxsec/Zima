---
title: "prompt / tools / helium"
aliases: ["helium", "helium prompt", "helium research prompt"]
tags: [zima, research, prompts, provider-research, tools, helium, graph_exclude]
type: provider_research_prompt
provider: helium
provider_category: tools
obsidianUIMode: preview
kind: artifact
status: not_started
llm_include: false
code_scope: backend
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic tool summary.

## Provider Under Research

- Provider name: helium
- Provider category: tools
- Provider website / API docs URL: https://www.powershellgallery.com
- Documentation / repo URL: Helium Get-Browsers docs
- Target module(s) from my provider map: browser_configuration, browser_inventory
- Build priority / tier: 2 / Plus
- Provider role: local_tool_or_deferred
- Tool type: local_cli
- Primary browser use case: installed browser detection and version collection
- Browser support: chrome, edge, firefox, brave, chromium
- Important provider-specific cautions:
  - Windows and Linux oriented.
  - Inventory-only, with no extension or browser-policy depth.

## Research Instructions

- Use official docs or maintained source materials as primary references.
- Document install/runtime model, output format, browser detection method, and version evidence.
- Treat this as utility or evidence collection unless there is stronger structured posture output.
