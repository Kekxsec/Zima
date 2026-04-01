---
title: "prompt / cloud / defender_for_endpoint"
aliases: ["defender_for_endpoint", "defender for endpoint prompt", "defender_for_endpoint research prompt"]
tags: [zima, research, prompts, provider-research, cloud, defender_for_endpoint, graph_exclude]
type: provider_research_prompt
provider: defender_for_endpoint
provider_category: cloud
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

## Provider Under Research

- Provider name: defender_for_endpoint
- Provider category: cloud
- Provider website / API docs URL: https://learn.microsoft.com/microsoft-365/security/defender-endpoint
- Documentation / repo URL: Microsoft Defender for Endpoint API docs
- Target module(s) from my provider map: software_vulnerability, software_inventory
- Build priority / tier: 4 / Business
- Provider role: enrichment_provider
- Tool type: commercial_api
- Primary device use case: managed endpoint vulnerability and inventory data
- OS support: windows, macos, linux via onboarded agents
- Important provider-specific cautions:
  - Requires Defender for Endpoint licensing and onboarding.
  - API results depend on agent coverage and cloud-side assessment freshness.

## Research Instructions

- Use official Microsoft docs as primary sources.
- Document exposed entities, auth scopes, vulnerability and software inventory schemas, and refresh model.
- Treat this as managed-enterprise enrichment rather than base collection for unmanaged devices.
