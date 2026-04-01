---
title: "prompt / tools / dnsx"
aliases: ["dnsx", "dnsx prompt", "dnsx research prompt"]
tags: [zima, research, prompts, provider-research, tools, dnsx, graph_exclude]
type: provider_research_prompt
provider: dnsx
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: dnsx
- Provider category: tools
- Provider website / API docs URL: https://github.com/projectdiscovery/dnsx
- Target module(s) from my provider map: unknown
- Build priority / tier: 4 / Business
- Provider role: local_tool_or_deferred
- Important provider-specific cautions:
  - Confirm whether JSON or JSONL output is stable enough to parse directly.
  - Separate raw DNS enrichment from true findings.

## Research Instructions

- Use official repository docs as the primary source.
- Confirm supported record types, resolver behavior, rate controls, and output formats.
- Separate direct signal input from enrichment-only, utility-only, and out-of-scope usage.
- Do not invent fields or output contracts.

## Tasks

### 1. Tool Surface Appendix

- Document commands, flags, DNS record outputs, and machine-readable artifacts.
- Capture supported entity types and execution requirements.

### 2. Module Mapping

- Decide which Zima modules can consume dnsx output directly.
- Call out which outputs are enrichment-only versus implementation-worthy signals.

### 3. Signal Contracts

- Define signals only where documented evidence supports them.
- Keep pure DNS resolution data separate from risk findings.
