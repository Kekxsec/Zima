← [[../Zima|Home]] · [[section-03-repository-structure|← §3 Repo Structure]] · [[section-05-provider-architecture|§5 Provider Architecture →]]

# Section 4 — Backend Architecture

---

## 4.1 API Layer

The API exposes endpoints for all external interactions.

```text
backend/app/api/
├── router.py
├── dependencies.py
└── v1/
    ├── findings.py
    ├── assets.py
    ├── scores.py
    ├── modules.py
    └── remediation.py
```

**Responsibilities:**

- accept user requests such as triggering scans, configuring tiers, and fetching scores and findings
- authenticate and authorize all calls
- translate user actions into internal jobs or queries
- return structured JSON responses

**Authentication:**

The API uses **JWT (JSON Web Tokens)** for authentication. Tokens are issued at login, carry tier and user context, and are validated on every request. API keys are used for programmatic access by integrations or automation scripts. All authentication logic lives in `api/dependencies.py` and is applied via FastAPI dependency injection. Tokens must be short-lived and rotated; refresh token handling is the responsibility of the auth flow, not individual endpoints.

---

## 4.2 Core Utilities

Shared functions and configuration live in `core/`.

```text
backend/app/core/
├── config/
├── settings.py
├── logging.py
├── exceptions.py
├── enums.py
└── utils.py
```

These modules provide global settings, logging configuration, custom exceptions, reusable enums, and helper functions. `core/` must not import from any higher layer. All other layers may import from `core/`.

---

## 4.3 Persistence Layer

Zima requires a persistence layer for storing signals, assets, findings, scores, and audit logs. This lives in `db/`.

```text
backend/app/db/
├── base.py
├── session.py
├── migrations/
└── repositories/
    ├── signals.py
    ├── assets.py
    ├── findings.py
    ├── scores.py
    └── audit.py
```

**Database:**

- **Primary store:** PostgreSQL (production) or SQLite (development and personal-tier local deployments)
- **ORM:** SQLAlchemy with Alembic for migrations
- **Caching:** Redis for short-lived signal state, scan job queuing, and rate limit counters
- **Secrets:** API keys and provider credentials are never stored in the database in plaintext. They are stored in a secrets manager (e.g. HashiCorp Vault, AWS Secrets Manager, or an encrypted local keystore for personal tiers) and referenced by identifier only

**Repository pattern:** All database access goes through repository classes in `db/repositories/`. No layer above `db/` issues raw queries. This keeps the persistence implementation swappable and makes testing straightforward with mocked repositories.

---

## 4.4 Asset Graph

Assets represent real-world objects in the security context.

```text
backend/app/assets/
├── models.py
├── schemas.py
├── service.py
├── graph.py
└── linking.py
```

**Example entities:**

```text
email          domain         subdomain      account
device         browser        browser_extension
router         network        ip             certificate
application    package        repository     secret
cloud_account  saas_app       document       business
user           phone_number   username
```

**Example relationships:**

```text
user -> owns -> email
user -> uses -> device
user -> logs_into -> account
domain -> resolves_to -> ip
browser -> has_extension -> browser_extension
business -> owns -> domain
business -> uses -> saas_app
repository -> contains -> secret
device -> connected_to -> network
```

`graph.py` maintains relationships between entities. Modules attach signals to these entities. The correlation layer uses the graph to relate signals from different domains and build cross-domain intelligence.

---

## 4.5 Signals

Signals are the basic units of information representing a detected security issue.

```text
backend/app/signals/
├── models.py
├── schemas.py
├── normalizer.py
├── registry.py
└── dedup.py
```

**Responsibilities:**

- define the structure of signals
- validate emitted signals
- normalize outputs across modules
- deduplicate repeated findings
- manage signal lifecycle: `open`, `resolved`, `suppressed`, `stale`

**Standard signal fields:**

```text
signal_id        signal_type      category         entity_type
entity_id        entity_value     severity         confidence
source           provider         module           summary
details          evidence         first_seen        last_seen
status           tags             recommended_action
```

---

## 4.6 Providers

Providers fetch data from external APIs or local collectors, organized by category.

```text
backend/app/providers/
├── base/
│   ├── client.py
│   ├── models.py
│   ├── exceptions.py
│   ├── auth.py
│   └── rate_limit.py
├── breach/
│   ├── hibp/
│   ├── leakcheck/
│   └── hudsonrock/
├── dns/
│   ├── securitytrails/
│   ├── whoisxml/
│   └── crtsh/
├── threat_intel/
│   ├── otx/
│   ├── threatfox/
│   ├── openphish/
│   └── rss_monitor/
├── infrastructure/
│   ├── shodan/
│   ├── censys/
│   └── binaryedge/
├── cloud/
│   ├── google_workspace/
│   ├── microsoft365/
│   ├── aws/
│   └── github/
├── local/
│   ├── device_agent/
│   ├── browser_collector/
│   └── network_scanner/
└── registry.py
```

Each provider folder contains:

- `client.py` — API calls or local collection logic
- `auth.py` — authentication logic
- `schemas.py` — provider-specific request and response models
- `mapper.py` — maps raw responses into provider models
- `config.py` — endpoints, limits, timeouts, feature flags
- `rate_limit.py` — backoff and retry policies
- `exceptions.py` — provider-specific errors
- `tests/` — client and auth tests

Provider files must not include product business logic. See Section 5 for the full provider specification.

---

## 4.7 Modules

Modules interpret provider data into security signals, grouped by domain under `modules/`.

```text
backend/app/modules/<domain>/<module_name>/
├── __init__.py
├── service.py
├── mapper.py
├── rules.py
├── schemas.py
├── config.py
├── constants.py
├── README.md
└── tests/
```

See Section 6 for the full module specification.

---

## 4.8 Correlation Layer

Correlation combines multiple signals into composite, higher-level findings that represent genuine security risk patterns. It is the layer that transforms raw signal volume into actionable intelligence.

```text
backend/app/correlation/
├── engine.py
├── findings.py
├── models.py
└── rules/
    ├── account_takeover.py
    ├── phishing_risk.py
    ├── backup_resilience.py
    ├── business_email_compromise.py
    └── ...
```

**Responsibilities:**

- orchestrate the evaluation of all correlation rules against current signals
- combine signals across module domains using the asset graph for context
- produce higher-level `Finding` objects with their own severity, confidence, and explanation
- keep all logic deterministic, explainable, and independently testable
- avoid any provider or API calls — correlation operates only on stored signals

**Rule structure:**

Each rule file defines one or more correlation rules. A rule specifies:

- the signal types it watches for
- optional entity constraints (e.g. signals must share the same entity)
- optional temporal constraints (e.g. both signals seen within the last 30 days)
- the finding it produces when conditions are met
- a human-readable explanation of why those signals together constitute a risk

**Rule evaluation:**

The correlation engine evaluates rules in the following order:

1. Filter signals by status (`open` or `stale`) and recency
2. For each rule, check whether its required signal types are present for a given entity or entity group
3. If conditions are satisfied, produce a `Finding` and attach it to the relevant entities
4. Deduplicate findings to avoid duplicating the same composite risk across rule runs
5. Persist findings to the database

**Conflict resolution:**

Where two rules might produce overlapping findings for the same entity (e.g. both an `account_takeover_risk` and a `credential_compromise_risk` for the same user), both findings are retained. The scoring layer is responsible for weighting them appropriately. Rules do not suppress each other.

**Example:**

```text
mfa_missing (entity: account) + email_breached (entity: email linked to account)
+ password_reuse_detected (entity: email)
→ high_account_takeover_risk (Finding, severity: critical)
```

---

## 4.9 Scoring Layer

The scoring layer converts signals and correlated findings into numerical or categorical scores.

```text
backend/app/scoring/
├── engine.py
├── models.py
├── weights.py
├── policies.py
└── calculators/
    ├── identity_score.py
    ├── device_score.py
    ├── privacy_score.py
    └── ...
```

Score logic must be versioned. Changes to weights or calculators should be tracked so that historical scores remain explainable. Scores are recalculated by the engine after each scan cycle.

**Scores produced:**

```text
Identity Security Score
Account Security Score
Device Security Score
Browser Security Score
Network Security Score
Privacy Exposure Score
Threat Exposure Score
Cloud Security Score
Business Resilience Score
Cyber Hygiene Score
Zima Overall Security Score
```

---

## 4.10 Remediation Layer

The remediation layer translates findings and signals into suggested, prioritized actions.

```text
backend/app/remediation/
├── engine.py
├── templates.py
├── playbooks/
│   ├── enable_mfa.md
│   ├── rotate_passwords.md
│   ├── secure_router.md
│   └── ...
├── models.py
└── tests/
```

For each signal or correlated finding, remediation provides:

- a summary of the risk
- why it matters
- step-by-step guidance
- estimated time and difficulty
- possible automation hooks

---

## 4.11 Automation Layer

Automation executes remediation tasks after approval where necessary. It is a top-level backend layer — a peer of correlation, scoring, and remediation — and is **not** a module domain.

```text
backend/app/automation/
├── engine.py
├── workflows/
│   ├── revoke_oauth_app.py
│   ├── rotate_secret.py
│   ├── remove_browser_extension.py
│   └── ...
├── approvals.py
└── audit.py
```

Automation includes:

- workflow logic for each supported remediation task
- approval prompts for sensitive or irreversible actions
- execution steps with verification
- audit logging of every action taken
- rollback recommendations where possible

Automation outputs are operational records (`automation_completed`, `automation_failed`), not security risk signals. They are written to the audit log, not the signal registry.

---

## 4.12 Tiers Configuration

Each tier is defined as YAML or JSON listing the module domains enabled for that plan.

```yaml
core:
  enabled_domains:
    - identity
    - accounts
    - device
    - browser

plus:
  enabled_domains:
    - identity
    - accounts
    - device
    - browser
    - network
    - privacy
    - darkweb
    - backup
    - threat_intel

pro:
  enabled_domains:
    - identity
    - accounts
    - device
    - browser
    - network
    - privacy
    - darkweb
    - backup
    - threat_intel
    - domain
    - email
    - infrastructure
    - secrets
    - supply_chain

business:
  enabled_domains:
    - identity
    - accounts
    - device
    - browser
    - network
    - privacy
    - darkweb
    - backup
    - threat_intel
    - domain
    - email
    - infrastructure
    - secrets
    - supply_chain
    - cloud
    - saas
    - incident_readiness
    - compliance
```

**Granularity:** Tier control operates at the **domain level** by default. Where finer control is needed — for example, enabling only specific modules within a domain for a given tier — individual module overrides can be added to the tier definition. Module code is never aware of tier context.

---

## 4.13 Jobs and Scheduling

Background tasks are managed in `jobs/`.

```text
backend/app/jobs/
├── scheduler.py
├── workers.py
├── module_runner.py
└── alerts.py
```

**Responsibilities:**

- trigger module domains at appropriate intervals based on tier config
- execute scans asynchronously
- orchestrate modules respecting tier settings
- manage notifications and user-facing alerts
