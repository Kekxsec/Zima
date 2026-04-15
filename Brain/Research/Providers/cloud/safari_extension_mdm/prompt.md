---
title: "prompt / cloud / safari_extension_mdm"
aliases: ["safari_extension_mdm", "safari extension mdm prompt", "safari_extension_mdm research prompt"]
tags: [zima, research, prompts, provider-research, cloud, safari_extension_mdm, graph_exclude]
type: provider_research_prompt
provider: safari_extension_mdm
provider_category: cloud
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

- Provider name: safari_extension_mdm
- Provider category: cloud
- Provider website / API docs URL: Apple MDM guides
- Documentation / repo URL: Safari extension configuration docs
- Target module(s) from my provider map: browser_configuration
- Build priority / tier: 4 / Business
- Provider role: enrichment_provider
- Tool type: browser_policy_source
- Primary browser use case: managed Safari extension allow/block controls
- Browser support: safari on macos and ios
- Important provider-specific cautions:
  - Requires supervised devices and MDM.
  - Policy-level control only; not a broad Safari extension inventory source.

## Research Instructions

- Use official Apple docs as primary sources.
- Document MDM profile payloads, policy keys, and which extension controls or Safari settings are actually enforceable.
- Treat as managed Apple-device enrichment, not general local browser collection.
