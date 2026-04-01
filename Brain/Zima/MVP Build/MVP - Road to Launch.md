---
tags: [zima, mvp, roadmap, expansion]
created: 2026-03-21
---

← [[../Zima|Zima]]

# Expansion Path

What comes after Stage 8 is complete and the first real user signs up.

---

## Immediate Post-Launch Sequence

```
Stage 8 complete + first real user signed up
  ↓
mfa_posture module (accounts domain)
  ↓
LeakCheck provider (Pattern B — second breach source, same module)
  ↓
Second correlation rule: breach + MFA missing → account_takeover_risk
  ↓
Dark web monitoring module
  ↓
Minimal Next.js frontend (score dashboard, findings, remediation tasks)
  ↓
Public launch: Product Hunt, Reddit, SEO
```

Each new module follows Stages 4 and 5 exactly. The pattern is fully established.

---

## Adding a New Module — Pattern

```
provider (fetch only)
  → module (severity + SignalCreate)
  → correlation rule
  → score calculator
  → remediation playbook entry
```

---

## Domain Expansion by Tier

### Core (all users at launch)
- identity ✅ (breach_monitor built)
- accounts (mfa_posture — next up)
- device
- browser

### Plus (add to Plus tier)
- network
- privacy
- darkweb
- backup
- threat_intel

### Pro (freelancers)
- domain
- email
- infrastructure
- secrets
- supply_chain

### Business (small businesses)
- cloud
- saas
- incident_readiness
- compliance

---

## Signal Registry (In Progress)

Before expanding providers, the signal registry must be finalized:
- First-pass built from SpiderFoot `STRIPPED` comment harvest
- ~60 providers return pure INFO (context/enrichment only)
- Five providers with conditional severity logic to preserve: `breachdirectory`, `greynoise`, `virustotal`, `threatjammer`, `honeypot`
- Next: verify API schemas for major providers via Perplexity → bring back to Claude to finalize rows
- Output: `signal-registry.md` — one row per (provider, signal_type) pair

---

## See Also

- [[MVP Master]] — current build status
- [[../Business/Business Model]] — tier pricing and revenue model
