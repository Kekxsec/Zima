---
title: "prompt / tools / browseraddonsview"
aliases: ["browseraddonsview", "browseraddonsview prompt", "browseraddonsview research prompt"]
tags: [zima, research, prompts, provider-research, tools, browseraddonsview, graph_exclude]
type: provider_research_prompt
provider: browseraddonsview
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

- Provider name: browseraddonsview
- Provider category: tools
- Provider website / API docs URL: https://www.nirsoft.net
- Documentation / repo URL: NirSoft BrowserAddonsView page
- Target module(s) from my provider map: browser_inventory, extension_risk
- Build priority / tier: 2 / Plus
- Provider role: local_tool_or_deferred
- Tool type: local_cli
- Primary browser use case: local add-on and extension inventory on Windows browsers
- Browser support: chrome, edge, firefox, internet_explorer
- Important provider-specific cautions:
  - Windows-only freeware utility.
  - Treat this as local evidence collection, not extension reputation or policy intelligence.

## Research Instructions

- Use official vendor materials as primary references.
- Document supported browsers, fields exposed, export formats, automation/headless fit, and per-user versus system scope.
- Focus on whether output is stable enough for normalized browser inventory and extension evidence.
