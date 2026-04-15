← [[../Zima|Home]] · [[section-02-design-principles|§2 Design Principles →]]

# Section 1 — Overview

## Modular Cybersecurity Platform (Personal → Small Business)

Zima is a **modular cybersecurity platform** built to:

- assess cyber risk
- monitor exposure across identities, accounts, devices, networks, domains, cloud and SaaS services
- provide clear remediation guidance and, where possible, automate fixes
- support both individuals and small businesses via a tier-based model

---

## Core Pipeline

The core pipeline follows this sequence:

```
providers → modules → signals → correlation → scoring → remediation → automation
```

Each stage performs a distinct role:

| Stage | Role |
|---|---|
| **providers** | Gather raw data from external APIs or local collectors |
| **modules** | Interpret that data into normalized security signals |
| **signals** | The atomic unit of security intelligence |
| **correlation** | Combine multiple signals into higher-level composite risks |
| **scoring** | Quantify risk numerically or categorically |
| **remediation** | Translate risk into actionable, prioritized steps |
| **automation** | Implement those steps safely, with approval and audit |

---

## Tier Model

```
Core → Plus → Pro → Business
```

Tiers control which modules are enabled, which signals and scores are surfaced, and which automation tasks are available. They never alter the core architecture or pipeline. The same engine runs at every tier.

| Tier | Target User |
|---|---|
| Core | Individuals: essential identity, account, device, browser hygiene |
| Plus | Advanced users: adds network, privacy, dark web, backup, threat intel |
| Pro | Freelancers and technical users: adds domain, email, infrastructure, secrets, supply chain |
| Business | Small businesses: adds cloud, SaaS, incident readiness, compliance |

---

## Domain Coverage

The platform supports monitoring and assessment across:

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

## Strategic Scope

Zima is designed to scale across:

```
individual user → advanced user → freelancer → micro-business
```

without rewriting the platform. The same codebase, the same pipeline, and the same signal model serve every tier.

---

**See also:** [[section-02-design-principles|§2 Design Principles]] · [[section-20-domain-breakdown|§20 All Domains]] · [[section-09-execution-flow|§9 Execution Flow]] · [[../Business/Business Model|Business Model]]
