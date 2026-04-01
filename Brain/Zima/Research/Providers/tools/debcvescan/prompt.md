---
title: "prompt / tools / debcvescan"
aliases: ["debcvescan", "debcvescan prompt", "debcvescan research prompt"]
tags: [zima, research, prompts, provider-research, tools, debcvescan, graph_exclude]
type: provider_research_prompt
provider: debcvescan
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic tool summary.

## Provider Under Research

- Provider name: debcvescan
- Provider category: tools
- Provider website / API docs URL: GitHub
- Documentation / repo URL: GitHub repo and project docs
- Target module(s) from my provider map: software_vulnerability, patch_status
- Build priority / tier: 2 / Plus
- Provider role: direct_signal_input
- Tool type: debian_vulnerability_scanner
- Primary device use case: lightweight CVE scanning for installed Debian or Ubuntu packages
- OS support: debian, ubuntu
- Important provider-specific cautions:
  - Debian-family only.
  - Third-party project, so source quality and update cadence need validation.

## Research Instructions

- Use repo materials and project docs as primary references.
- Document JSON support, package-data source, installation paths, privilege requirements, and scan coverage.
- Be explicit about where this outperforms or simply duplicates debsecan.
