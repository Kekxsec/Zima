---
title: "prompt / tools / katana"
aliases: ["katana", "katana prompt", "katana research prompt"]
tags: [zima, research, prompts, provider-research, tools, katana, graph_exclude]
type: provider_research_prompt
provider: katana
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: katana
- Provider category: tools
- Provider website / API docs URL: https://github.com/projectdiscovery/katana
- Target module(s) from my provider map: unknown
- Build priority / tier: 4 / Business
- Provider role: local_tool_or_deferred
- Important provider-specific cautions:
  - Confirm active crawling behavior, JavaScript parsing, and headless features before mapping into default scans.
  - Separate discovered content and endpoints from confirmed findings.

## Research Instructions

- Use official repository docs as the primary source.
- Confirm crawl scope, rate controls, JSONL output, and extraction features.
- Separate direct signal input from enrichment-only, utility-only, and out-of-scope usage.
- Treat this as more active than passive OSINT unless the docs say otherwise.

## Tasks

### 1. Tool Surface Appendix

- Document commands, flags, crawl modes, output fields, and execution requirements.
- Capture supported entity types and machine-readable formats.

### 2. Module Mapping

- Decide which modules can use discovered URLs, forms, emails, and response metadata.
- Mark what should remain analyst-driven or opt-in.

### 3. Signal Contracts

- Define only signals with explicit, defensible trigger logic.
- Keep crawl artifacts and content discovery as enrichment unless documented evidence supports more.
