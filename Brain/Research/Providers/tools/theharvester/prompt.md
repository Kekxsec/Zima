---
title: "prompt / tools / theharvester"
aliases: ["theharvester", "theharvester prompt", "theharvester research prompt"]
tags: [zima, research, prompts, provider-research, tools, theharvester, graph_exclude]
type: provider_research_prompt
provider: theharvester
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

- Provider name: theharvester
- Provider category: tools
- Provider website / API docs URL: https://github.com/laramies/theHarvester
- Target module(s) from my provider map: unknown
- Build priority / tier: 4 / Business
- Provider role: local_tool_or_deferred
- Important provider-specific cautions:
  - Confirm source-specific auth, rate limits, and which results come from paid integrations.
  - Separate raw OSINT collection from high-confidence findings.

## Research Instructions

- Use official repository docs as the primary source.
- Confirm commands, sources, output formats, and per-source schema limitations.
- Separate direct signal input from enrichment-only, utility-only, and out-of-scope usage.
- Do not merge source-level confidence into one blanket severity.

## Tasks

### 1. Tool Surface Appendix

- Document commands, flags, sources, outputs, and execution requirements.
- Capture supported entity types and machine-readable formats.

### 2. Module Mapping

- Decide which Zima modules can consume emails, names, subdomains, IPs, and URLs from this tool.
- Mark which outputs are discovery context versus standalone signals.

### 3. Signal Contracts

- Define only strong, implementation-worthy signal types.
- Keep broad collection results as enrichment unless corroboration rules are explicit.
