---
title: "prompt / tools / firefox_enterprise_policies"
aliases: ["firefox_enterprise_policies", "firefox enterprise policies prompt", "firefox_enterprise_policies research prompt"]
tags: [zima, research, prompts, provider-research, tools, firefox_enterprise_policies, graph_exclude]
type: provider_research_prompt
provider: firefox_enterprise_policies
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic tool summary.

## Provider Under Research

- Provider name: firefox_enterprise_policies
- Provider category: tools
- Provider website / API docs URL: Mozilla policy templates
- Documentation / repo URL: Firefox Policy List
- Target module(s) from my provider map: browser_configuration
- Build priority / tier: 2 / Plus
- Provider role: local_tool_or_deferred
- Tool type: browser_policy_source
- Primary browser use case: inspect enforced Firefox browser policies for tracking, cookies, updates, and extension controls
- Browser support: firefox
- Important provider-specific cautions:
  - Policy files may not exist on unmanaged endpoints.
  - File locations and registry use vary by OS.

## Research Instructions

- Use official Mozilla docs as primary sources.
- Document policy file/registry locations, key policy settings, and which settings map to concrete browser posture signals.
- Prefer direct configuration evidence over general admin guidance.

---

## Tasks

Apply the full workflow in [[../../../../provider-research-protocol|Provider Research Protocol]].

## Required Output

Minimum required deliverables for this provider:

- API or tool surface appendix
- module mapping table
- signal contract table
- confidence guidance table
- provider summary
- structured JSON output

If this prompt is used outside Obsidian, include the contents of `Research/provider-research-protocol.md` alongside this prompt before running the research task.
