---
title: "prompt / tools / huginn_muninn"
tags: [zima, research, providers, tools, huginn_muninn]
type: provider_research_prompt
provider: huginn_muninn
status: complete
---

# Research Prompt: Huginn-Muninn

Research Huginn-Muninn (https://github.com/Ringmast4r/Huginn-Muninn) as a device fingerprint reference database for Zima.

Focus on: 8 datasets (MAC vendors 10.1M, DHCP fingerprints 368K, device profiles 116K, protocol signatures 1.9K), SQLite schema, overlap with OUI-Master-Database, DHCP fingerprint unique value, update cadence, dataset size implications.

Classification target: enrichment_only
Module target: device_inventory (DHCP fingerprinting)
Note: Overlaps with OUI-Master-Database for MAC lookups. Unique value is DHCP fingerprint → device model identification.
