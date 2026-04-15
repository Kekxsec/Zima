---
title: "prompt / cloud / jamf_pro_api"
aliases: ["jamf_pro_api", "jamf pro api prompt", "jamf_pro_api research prompt"]
tags: [zima, research, prompts, provider-research, cloud, jamf_pro_api, graph_exclude]
type: provider_research_prompt
provider: jamf_pro_api
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

- Provider name: jamf_pro_api
- Provider category: cloud
- Provider website / API docs URL: https://developer.jamf.com
- Documentation / repo URL: Jamf Pro API docs
- Target module(s) from my provider map: disk_encryption_check, software_inventory
- Build priority / tier: 4 / Business
- Provider role: enrichment_provider
- Tool type: mdm_or_edr_integration
- Primary device use case: managed mac inventory, FileVault, and app posture
- OS support: macos
- Important provider-specific cautions:
  - Enterprise-managed Macs only.
  - Confirm whether modern API coverage supersedes Classic API dependencies.

## Research Instructions

- Use official Jamf docs as primary sources.
- Document auth, inventory entities, FileVault/device fields, software inventory artifacts, and export format.
- Treat this as managed-environment enrichment rather than universal Mac device collection.
