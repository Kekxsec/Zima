---
title: "prompt / cloud / chrome_management_api"
aliases: ["chrome_management_api", "chrome management api prompt", "chrome_management_api research prompt"]
tags: [zima, research, prompts, provider-research, cloud, chrome_management_api, graph_exclude]
type: provider_research_prompt
provider: chrome_management_api
provider_category: cloud
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: chrome_management_api
- Provider category: cloud
- Provider website / API docs URL: https://developers.google.com
- Documentation / repo URL: Chrome Management API docs
- Target module(s) from my provider map: extension_risk, browser_configuration
- Build priority / tier: 4 / Business
- Provider role: enrichment_provider
- Tool type: commercial_api
- Primary browser use case: managed Chrome inventory and enterprise browser state
- Browser support: chrome enterprise
- Important provider-specific cautions:
  - Requires Google Workspace admin access and managed Chrome environments.
  - Chrome-only and enterprise-only.

## Research Instructions

- Use official Google docs as primary sources.
- Document auth scopes, device/browser inventory objects, extension list support, and policy-related fields.
- Treat as managed-enterprise enrichment, not general browser collection.
