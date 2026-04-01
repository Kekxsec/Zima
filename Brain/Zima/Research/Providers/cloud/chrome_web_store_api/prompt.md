---
title: "prompt / cloud / chrome_web_store_api"
aliases: ["chrome_web_store_api", "chrome_web_store_api prompt", "chrome_web_store_api research prompt"]
tags: [zima, research, prompts, provider-research, cloud, chrome_web_store_api, graph_exclude]
type: provider_research_prompt
provider: chrome_web_store_api
provider_category: cloud
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic API summary.

## Provider Under Research

- Provider name: chrome_web_store_api
- Provider category: cloud
- Provider website / API docs URL: Chrome Web Store / related API surface
- Documentation / repo URL: chrome-webstore-api package or equivalent maintained source
- Target module(s) from my provider map: extension_risk, browser_inventory
- Build priority / tier: 2 / Plus
- Provider role: enrichment_only
- Tool type: extension_metadata_source
- Primary browser use case: remote lookup of Chrome extension metadata for inventory enrichment
- Browser support: chrome
- Important provider-specific cautions:
  - Validate whether this is official, unofficial, or package-wrapped access to Chrome Web Store metadata.
  - Metadata enrichment is not the same as local extension detection.

## Research Instructions

- Determine whether the API path is official, semi-official, or package-mediated.
- Document required credentials, metadata fields, output schema, rate limits, and whether extension permissions, category, and publisher data are reliably available.
- Be explicit about where this helps Zima and where it introduces dependency risk.

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
