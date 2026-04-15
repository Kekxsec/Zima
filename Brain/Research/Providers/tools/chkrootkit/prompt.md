---
title: "prompt / tools / chkrootkit"
aliases: ["chkrootkit", "chkrootkit prompt", "chkrootkit research prompt"]
tags: [zima, research, prompts, provider-research, tools, chkrootkit, graph_exclude]
type: provider_research_prompt
provider: chkrootkit
provider_category: tools
obsidianUIMode: preview
kind: artifact
status: not_started
llm_include: false
code_scope: backend
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic tool summary.

## Provider Under Research

- Provider name: chkrootkit
- Provider category: tools
- Provider website / API docs URL: http://www.chkrootkit.org
- Documentation / repo URL: official site and README
- Target module(s) from my provider map: malware_scan
- Build priority / tier: 3 / Pro
- Provider role: direct_signal_input
- Tool type: rootkit_scanner
- Primary device use case: detect known rootkits and suspicious hidden processes on Unix-like systems
- OS support: linux, bsd, solaris, macos
- Important provider-specific cautions:
  - Signature-style detections can produce false positives and stale findings.
  - Treat this as one evidence source rather than a high-confidence malware verdict.

## Research Instructions

- Use official project materials as primary references.
- Document scan coverage, update cadence, privilege requirements, output structure, and common false-positive patterns.
- Be explicit about where this is useful for lightweight individual scanning versus where it is too noisy.
