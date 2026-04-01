---
title: "prompt / tools / yasat"
aliases: ["yasat", "yasat prompt", "yasat research prompt"]
tags: [zima, research, prompts, provider-research, tools, yasat, graph_exclude]
type: provider_research_prompt
provider: yasat
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic tool summary.

## Provider Under Research

- Provider name: yasat
- Provider category: tools
- Provider website / API docs URL: GitHub
- Documentation / repo URL: GitHub repo
- Target module(s) from my provider map: configuration_audit, patch_status
- Build priority / tier: 3 / Pro
- Provider role: direct_signal_input
- Tool type: system_audit
- Primary device use case: lightweight Unix security and configuration auditing
- OS support: linux, unix
- Important provider-specific cautions:
  - Text-report output will need parsing or custom normalization.
  - Coverage appears simpler and narrower than heavier audit tools like Lynis.

## Research Instructions

- Use repo materials as primary references.
- Document supported checks, runtime model, output format, privilege assumptions, and maintenance status.
- Be explicit about whether this is strong enough for productized signals or better used as a reference script.
