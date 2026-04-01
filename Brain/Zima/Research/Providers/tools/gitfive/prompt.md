---
title: "prompt / tools / gitfive"
aliases: ["gitfive", "gitfive prompt", "gitfive research prompt"]
tags: [zima, research, prompts, provider-research, tools, gitfive, graph_exclude]
type: provider_research_prompt
provider: gitfive
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: gitfive
- Provider category: tools
- Provider website / API docs URL: https://github.com/mxrch/GitFive
- Target module(s) from my provider map: unknown
- Build priority / tier: 4 / Business
- Provider role: local_tool_or_deferred
- Important provider-specific cautions:
  - Confirm usage terms before treating this as a productized provider.
  - Distinguish GitHub identity attribution from high-confidence account takeover or impersonation findings.

## Research Instructions

- Use official repository docs as the primary source.
- Confirm execution flow, dependencies, output structure, and usage constraints.
- Separate direct signal input from enrichment-only, utility-only, and out-of-scope usage.
- Do not overstate confidence for inferred identity links.

## Tasks

### 1. Tool Surface Appendix

- Document commands, flags, output artifacts, and execution requirements.
- Capture supported entity types and machine-readable formats.

### 2. Module Mapping

- Decide whether GitHub identity investigation fits Zima directly or only as analyst tooling.
- Note legal or licensing constraints that affect implementation.

### 3. Signal Contracts

- Define only stable, defensible signal contracts.
- Mark attribution chains as enrichment if the evidence is weak or heavily inferred.
