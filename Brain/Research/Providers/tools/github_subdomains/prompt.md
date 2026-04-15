---
title: "prompt / tools / github_subdomains"
aliases: ["github_subdomains", "github_subdomains prompt", "github_subdomains research prompt"]
tags: [zima, research, prompts, provider-research, tools, github_subdomains, graph_exclude]
type: provider_research_prompt
provider: github_subdomains
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

- Provider name: github_subdomains
- Provider category: tools
- Provider website / API docs URL: https://github.com/gwen001/github-subdomains
- Target module(s) from my provider map: unknown
- Build priority / tier: 4 / Business
- Provider role: local_tool_or_deferred
- Important provider-specific cautions:
  - Confirm how the tool queries GitHub and what authentication or rate limits apply.
  - Separate discovered assets from verified takeover or exposure findings.

## Research Instructions

- Use official repository docs as the primary source.
- Confirm CLI usage, token needs, output files, and deduplication behavior.
- Separate direct signal input from enrichment-only, utility-only, and out-of-scope usage.
- Do not treat discovered subdomains as risky without supporting evidence.

## Tasks

### 1. Tool Surface Appendix

- Document commands, flags, output artifacts, and execution requirements.
- Capture supported entity types and machine-readable formats.

### 2. Module Mapping

- Decide where GitHub-derived asset discovery fits within Zima.
- Mark whether this should seed downstream probes rather than emit standalone signals.

### 3. Signal Contracts

- Define direct signals only if the tool produces evidence beyond raw asset discovery.
- Otherwise classify it as enrichment or utility-only.
