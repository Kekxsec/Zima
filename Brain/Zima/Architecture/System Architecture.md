---
tags: [zima, architecture]
created: 2026-03-21
---

# System Architecture

← [[../Zima|Zima Home]]

## Core Pipeline

```
providers → modules → signals → correlation → scoring → remediation → automation
```

Each stage has a single, strict responsibility:

| Stage | Role |
|---|---|
| **providers** | Fetch raw data from external APIs or local collectors. Auth, pagination, rate limits. Never assign severity. |
| **modules** | Interpret provider data. Map to security risks. Emit normalized signals. Never make HTTP calls. |
| **signals** | Atomic unit of security intelligence. Deduped, versioned, lifecycle-managed. |
| **correlation** | Combine signals into composite findings. Uses asset graph. No API calls — operates on stored signals only. |
| **scoring** | Quantify risk. Append-only rows with `scorer_version`. Recalculated after each scan. |
| **remediation** | Actionable step-by-step guidance with effort estimates. |
| **automation** | Execute approved fixes with audit log + rollback. Operational records, not signals. |

---

## Dependency Direction

> [!important] Non-negotiable rule
> All dependencies flow in one direction only. Lower layers never import higher layers.

```
core → db → auth → assets → signals → providers → modules
     → correlation → scoring → remediation → automation → api
```

Enforced by CI import checker — violations fail the build.

---

## Repository Structure

```
backend/app/
├── api/           ← routes, dependencies, auth
├── core/          ← config, logging, exceptions, enums
├── db/            ← session, migrations, repositories/
├── assets/        ← models, graph, linking
├── signals/       ← models, normalizer, dedup, registry
├── providers/     ← category/provider/ (client, auth, mapper)
├── modules/       ← domain/module/ (service, rules, mapper)
├── correlation/   ← engine, findings, rules/
├── scoring/       ← engine, calculators/, weights, policies
├── remediation/   ← engine, playbooks/, templates
├── automation/    ← engine, workflows/, approvals, audit
└── jobs/          ← scheduler, module_runner, alerts
```

---

## Asset Graph

Assets are real-world objects. Signals attach to assets. Correlation uses the graph to link signals across domains.

**Entity types:** `email`, `domain`, `account`, `device`, `browser`, `ip`, `certificate`, `secret`, `cloud_account`, `saas_app`, ...

**Example relationships:**
```
user → owns → email
user → logs_into → account
domain → resolves_to → ip
browser → has_extension → browser_extension
repository → contains → secret
```

---

## Signal Model

```json
{
  "signal_type": "mfa_missing",
  "entity_type": "account",
  "severity": "high",
  "confidence": "high",
  "source": "mfa_posture",
  "provider": "google_workspace",
  "summary": "MFA not enabled",
  "status": "open",
  "first_seen": "...",
  "last_seen": "..."
}
```

Severity values: `critical`, `high`, `medium`, `low`, `info`
Lifecycle: `open → resolved | suppressed | stale`

Signals use deterministic hash IDs — repeated scans upsert, never duplicate.

---

## Tier Configuration

Tiers are YAML config — they never alter pipeline code. Modules have no awareness of which tier activated them.

| Tier | Domains |
|---|---|
| Core | identity, accounts, device, browser |
| Plus | + network, privacy, darkweb, backup, threat_intel |
| Pro | + domain, email, infrastructure, secrets, supply_chain |
| Business | + cloud, saas, incident_readiness, compliance |

---

## Key Scores Produced

```
Identity Security Score       Account Security Score
Device Security Score         Browser Security Score
Network Security Score        Privacy Exposure Score
Threat Exposure Score         Cloud Security Score
Business Resilience Score     Cyber Hygiene Score
Zima Overall Security Score
```

---

## See Also

- [[Design Principles]] — non-negotiable rules
- [[Tech Stack]] — implementation choices
- `Zima/docs/Architecture/section-04-backend-architecture.md`
