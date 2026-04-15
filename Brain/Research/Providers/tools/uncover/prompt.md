---
title: "prompt / tools / uncover"
aliases: ["uncover", "uncover prompt", "uncover research prompt"]
tags: [zima, research, prompts, provider-research, tools, uncover, graph_exclude]
type: provider_research_prompt
provider: uncover
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

- Provider name: uncover
- Provider category: tools
- Provider website / API docs URL: https://github.com/projectdiscovery/uncover
- Target module(s) from my provider map: unknown
- Build priority / tier: 4 / Business
- Provider role: local_tool_or_deferred
- Important provider-specific cautions:
  - Confirm which third-party search engines are supported and what credentials each requires.
  - Treat uncover as an abstraction layer over external providers, not as an authoritative source by itself.

## Research Instructions

- Use official repository docs as the primary source.
- Confirm commands, engine coverage, auth model, output formats, and source attribution.
- Separate direct signal input from enrichment-only, utility-only, and out-of-scope usage.
- Note where downstream source-specific research may still be required.

## Tasks

### 1. Tool Surface Appendix

- Document commands, flags, engines, outputs, and execution requirements.
- Capture supported entity types and machine-readable formats.

### 2. Module Mapping

- Decide where meta-search over internet datasets fits in Zima.
- Mark whether this should seed or proxy other provider categories.

### 3. Signal Contracts

- Define only signals with clear evidence and source attribution.
- If uncover mostly aggregates search results, keep it enrichment or utility-first.
