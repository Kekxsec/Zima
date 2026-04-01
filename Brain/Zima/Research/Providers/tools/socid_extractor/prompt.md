---
title: "prompt / tools / socid_extractor"
tags: [zima, research, providers, tools, socid_extractor]
type: provider_research_prompt
provider: socid_extractor
status: complete
---

# Research Prompt: socid_extractor

Research the socid-extractor tool (https://github.com/soxoj/socid-extractor) as a profile enrichment provider for Zima.

Focus on:
1. CLI interface and Python library API surface
2. Complete list of supported platforms and extraction methods
3. Output schema — all extractable fields and their presence rules per platform
4. How it integrates with maigret (pipeline: maigret finds accounts → socid-extractor enriches each profile URL)
5. Platform UID fields (gaia_id, uid, etc.) and their value for cross-service identity correlation
6. Failure modes (bot detection, stale extractors, missing fields)
7. License implications (GPL-3.0)
8. Rate limit and throttling considerations

Classification target: enrichment_only
Module target: username_exposure, account_inventory
