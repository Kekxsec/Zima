---
title: "prompt / tools / prowler"
aliases: ["prowler", "prowler prompt", "prowler research prompt"]
tags: [zima, research, prompts, provider-research, tools, prowler, graph_exclude]
type: provider_research_prompt
provider: prowler
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

- Provider name: prowler
- Provider category: tools
- Provider website / API docs URL: https://github.com/prowler-cloud/prowler
- Target module(s) from my provider map: unknown
- Build priority / tier: 4 / Business
- Provider role: local_tool_or_deferred
- Important provider-specific cautions:
  - Confirm which clouds and SaaS providers are supported and which outputs are stable.
  - Separate audit findings from raw inventory or compliance metadata.

## Research Instructions

- Use official repository docs as the primary source.
- Confirm supported providers, auth model, report formats, and finding schemas.
- Separate direct signal input from enrichment-only, utility-only, and out-of-scope usage.
- Map provider-native severities carefully instead of inheriting them blindly.

## Tasks

### 1. Tool Surface Appendix

- Document commands, checks, report formats, and execution requirements.
- Capture supported entity types, evidence fields, and machine-readable outputs.

### 2. Module Mapping

- Decide which Zima cloud or SaaS modules can consume Prowler output directly.
- Separate posture findings from inventory-only data.

### 3. Signal Contracts

- Define implementation-grade signal types based on documented finding fields.
- Note how severity, remediation, and evidence should be normalized.
