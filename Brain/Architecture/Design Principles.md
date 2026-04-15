---
tags: [zima, architecture, canonical, summary]
created: 2026-04-14
updated: 2026-04-14
---

# Design Principles

Short summary note for vault navigation. The full document is [[section-02-design-principles|Section 2 — Core Design Principles]].

## Non-Negotiables

1. Providers fetch and normalize data. Modules interpret it.
2. Dependency flow is one-way from lower-level infrastructure toward the API.
3. Tiers are configuration, not module logic.
4. Scoring and automation are top-level backend layers, not module domains.
5. Keep implementation details aligned with the canonical briefing in [[CLAUDE-CODE-BRIEFING]].

## Read Next

- [[section-02-design-principles|Full design principles]]
- [[section-10-dependency-flow|Dependency flow]]
- [[section-11-development-rules|Development rules]]
