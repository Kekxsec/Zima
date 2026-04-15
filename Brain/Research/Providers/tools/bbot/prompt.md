---
title: "prompt / tools / bbot"
aliases: ["bbot", "bbot prompt", "bbot research prompt"]
tags: [zima, research, prompts, provider-research, tools, bbot, graph_exclude]
type: provider_research_prompt
provider: bbot
provider_category: tools
obsidianUIMode: preview
kind: artifact
status: not_started
llm_include: false
code_scope: backend
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: bbot
- Provider category: tools
- Provider website / API docs URL: https://github.com/blacklanternsecurity/bbot
- Target module(s) from my provider map: unknown
- Build priority / tier: 4 / Business
- Provider role: local_tool_or_deferred
- Important provider-specific cautions:
  - Treat this as a local tool unless the docs clearly define stable machine-readable outputs.
  - Distinguish orchestration/runtime features from evidence fields Zima can actually persist.

## Research Instructions

- Use official repository docs as the primary source.
- Confirm installation requirements, CLI entrypoints, auth needs, and output formats.
- Separate direct signal input from enrichment-only, utility-only, and out-of-scope usage.
- Do not invent JSON fields or parser behavior if the docs do not show them.

## Tasks

### 1. Tool Surface Appendix

- Document the main commands, flags, modules, and output artifacts worth integrating.
- Capture supported entity types, execution requirements, and machine-readable output formats.

### 2. Module Mapping

- Decide which Zima modules could consume this tool directly.
- Note whether the tool is better treated as an orchestrator, enrichment source, or signal source.

### 3. Signal Contracts

- Define only implementation-worthy signals.
- If output is mostly workflow/orchestration data, mark it utility-only.
