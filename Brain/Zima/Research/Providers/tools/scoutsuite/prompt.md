---
title: "prompt / tools / scoutsuite"
aliases: ["scoutsuite", "scoutsuite prompt", "scoutsuite research prompt"]
tags: [zima, research, prompts, provider-research, tools, scoutsuite, graph_exclude]
type: provider_research_prompt
provider: scoutsuite
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: scoutsuite
- Provider category: tools
- Provider website / API docs URL: https://github.com/nccgroup/ScoutSuite
- Target module(s) from my provider map: unknown
- Build priority / tier: 4 / Business
- Provider role: local_tool_or_deferred
- Important provider-specific cautions:
  - Confirm supported cloud platforms and output/report format stability.
  - Separate offline reporting UX from evidence fields Zima should ingest.

## Research Instructions

- Use official repository docs as the primary source.
- Confirm commands, auth model, offline report behavior, and machine-readable output artifacts.
- Separate direct signal input from enrichment-only, utility-only, and out-of-scope usage.
- Note any recency or maintenance concerns that affect adoption.

## Tasks

### 1. Tool Surface Appendix

- Document commands, cloud coverage, reports, and execution requirements.
- Capture supported entity types and exportable fields.

### 2. Module Mapping

- Decide whether ScoutSuite should be integrated directly or kept as optional comparative tooling.
- Separate posture findings from inventory and visualization output.

### 3. Signal Contracts

- Define only stable signal contracts backed by documented finding fields.
- Note where Prowler may be the better primary integration if overlap is high.
