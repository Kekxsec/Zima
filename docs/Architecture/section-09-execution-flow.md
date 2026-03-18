# Section 9 — Execution Flow

At runtime, Zima orchestrates providers and modules via the job scheduler. The sequence is the same for every tier — only the set of enabled module domains changes.

---

## Runtime Sequence

```
scheduler
  → module_runner (respects tier config)
    → module service
      → provider client(s) fetch data
      → module mapper normalizes provider data
      → module rules.py evaluates and emits signals
  → signals stored in db and linked to asset graph
  → correlation engine evaluates rules against new signals
    → composite Findings produced where rule conditions are met
  → scoring engine recalculates domain and overall scores
  → remediation engine maps open signals and findings to playbooks
  → alerts and notification manager surfaces new findings to user
  → (optional) automation engine triggers approved fix workflows
```

---

## Scheduling Cadence

Different module domains run at different frequencies depending on the nature of the data:

| Domain | Example cadence |
|---|---|
| identity (breach) | Daily |
| accounts (MFA posture) | Daily |
| device | On agent checkin or daily |
| network | On-demand or daily |
| domain / DNS | Every 6–12 hours |
| threat intelligence | Every 1–6 hours |
| dark web | Daily |
| cloud / SaaS | Daily |

Cadences are configurable per module domain in `jobs/scheduler.py`.
