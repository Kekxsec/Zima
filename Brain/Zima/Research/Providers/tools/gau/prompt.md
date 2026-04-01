---
title: "prompt / tools / gau"
aliases: ["gau", "gau prompt", "gau research prompt"]
tags: [zima, research, prompts, provider-research, tools, gau, graph_exclude]
type: provider_research_prompt
provider: gau
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: gau
- Provider category: tools
- Provider website / API docs URL: https://github.com/lc/gau
- Target module(s) from my provider map: unknown
- Build priority / tier: 4 / Business
- Provider role: local_tool_or_deferred
- Important provider-specific cautions:
  - Confirm which passive URL sources are built in and which are optional.
  - Separate historical URL discovery from active risk findings.

## Research Instructions

- Use official repository docs as the primary source.
- Confirm CLI usage, output formats, filtering behavior, and source metadata.
- Separate direct signal input from enrichment-only, utility-only, and out-of-scope usage.
- Do not infer vulnerability findings from URL collection alone.

## Tasks

### 1. Tool Surface Appendix

- Document commands, flags, sources, and output artifacts.
- Capture supported entity types and machine-readable formats.

### 2. Module Mapping

- Decide where passive URL history is useful in Zima.
- Mark whether the tool is primarily enrichment or can support direct signals.

### 3. Signal Contracts

- Define only signals supported by documented evidence.
- Historical URLs should usually be treated as context unless paired with stronger findings.
