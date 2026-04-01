---
title: "prompt / tools / sherlock"
aliases: ["sherlock", "sherlock prompt", "sherlock research prompt"]
tags: [zima, research, prompts, provider-research, tools, sherlock, graph_exclude]
type: provider_research_prompt
provider: sherlock
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: sherlock
- Provider category: tools
- Provider website / API docs URL: https://github.com/sherlock-project/sherlock
- Target module(s) from my provider map: unknown
- Build priority / tier: 4 / Business
- Provider role: local_tool_or_deferred
- Important provider-specific cautions:
  - Confirm current site coverage, output formats, and rate-limit behavior.
  - Separate username presence from identity confidence.

## Research Instructions

- Use official repository docs as the primary source.
- Confirm CLI usage, JSON export support, site metadata, and error handling.
- Separate direct signal input from enrichment-only, utility-only, and out-of-scope usage.
- Do not treat a found username as proof of account ownership without corroboration.

## Tasks

### 1. Tool Surface Appendix

- Document commands, flags, output artifacts, and execution requirements.
- Capture supported entity types and machine-readable formats.

### 2. Module Mapping

- Decide where username enumeration fits within Zima identity workflows.
- Separate discovery from higher-confidence attribution.

### 3. Signal Contracts

- Define only defensible signals supported by documented outputs.
- Mark most account-presence results as enrichment unless corroboration rules are strong.
