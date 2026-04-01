---
title: "prompt / cloud / firefox_addons_site_api"
aliases: ["firefox_addons_site_api", "firefox_addons_site_api prompt", "firefox_addons_site_api research prompt"]
tags: [zima, research, prompts, provider-research, cloud, firefox_addons_site_api, graph_exclude]
type: provider_research_prompt
provider: firefox_addons_site_api
provider_category: cloud
obsidianUIMode: preview
---
Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic API summary.

## Provider Under Research

- Provider name: firefox_addons_site_api
- Provider category: cloud
- Provider website / API docs URL: Mozilla Add-ons site
- Documentation / repo URL: Mozilla Add-ons developer references or maintained source materials
- Target module(s) from my provider map: extension_risk, browser_inventory
- Build priority / tier: 3 / Pro
- Provider role: enrichment_only
- Tool type: extension_metadata_source
- Primary browser use case: remote lookup of Firefox add-on metadata for extension enrichment
- Browser support: firefox
- Important provider-specific cautions:
  - Validate whether there is an official supported API or only site-level JSON/HTML access.
  - Treat this as metadata enrichment, not local browser inventory.

## Research Instructions

- Determine whether Firefox add-on metadata is available via official API, embedded JSON, or unsupported scraping paths.
- Document fields available, stability, access model, and whether permission or review data can be normalized.
- Be explicit about maintenance risk if access relies on undocumented endpoints.

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
