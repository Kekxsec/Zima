---
tags: [zima, moc, project]
created: 2026-03-21
updated: 2026-03-21
---

# Zima

> Modular cybersecurity platform — assess risk, monitor exposure, provide remediation.

**One-liner:** Security report card for individuals, freelancers, and small businesses.
**Target:** £500/month MRR → £5K+ · 50 customers × £10/month
**Stack:** Python 3.12 · FastAPI · PostgreSQL · Redis · Railway

---

## Status

| Area | Status |
|---|---|
| Stages 0–5 (scaffold → correlation/scoring/remediation) | ✅ Complete — 17/17 tests pass |
| Stages 6–8 (jobs/API, GDPR/billing, hardening) | 🔲 Not started |
| mypy / ruff / import checker | ✅ Clean |
| Signal registry research | 🔄 In progress |

**Next:** Complete signal registry handoff → begin Stage 6

---

## Navigation

### Product & Vision
- [[Architecture/section-01-overview|§1 Platform Overview]] — what Zima is, strategic scope, full product vision
- [[Architecture/section-20-domain-breakdown|§20 Domain Breakdown]] — all security domains, modules, and signals
- [[Architecture/Design Principles]] — non-negotiable rules (10-point summary)

### Business
- [[Business/Business Model]] — tiers, pricing, unit economics, risks
- [[Business/Market & GTM]] — personas, launch sequence, conversion funnel, KPIs
- [[Business/threat-model]] — threat actors, attack vectors, mitigations

### Build
- [[MVP Master]] — all stages 0–10, current status, key decisions log
- [[MVP Build/stage-10-16-implementation-plan|Stage 10–16 Implementation Plan]] — current provider scope and implementation stages
- [[MVP Build/pre-stage-06-signal-registry-handoff|Pre-Stage-6 Handoff]] — research synthesis and implementation bridge before Stage 6
- [[MVP Build/mvp-completion-review-2026-04-01|MVP Completion Review]] — code-vs-plan review (2026-04-01)

### Architecture
- [[Architecture/System Architecture]] — pipeline, layers, asset graph
- [[Architecture/Tech Stack]] — stack choices and key decisions
- [[Architecture/CLAUDE-CODE-BRIEFING]] — ⭐ canonical code patterns, exact implementations, verification commands
- [[Architecture/section-02-design-principles|§2–§16 Full Architecture Sections]] — all 16 source sections

### Research & Extension
- [[Research/research|Research]] — provider research workspace, provider hubs, and signal registry notes
- [[Research/launch-research-dashboard|Launch Research Dashboard]] — what to do next, provider waves, and execution order
- [[Research/Security Pillars/personal_core_security|Personal/Core Security]] — identity, accounts, device, browser
- [[Research/Security Pillars/exposure_attack_surface|Exposure and Attack Surface]] — network, domain, email, infrastructure, privacy, darkweb, threat_intel
- [[Research/Security Pillars/business_operational_security|Business and Operational Security]] — cloud, saas, secrets, supply_chain, backup, incident_readiness, compliance
- [[Extending the Platform]] — how to add providers, modules, correlation rules
- [[Provider Module Map]] — all 150+ providers mapped to module domains
- [[Provider Schemas]] — universal schema + per-category output tables
- [[Signal Research Guide]] — signal design, severity framework, research phases

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
