---
title: "prompt / tools / gowitness"
aliases: ["gowitness", "gowitness prompt", "gowitness research prompt"]
tags: [zima, research, prompts, provider-research, tools, gowitness, graph_exclude]
type: provider_research_prompt
provider: gowitness
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: gowitness
- Provider category: tools
- Provider website / API docs URL: https://github.com/sensepost/gowitness
- Target module(s) from my provider map: unknown
- Build priority / tier: 4 / Business
- Provider role: local_tool_or_deferred
- Important provider-specific cautions:
  - Treat screenshots as evidence and analyst UX output, not a standalone security finding.
  - Confirm output artifacts, database support, and headless browser requirements.

## Research Instructions

- Use official repository docs as the primary source.
- Confirm commands, output directories, database artifacts, and exportable fields.
- Separate direct signal input from enrichment-only, utility-only, and out-of-scope usage.
- Do not conflate screenshots with verified exposures.

## Tasks

### 1. Tool Surface Appendix

- Document commands, flags, output artifacts, and execution requirements.
- Capture supported entity types and machine-readable formats.

### 2. Module Mapping

- Decide where screenshots or captured metadata support Zima workflows.
- Mark evidence capture separately from risk detection.

### 3. Signal Contracts

- Only define signals if the tool exposes structured security-relevant metadata.
- Otherwise classify it as enrichment or utility-only.
