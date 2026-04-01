---
title: "prompt / tools / vuls"
aliases: ["vuls", "vuls prompt", "vuls research prompt"]
tags: [zima, research, prompts, provider-research, tools, vuls, graph_exclude]
type: provider_research_prompt
provider: vuls
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic tool summary.

## Provider Under Research

- Provider name: vuls
- Provider category: tools
- Provider website / API docs URL: https://vuls.io
- Documentation / repo URL: https://github.com/future-architect/vuls
- Target module(s) from my provider map: software_vulnerability
- Build priority / tier: 2 / Plus
- Provider role: local_tool_or_deferred
- Tool type: vulnerability_scanner
- Primary device use case: agentless vulnerability scanning with OS package intelligence
- OS support: linux, freebsd, ssh-targeted hosts
- Important provider-specific cautions:
  - Primarily Linux-focused and operationally more complex than lightweight endpoint tooling.
  - Distinguish fast/no-root scan modes from deep scan modes.

## Research Instructions

- Use official docs as primary sources.
- Document scan modes, OS coverage, data sources, JSON artifacts, and operational complexity.
- Be explicit about whether Vuls is a good fit for Zima or mainly a comparative option.
