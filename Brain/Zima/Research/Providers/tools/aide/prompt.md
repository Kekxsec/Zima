---
title: "prompt / tools / aide"
aliases: ["aide", "aide prompt", "aide research prompt"]
tags: [zima, research, prompts, provider-research, tools, aide, graph_exclude]
type: provider_research_prompt
provider: aide
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic tool summary.

## Provider Under Research

- Provider name: aide
- Provider category: tools
- Provider website / API docs URL: https://aide.github.io
- Documentation / repo URL: official site and GitHub
- Target module(s) from my provider map: file_integrity
- Build priority / tier: 3 / Pro
- Provider role: direct_signal_input
- Tool type: file_integrity_checker
- Primary device use case: detect file-system tampering through integrity database comparisons
- OS support: unix, linux, macos
- Important provider-specific cautions:
  - Requires baseline initialization before it becomes useful.
  - Diff-heavy output may create noise without careful scoping.

## Research Instructions

- Use official project materials as primary references.
- Document baseline workflow, database storage, check granularity, output structure, and operational burden for individual devices.
- Be explicit about whether AIDE is practical for Zima launch or better as an advanced/deferred control.
