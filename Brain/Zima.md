---
tags: [zima, moc, project]
aliases: [Zima Home, Zima MOC]
created: 2026-03-21
updated: 2026-04-17
verified: 2026-04-15

---

# Zima

> Modular cybersecurity platform — assess risk, monitor exposure, provide remediation.

**One-liner:** Security report card for individuals, freelancers, and small businesses.
**Target:** £500/month MRR → £5K+ · 50 customers × £10/month
**Stack:** Python 3.12 · FastAPI · PostgreSQL · Redis · Railway · Rust (companion)

---

## Status

| Stage | Area | Status |
|---|---|---|
| 00–05 | Scaffold → Correlation / Scoring / Remediation | ✅ Complete — 17/17 tests pass |
| 06 | Jobs, API, Orchestration | ✅ Complete |
| 06b | Breach Alerts & Stale Scans | ✅ Complete |
| 07 | GDPR & Billing | ✅ Complete |
| 08 | Pre-Launch Hardening | 🔴 Open — infra/ops items only (HTTPS, Sentry, ICO) |
| 09 | Execution Policy & Security Hardening | ✅ Complete |
| 10a | P0 Breach Provider Schemas & Mappers | ✅ Complete (2026-04-09) |
| 10b | Reputation / Social Provider Schemas & Mappers | ✅ Complete (2026-04-09) |
| 10c | IntelX Full Client + Schema/Mapper | ✅ Complete (2026-04-15) — schema/mapper verified |
| 10d | Subprocess Tools (Mailcat, WhatsmyName) | ✅ Complete (2026-04-15) — schemas/mappers verified |
| 11 | Identity Module Signal Rules | ✅ Complete (2026-04-15) — launch-scope module tests added |
| 12 | Device Pillar | ✅ Complete (2026-04-15) — 40 unit tests passing |
| 13 | Browser Pillar | 🔄 All provider clients + module services implemented — tests gap |
| 14 | File Upload Parsers | ✅ Complete (2026-04-15) — streamed upload path, file-based mbox parsing, PM exporter verification, newsletter filtering, alias actions |
| 15 | Infrastructure Providers | ✅ Complete (2026-04-15) — LeakIX + Frankenstein schemas/mappers added |
| 16 | Integration Wiring & Cleanup | ✅ Complete (2026-04-15) — epieos removed, ProviderFinding audit clean, orchestrator policy gate added, e2e pillar tests passing |
| 17 | Zima Companion (Rust binary, Phase 1) | ✅ Complete |
| AI | Ollama Local AI Provider | ✅ Complete (2026-04-17) — mapper, client methods, status endpoint, 26 tests passing |

**Next active work:** Ollama provider completion (mapper, health_check, list_models, structured_query) + status endpoint + tests. Then Stage 08 deploy-time hardening.

---

## Navigation

### Product & Vision
- [[Architecture/section-01-overview|§1 Platform Overview]] — what Zima is, strategic scope, full product vision
- [[Architecture/section-20-domain-breakdown|§20 Domain Breakdown]] — all security domains, modules, and signals
- [[Architecture/Design Principles]] — non-negotiable rules summary

### Business
- [[Business/Business Model]] — tiers, pricing, unit economics, risks
- [[Business/Market & GTM]] — personas, launch sequence, conversion funnel, KPIs
- [[Business/threat-model]] — threat actors, attack vectors, mitigations

### Build
- [[Archive/MVP Build 2026/MVP Master|MVP Stage History]] — stages 00–09, key decisions log
- [[MVP Build/stage-10-16-implementation-plan|Stage 10–16 Provider Scope]] — full provider and module spec with current statuses
- [[Archive/MVP Build 2026/mvp-completion-review-2026-04-01|MVP Completion Review (2026-04-01)]] — code-vs-plan verification
- [[next-steps-to-launch]] — ⭐ single source of truth for what must be done before launch
- [[MVP Build/stage-08-pre-launch-hardening|Stage 08 Checklist]] — launch gate, open infra items

### Architecture
- [[Architecture/CLAUDE-CODE-BRIEFING]] — vault mirror note for the canonical implementation briefing in `.claude/CLAUDE-CODE-BRIEFING.md`
- [[Architecture/section-02-design-principles|§2 Design Principles]] — non-negotiable rules
- [[Architecture/section-04-backend-architecture|§4 Backend Architecture]]
- [[Architecture/section-05-provider-architecture|§5 Provider Architecture]]
- [[Architecture/section-06-module-architecture|§6 Module Architecture]]

### Research & Extension
- [[Research/research|Research Hub]] — execution dashboards, schemas, protocol, provider hubs
- [[Research/Provider Module Map]] — all 150+ providers mapped to module domains
- [[Research/Provider Schemas]] — universal schema + per-category output tables
- [[Research/Extending the Platform]] — how to add providers, modules, correlation rules
- [[Launch Plan/_index|Launch Plan]] — provider launch wave ordering and active shortlist

### Companion
- [[Companion/architecture|Companion Architecture]]
- [[Companion/building|Companion Build & Release]]
- [[Companion/baselines|Companion Browser Baselines]]

### Implementation Deep Dives
- [[MVP Build/email-account-identifier/phase-01-models-and-repositories|Email Account Identifier — Phase 1]]
- [[MVP Build/email-account-identifier/phase-02-mbox-parser-provider|Email Account Identifier — Phase 2]]
- [[MVP Build/email-account-identifier/phase-03-service-discovery|Email Account Identifier — Phase 3]]
- [[MVP Build/email-account-identifier/phase-04-module-and-background-task|Email Account Identifier — Phase 4]]
- [[MVP Build/email-account-identifier/phase-05-api-endpoints|Email Account Identifier — Phase 5]]
- [[MVP Build/email-account-identifier/phase-06-tests|Email Account Identifier — Phase 6]]

---

## Core Pipeline

```
providers → modules → signals → correlation → scoring → remediation → automation
```

Providers answer *how do I get the data?* — Modules answer *what does it mean?*
Dependency direction is one-way and enforced by CI.

---

## Tier Model

| Tier | Users | Domains |
|---|---|---|
| Core | Individuals | identity, accounts, device, browser |
| Plus | Advanced users | + network, privacy, darkweb, backup, threat_intel |
| Pro | Freelancers | + domain, email, infrastructure, secrets, supply_chain |
| Business | Small businesses | + cloud, saas, incident_readiness, compliance |

Tiers are configuration only — the same engine runs at every tier.
