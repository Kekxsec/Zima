---
title: "prompt / tools / hindsight"
aliases: ["hindsight", "hindsight prompt", "hindsight research prompt"]
tags: [zima, research, prompts, provider-research, tools, hindsight, graph_exclude]
type: provider_research_prompt
provider: hindsight
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic tool summary.

## Provider Under Research

- Provider name: hindsight
- Provider category: tools
- Provider website / API docs URL: https://github.com/obsidianforensics/hindsight
- Documentation / repo URL: https://github.com/obsidianforensics/hindsight
- Target module(s) from my provider map: browser_inventory, browser_forensics
- Build priority / tier: 4 / Business
- Provider role: local_tool_or_deferred
- Tool type: local_library
- Primary browser use case: deep Chromium-history and extension artifact parsing for forensic review
- Browser support: chrome, chromium, brave
- Important provider-specific cautions:
  - More forensic/post-facto than a lightweight launch-time posture collector.
  - Chromium-focused rather than cross-browser.

## Research Instructions

- Use repo materials as primary references.
- Document artifact coverage, browser support, output structure, library/CLI usage, and whether it is practical for routine local scans.
- Be explicit about whether Zima should treat this as analyst tooling rather than MVP signal infrastructure.
