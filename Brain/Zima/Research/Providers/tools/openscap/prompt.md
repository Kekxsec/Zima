---
title: "prompt / tools / openscap"
aliases: ["openscap", "openscap prompt", "openscap research prompt"]
tags: [zima, research, prompts, provider-research, tools, openscap, graph_exclude]
type: provider_research_prompt
provider: openscap
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic tool summary.

## Provider Under Research

- Provider name: openscap
- Provider category: tools
- Provider website / API docs URL: https://www.open-scap.org
- Documentation / repo URL: https://www.open-scap.org/tools/openscap-base
- Target module(s) from my provider map: os_security, patch_status
- Build priority / tier: 2 / Plus
- Provider role: local_tool_or_deferred
- Tool type: vulnerability_scanner
- Primary device use case: SCAP-based compliance and vulnerability scanning
- OS support: linux
- Important provider-specific cautions:
  - Linux-only, XML-heavy, and comparatively heavy-weight.
  - Strong for compliance-style posture, weaker for lightweight cross-platform endpoint collection.

## Research Instructions

- Use official docs as primary sources.
- Document scan profiles, result formats, privilege needs, and what device posture evidence is directly available.
- Be explicit about normalization difficulty and Linux-only scope.
