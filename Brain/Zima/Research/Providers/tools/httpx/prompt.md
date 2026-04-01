---
title: "prompt / tools / httpx"
aliases: ["httpx", "httpx prompt", "httpx research prompt"]
tags: [zima, research, prompts, provider-research, tools, httpx, graph_exclude]
type: provider_research_prompt
provider: httpx
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: httpx
- Provider category: tools
- Provider website / API docs URL: https://github.com/projectdiscovery/httpx
- Target module(s) from my provider map: unknown
- Build priority / tier: 4 / Business
- Provider role: local_tool_or_deferred
- Important provider-specific cautions:
  - Confirm which probes are passive metadata collection versus active HTTP interaction.
  - Separate fingerprinting metadata from confirmed exposures.

## Research Instructions

- Use official repository docs as the primary source.
- Confirm CLI usage, probe types, rate controls, JSON/JSONL output, and library support.
- Separate direct signal input from enrichment-only, utility-only, and out-of-scope usage.
- Do not map banners or titles to final risk without documented logic.

## Tasks

### 1. Tool Surface Appendix

- Document commands, flags, probes, output fields, and execution requirements.
- Capture supported entity types and machine-readable formats.

### 2. Module Mapping

- Decide which modules can consume HTTP metadata, headers, TLS, and fingerprints.
- Mark which outputs should trigger follow-on checks rather than direct alerts.

### 3. Signal Contracts

- Define only findings supported by explicit evidence fields.
- Keep generic fingerprinting and crawl metadata as enrichment unless the docs justify stronger mapping.
