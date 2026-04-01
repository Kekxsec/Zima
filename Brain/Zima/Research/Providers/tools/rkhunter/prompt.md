---
title: "prompt / tools / rkhunter"
aliases: ["rkhunter", "rkhunter prompt", "rkhunter research prompt"]
tags: [zima, research, prompts, provider-research, tools, rkhunter, graph_exclude]
type: provider_research_prompt
provider: rkhunter
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic tool summary.

## Provider Under Research

- Provider name: rkhunter
- Provider category: tools
- Provider website / API docs URL: SourceForge project
- Documentation / repo URL: official site or packaged docs
- Target module(s) from my provider map: malware_scan
- Build priority / tier: 5 / Later
- Provider role: direct_signal_input
- Tool type: rootkit_scanner
- Primary device use case: detect rootkits, backdoors, and insecure Unix configurations
- OS support: unix, linux
- Important provider-specific cautions:
  - Project freshness appears weak compared with newer alternatives.
  - Expect older signatures and potential false positives.

## Research Instructions

- Use official project materials as primary references.
- Document release freshness, scan coverage, update model, privilege needs, and output format.
- Be explicit about whether this is still worth keeping versus treating as stale legacy tooling.
