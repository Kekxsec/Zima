---
title: "prompt / tools / tlsx"
aliases: ["tlsx", "tlsx prompt", "tlsx research prompt"]
tags: [zima, research, prompts, provider-research, tools, tlsx, graph_exclude]
type: provider_research_prompt
provider: tlsx
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

- Provider name: tlsx
- Provider category: tools
- Provider website / API docs URL: https://github.com/projectdiscovery/tlsx
- Target module(s) from my provider map: unknown
- Build priority / tier: 4 / Business
- Provider role: local_tool_or_deferred
- Important provider-specific cautions:
  - Confirm certificate, TLS, and fingerprint outputs that are stable enough to parse.
  - Separate metadata collection from misconfiguration or risk findings.

## Research Instructions

- Use official repository docs as the primary source.
- Confirm commands, supported protocols, fingerprints, checks, and JSON output fields.
- Separate direct signal input from enrichment-only, utility-only, and out-of-scope usage.
- Do not overstate risk from generic TLS metadata alone.

## Tasks

### 1. Tool Surface Appendix

- Document commands, flags, output fields, and execution requirements.
- Capture supported entity types and machine-readable formats.

### 2. Module Mapping

- Decide where certificate metadata, TLS versions, and fingerprints fit in Zima.
- Mark which outputs should trigger correlation rather than direct alerting.

### 3. Signal Contracts

- Define only security-relevant signal types supported by documented evidence fields.
- Keep passive certificate metadata separate from confirmed misconfigurations.
