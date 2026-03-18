# Section 17–19 — Architecture Summary & Strategic Outcome

---

## 17. Final Architecture Summary

Zima is a modular cybersecurity engine where:

| Layer | Role |
|---|---|
| **providers** | Fetch raw data from external or local sources without making risk judgments |
| **modules** | Process provider data and emit standardized signals representing security findings |
| **signals** | Attach to assets in a graph, enabling cross-domain correlation |
| **correlation** | Combine multiple signals into higher-level, explainable risk findings |
| **scoring** | Quantify risk using weighted models and produce domain and overall security scores |
| **remediation** | Provide step-by-step instructions to fix issues, with estimated time and impact |
| **automation** | Execute remediation steps safely, with approvals and audit logging |
| **tiers** | Enable or disable module domains without changing the underlying architecture |
| **persistence** | Store signals, assets, findings, scores, and audit records via a repository layer backed by PostgreSQL or SQLite |

---

## 18. Strategic Outcome

By keeping modules decoupled from providers and isolating correlation, scoring, and remediation logic into their own layers, Zima can scale across:

```
individual user → advanced user → freelancer → micro-business
```

without rewriting the platform.

The domain model supports the full breadth of personal and small-business security:

- identity security
- account security
- device posture
- browser posture
- network hygiene
- domain and infrastructure monitoring
- privacy exposure
- dark web monitoring
- threat intelligence
- cloud and SaaS security
- secrets management
- supply chain security
- backups
- incident readiness
- compliance

---

## 19. One-Line Definition

> **Zima is a modular, tier-driven cybersecurity platform where providers gather data, modules convert it into normalized signals, correlation and scoring turn signals into measurable risk, remediation and automation transform risk into action, and tiers control which capabilities are enabled without altering the engine.**
