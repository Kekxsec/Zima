---
title: "prompt / tools / syft"
aliases: ["syft", "syft prompt", "syft research prompt"]
tags: [zima, research, prompts, provider-research, tools, syft, graph_exclude]
type: provider_research_prompt
provider: syft
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

- Provider name: syft
- Provider category: tools
- Provider website / API docs URL: https://anchore.com
- Documentation / repo URL: https://github.com/anchore/syft
- Target module(s) from my provider map: software_inventory
- Build priority / tier: 3 / Pro
- Provider role: local_tool_or_deferred
- Tool type: inventory_collector
- Primary device use case: SBOM and package inventory generation
- OS support: linux, macos, windows
- Important provider-specific cautions:
  - Very broad filesystem scans may need filtering to be useful for endpoint inventory.
  - Inventory output is utility-heavy unless paired with vulnerability or posture logic.

## Research Instructions

- Use official docs as primary sources.
- Document SBOM formats, package sources, filesystem scan behavior, and structured output fields.
- Focus on how Zima could reuse Syft for normalized software inventory.

---

## Tasks

Apply the full workflow in [[../../../provider-research-protocol|Provider Research Protocol]].

## Required Output

Minimum required deliverables for this provider:

- API or tool surface appendix
- module mapping table
- signal contract table
- confidence guidance table
- provider summary
- structured JSON output

If this prompt is used outside Obsidian, include the contents of `Research/provider-research-protocol.md` alongside this prompt before running the research task.
