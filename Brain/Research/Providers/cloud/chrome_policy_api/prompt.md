---
title: "prompt / cloud / chrome_policy_api"
aliases: ["chrome_policy_api", "chrome policy api prompt", "chrome_policy_api research prompt"]
tags: [zima, research, prompts, provider-research, cloud, chrome_policy_api, graph_exclude]
type: provider_research_prompt
provider: chrome_policy_api
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

- Provider name: chrome_policy_api
- Provider category: cloud
- Provider website / API docs URL: https://developers.google.com
- Documentation / repo URL: Chrome Policy API docs
- Target module(s) from my provider map: browser_configuration
- Build priority / tier: 4 / Business
- Provider role: enrichment_provider
- Tool type: commercial_api
- Primary browser use case: managed Chrome enterprise policy retrieval
- Browser support: chrome enterprise
- Important provider-specific cautions:
  - Requires Google admin/OAuth setup.
  - Only covers managed policy state, not unmanaged local browser state.

## Research Instructions

- Use official Google docs as primary sources.
- Document policy retrieval endpoints, auth scopes, key browser policy objects, and JSON structure.
- Focus on settings relevant to extensions, cookies, safe browsing, tracking, and browser hardening.
