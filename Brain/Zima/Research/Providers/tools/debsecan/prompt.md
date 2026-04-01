---
title: "prompt / tools / debsecan"
aliases: ["debsecan", "debsecan prompt", "debsecan research prompt"]
tags: [zima, research, prompts, provider-research, tools, debsecan, graph_exclude]
type: provider_research_prompt
provider: debsecan
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic tool summary.

## Provider Under Research

- Provider name: debsecan
- Provider category: tools
- Provider website / API docs URL: Debian/Ubuntu packaged tool
- Documentation / repo URL: man page and package docs
- Target module(s) from my provider map: software_vulnerability, patch_status
- Build priority / tier: 2 / Plus
- Provider role: direct_signal_input
- Tool type: debian_vulnerability_scanner
- Primary device use case: list known CVEs in installed Debian or Ubuntu packages
- OS support: debian, ubuntu
- Important provider-specific cautions:
  - Debian-family only.
  - Text-oriented output may need normalization unless stable machine-readable flags exist.

## Research Instructions

- Use packaged documentation and official sources as primary references.
- Document data source, update model, output options, privilege requirements, and CVE-to-package mapping quality.
- Be explicit about whether this is better than or complementary to broader scanners like Trivy or Vuls.
