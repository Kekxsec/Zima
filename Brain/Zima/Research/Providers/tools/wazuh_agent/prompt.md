---
title: "prompt / tools / wazuh_agent"
aliases: ["wazuh_agent", "wazuh agent prompt", "wazuh_agent research prompt"]
tags: [zima, research, prompts, provider-research, tools, wazuh_agent, graph_exclude]
type: provider_research_prompt
provider: wazuh_agent
provider_category: tools
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic tool summary.

## Provider Under Research

- Provider name: wazuh_agent
- Provider category: tools
- Provider website / API docs URL: https://wazuh.com
- Documentation / repo URL: https://documentation.wazuh.com
- Target module(s) from my provider map: os_security, software_vulnerability, software_inventory, browser_inventory, extension_risk
- Build priority / tier: 4 / Business
- Provider role: local_tool_or_deferred
- Tool type: endpoint_agent
- Primary device/browser use case: host monitoring, inventory, vulnerability detection, and agent-side browser extension inventory
- OS support: windows, macos, linux
- Important provider-specific cautions:
  - Heavy deployment model with manager/server dependencies.
  - Browser-extension coverage appears tied to agent-side inventory logic rather than a lightweight local collector.
  - Separate local agent data from manager-side correlation and alerting.

## Research Instructions

- Use official docs as primary sources.
- Document agent install requirements, manager dependencies, inventory schema, browser-extension collection model, vuln detection model, and machine-readable exports.
- Be explicit about what Zima could reuse versus what is overkill for an SMB/local-agent product direction.
