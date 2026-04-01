---
title: "prompt / tools / subfinder"
aliases: ["subfinder", "subfinder prompt", "subfinder research prompt"]
tags: [zima, research, prompts, provider-research, tools, subfinder, graph_exclude]
type: provider_research_prompt
provider: subfinder
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: subfinder
- Provider category: tools
- Provider website / API docs URL: https://github.com/projectdiscovery/subfinder
- Target module(s) from my provider map: unknown
- Build priority / tier: 4 / Business
- Provider role: local_tool_or_deferred
- Important provider-specific cautions:
  - Confirm passive-only behavior, source coverage, and JSON or JSONL output details.
  - Separate discovered assets from validated exposures.

## Research Instructions

- Use official repository docs as the primary source.
- Confirm commands, source configuration, rate controls, and output formats.
- Separate direct signal input from enrichment-only, utility-only, and out-of-scope usage.
- Do not treat a discovered subdomain as a security finding by itself.

## Tasks

### 1. Tool Surface Appendix

- Document commands, flags, sources, outputs, and execution requirements.
- Capture supported entity types and machine-readable formats.

### 2. Module Mapping

- Decide where passive subdomain discovery fits in Zima.
- Mark which downstream providers should consume discovered assets.

### 3. Signal Contracts

- Define direct signals only where the tool exposes evidence beyond raw discovery.
- Otherwise classify it as enrichment or utility-only.
