---
title: "prompt / tools / photon"
aliases: ["photon", "photon prompt", "photon research prompt"]
tags: [zima, research, prompts, provider-research, tools, photon, graph_exclude]
type: provider_research_prompt
provider: photon
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: photon
- Provider category: tools
- Provider website / API docs URL: https://github.com/s0md3v/Photon
- Target module(s) from my provider map: unknown
- Build priority / tier: 4 / Business
- Provider role: local_tool_or_deferred
- Important provider-specific cautions:
  - Confirm maintenance status and whether the output contract is stable enough for integration.
  - Separate crawler results from verified findings.

## Research Instructions

- Use official repository docs as the primary source.
- Confirm commands, crawl behavior, exports, and machine-readable output.
- Separate direct signal input from enrichment-only, utility-only, and out-of-scope usage.
- Note any maintenance or recency concerns that affect adoption.

## Tasks

### 1. Tool Surface Appendix

- Document commands, flags, outputs, and execution requirements.
- Capture supported entity types and export formats.

### 2. Module Mapping

- Decide where this crawler adds value compared with newer tooling already in the stack.
- Mark whether it should remain optional or historical-only.

### 3. Signal Contracts

- Define signals only if the tool exposes structured evidence that maps cleanly into Zima.
- Otherwise classify it as enrichment or utility-only.
