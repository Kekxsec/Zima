---
title: "prompt / tools / lunar"
aliases: ["lunar", "lunar prompt", "lunar research prompt"]
tags: [zima, research, prompts, provider-research, tools, lunar, graph_exclude]
type: provider_research_prompt
provider: lunar
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic tool summary.

## Provider Under Research

- Provider name: lunar
- Provider category: tools
- Provider website / API docs URL: GitHub
- Documentation / repo URL: GitHub repo
- Target module(s) from my provider map: configuration_audit, system_audit
- Build priority / tier: 4 / Business
- Provider role: direct_signal_input
- Tool type: cis_based_audit_script
- Primary device use case: CIS/STIG-style Unix hardening audit
- OS support: linux, macos, solaris, freebsd
- Important provider-specific cautions:
  - Some modes may change system state rather than remain read-only.
  - Complexity and benchmark breadth may be excessive for individual-launch scope.

## Research Instructions

- Use repo materials as primary references.
- Document safe read-only modes, benchmark coverage, output format, privilege needs, and any lockdown/remediation behavior.
- Be explicit about whether Zima should use this for launch or treat it as a deferred heavier audit option.
