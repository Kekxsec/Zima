← [[../Zima|Home]] · [[section-02-design-principles|← §2 Design Principles]] · [[section-04-backend-architecture|§4 Backend Architecture →]]

# Section 3 — Repository Structure

The project uses a monorepo layout. The `backend/app` directory houses the server logic, security modules, providers, and orchestration engines. The `frontend` contains the user interface. Documentation lives in `docs/`. A `tests` directory contains unit, integration, contract, and system tests.

```text
zima/
├── backend/
│   └── app/
│       ├── api/
│       ├── core/
│       ├── assets/
│       ├── signals/
│       ├── providers/
│       ├── modules/
│       ├── correlation/
│       ├── scoring/
│       ├── remediation/
│       ├── automation/
│       ├── tiers/
│       ├── jobs/
│       └── db/
├── frontend/
├── docs/
├── tests/
├── scripts/
├── infra/
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## Top-Level Responsibilities

| Directory | Responsibility |
|---|---|
| `backend/app/api/` | REST endpoints for triggering scans, retrieving findings, updating settings, and scheduling jobs |
| `backend/app/core/` | Shared utilities: configuration, logging, enums, exceptions, helpers |
| `backend/app/assets/` | Entity graph models and services — emails, domains, accounts, devices, cloud accounts, SaaS apps |
| `backend/app/signals/` | Signal definitions, schemas, normalization, deduplication, lifecycle management |
| `backend/app/providers/` | Source adapters organized by category |
| `backend/app/modules/` | Security capabilities grouped by domain |
| `backend/app/correlation/` | Rules for combining signals into higher-level composite findings |
| `backend/app/scoring/` | Scoring engine, calculators, weights, and policies |
| `backend/app/remediation/` | Engine for mapping signals and findings to remediation instructions |
| `backend/app/automation/` | Orchestration of safe, auditable remediation workflows |
| `backend/app/tiers/` | YAML or JSON definitions enumerating which module domains are enabled per plan |
| `backend/app/jobs/` | Job scheduler and workers for background scanning and async tasks |
| `backend/app/db/` | Database models, migrations, session management, and repository layer |
| `frontend/` | Dashboard, onboarding, findings UI, remediation UI, settings, tier gating |
| `docs/` | Architecture docs, provider docs, module docs, playbooks, scoring definitions, runbooks |
| `tests/` | Cross-cutting tests, end-to-end tests, shared fixtures |
| `scripts/` | Developer utilities, migrations, helpers, smoke test wrappers |
| `infra/` | Deployment config, CI/CD, containers, observability setup, environment bootstrapping |

This structure supports strong modularity: each concern lives in its own layer and communicates via well-defined interfaces.
