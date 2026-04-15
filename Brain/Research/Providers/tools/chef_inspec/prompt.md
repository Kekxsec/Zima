---
title: "prompt / tools / chef_inspec"
aliases: ["chef_inspec", "chef inspec prompt", "chef_inspec research prompt"]
tags: [zima, research, prompts, provider-research, tools, chef_inspec, graph_exclude]
type: provider_research_prompt
provider: chef_inspec
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

- Provider name: chef_inspec
- Provider category: tools
- Provider website / API docs URL: https://www.inspec.io
- Documentation / repo URL: https://github.com/inspec/inspec
- Target module(s) from my provider map: os_security, configuration
- Build priority / tier: 2 / Plus
- Provider role: local_tool_or_deferred
- Tool type: local_cli
- Primary device use case: compliance testing and host configuration auditing
- OS support: linux, macos, windows
- Important provider-specific cautions:
  - Test/profile driven model may be powerful but heavier to maintain.
  - Ruby/runtime and licensing constraints may matter.

## Research Instructions

- Use official docs as primary sources.
- Document profile model, JSON outputs, local and remote execution modes, and what controls translate well into Zima signals.
- Distinguish framework-driven assertions from raw system evidence.
