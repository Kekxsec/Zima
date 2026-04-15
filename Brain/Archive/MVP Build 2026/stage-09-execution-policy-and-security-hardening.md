---
tags: [zima, architecture, execution, security, next-stage]
created: 2026-04-01
---

← [[MVP Master|Stage Progress]]

# Stage 09 — Execution Policy, Provider Architecture, and Security Hardening

## Why This Stage Exists

The MVP codebase is now large enough that the next bottlenecks are not basic feature gaps. The main issues are:

- provider execution policy is scattered across modules
- identical upstreams are called more than once in a single scan
- failure handling is exception-heavy
- scan history is too thin for debugging and audit
- local-tool providers need stronger isolation and explicit trust boundaries

This stage is about making scan execution safer, cheaper, more observable, and easier to evolve.

## Primary Goals

1. Centralize provider execution policy.
2. Replace exception-driven provider flow with structured results.
3. Reuse provider fetches across modules within a scan.
4. Persist a structured scan execution history.
5. Strengthen security controls around local tools, notifications, and evidence handling.

## 9.1 Structured Provider Results

Introduce a shared result type for provider execution.

Suggested shape:

```python
@dataclass(frozen=True)
class ProviderResult:
    provider: str
    success: bool
    findings: list[dict[str, Any]]
    reason: str | None = None
    retryable: bool = False
    skipped: bool = False
    metadata: dict[str, Any] | None = None
```

Goals:

- remove repeated `try/except ProviderError` blocks from module services
- make skipped providers first-class rather than implicit
- make logging, audit, and scan history consistent
- support downstream decisions without reading exception text

Apply first to:

- `backend/app/modules/identity/breach_monitor/service.py`
- `backend/app/modules/identity/credential_exposure/service.py`
- `backend/app/modules/identity/username_exposure/service.py`
- `backend/app/modules/identity/alias_correlation/service.py`

## 9.2 Central Provider Policy

Create a single policy layer that decides whether a provider is allowed to run before execution starts.

Policy inputs:

- API key / credential presence
- user tier
- scan type
- region / GDPR restrictions
- provider class
- quota / budget status
- local-tool execution permission

Suggested concepts:

```python
@dataclass(frozen=True)
class ProviderPermissionContext:
    scan_type: str
    tier: str
    region: str | None
    deny_names: frozenset[str] = frozenset()
    deny_prefixes: tuple[str, ...] = ()
```

```python
@dataclass(frozen=True)
class ProviderPolicyDecision:
    allowed: bool
    reason: str | None = None
```

Initial write targets:

- `backend/app/providers/base/models.py`
- new policy module under `backend/app/providers/base/`
- module services that currently inline settings checks

## 9.3 Per-Scan Execution Context and Shared Fetch Reuse

Introduce a `ScanExecutionContext` that lives for one scan and memoizes provider calls.

Why:

- `DeHashed` and `BreachDirectory` are called by both `breach_monitor` and `credential_exposure`
- `Epieos` is called by both `username_exposure` and `alias_correlation`
- duplicate calls waste quota, increase latency, and create inconsistent outcomes

Suggested responsibilities:

- cache provider responses keyed by `(provider, entity_type, entity_value, method, params)`
- track provider outcomes and skip reasons
- expose counters for cost / quota / diagnostics
- collect stage and provider events for later persistence

## 9.4 Scan History and Stage Events

The current `Scan` row stores only summary fields.

Add either:

- a `history` JSON field on `scans`, or
- a companion `scan_events` table

Store events such as:

- `scan_started`
- `stage_started`
- `provider_allowed`
- `provider_skipped`
- `provider_failed`
- `provider_succeeded`
- `signals_upserted`
- `notification_sent`
- `notification_failed`
- `scan_completed`
- `scan_failed`
- `scan_marked_stale`

This should become the main debugging surface for stalled or partial scans.

## 9.5 Provider Metadata Registry

Do not do a large runtime discovery rewrite yet.

Instead, add a static provider metadata registry describing:

- provider name
- risk class
- required credentials
- entity coverage
- cost / quota class
- whether it runs a local subprocess
- whether it stores or returns sensitive evidence
- whether sandboxing is required

This is a metadata layer, not a dynamic plugin system.

## 9.6 Security Improvements

### Data Protection and Encryption at Rest

The current architecture assumes infrastructure-level encryption, but the next stage should make the data protection model explicit.

Add a dedicated data protection layer for high-sensitivity fields:

- verified asset values
- signal `entity_value`
- signal `details`
- signal `evidence`
- discovered-account `email_used`
- any future stored OAuth refresh token, API token, or remediation credential

Use envelope encryption:

- master key in Vault / KMS / managed secret store
- per-record or per-field data encryption keys
- application-level encryption before DB write
- authenticated encryption only

Important constraint:

- any field that must support equality lookup should not rely on plaintext storage
- use a blind index / keyed hash for lookup and keep the canonical value encrypted

Stage 09 should explicitly reject the pattern of storing sensitive personal data only in ordinary text or JSON columns and assuming disk encryption is sufficient.

### Encrypted Transport Must Be Enforced, Not Assumed

Production startup checks should fail closed unless:

- PostgreSQL connections require TLS
- Redis connections require TLS where the deployment supports it
- internal service-to-service traffic is encrypted or constrained to a trusted private network

This should be validated in config parsing and startup checks, not left to convention.

Also document the infrastructure dependency clearly:

- managed database storage must be encrypted
- backups and snapshots must be encrypted
- developer laptops and self-hosted machines must use host disk encryption

### Evidence Minimization and Retention

Stage 09 should move from "store rich raw evidence" to "store the minimum durable evidence needed for product behavior, audit, and remediation."

Rules:

- raw provider payloads should not be persisted by default
- evidence should be normalized into concise flags, references, counts, and safe excerpts
- PII-heavy evidence should have a stricter retention class than low-risk metadata
- temporary raw evidence, if ever required, should have TTL-based deletion

Retention classes to introduce:

- ephemeral raw evidence
- durable product evidence
- immutable audit evidence

Each class should define:

- who can read it
- whether it is encrypted at the application layer
- how long it is retained
- how it is deleted

### Central Execution Permission Model

Introduce explicit execution classes:

- passive API lookup
- local subprocess
- filesystem write
- notification send
- billing action
- remediation action

Each class should have policy and audit hooks.

### Evidence Redaction Layer

Move evidence sanitization into shared infrastructure.

Rules:

- providers must never directly persist raw secrets
- modules should not store raw provider payloads unless passed through redaction
- PII-heavy evidence should be filtered before DB write and before log emission
- redaction must run before both persistence and structured logging
- redaction decisions should be testable and versioned

Apply especially to breach and credential-leak providers.

### Stronger Isolation for Local Tools

Treat local-tool providers as higher trust/risk than passive APIs.

Targets:

- `backend/app/providers/tools/holehe/client.py`
- `backend/app/providers/tools/maigret/client.py`

Requirements:

- explicit policy gate before execution
- dedicated sandbox profile
- low-privilege runtime where possible
- separate audit trail for local-tool invocations

### Provider Budgets and Rate Controls

Add limits for:

- providers per asset
- calls per provider per scan
- signals emitted per provider
- notifications per scan

This is both a security control and a cost control.

### Secrets Management Upgrade

Do not treat `.env` as the long-term production secret store.

Stage 09 should move production secrets to a managed secret system:

- provider API keys
- Stripe secrets
- email provider secrets
- JWT signing keys
- future encryption keys

Requirements:

- no secrets committed to repo or baked into images
- rotation procedure documented and tested
- startup should fail if required secret references exist but secret resolution fails

### GDPR and Deletion Hardening

The deletion model must cover all user-derived stores, not just core scan tables.

Stage 09 should require:

- one explicit inventory of all tables containing user-derived data
- one deletion path per table
- tests that verify full deletion coverage
- retention exceptions documented only for true audit/legal requirements

Inbox-derived account discovery data must be included in this model, not treated as secondary metadata.

### Provider Transport Hygiene

The provider catalog should classify each provider by transport risk:

- HTTPS-only
- mixed transport
- HTTP-only
- local-only

Default policy:

- HTTP-only providers are disabled in production unless explicitly approved
- providers with weak or legacy transport require explicit risk acceptance
- transport risk should be visible in provider metadata and scan history

### Additional Controls Worth Considering

These are not all mandatory for the first pass, but they are strong follow-on controls:

- immutable audit protections at the DB layer for audit tables
- backup restore drills for encrypted backups
- `__Host-` prefixed session cookies once deployment shape is stable
- admin/operator RBAC if internal tooling is added
- per-user and per-tenant export audit events
- anomaly detection for unusual scan volume, OTP failures, and provider cost spikes
- incident response runbooks for key rotation, provider compromise, and database compromise
- security regression tests for evidence redaction, deletion coverage, and unsafe provider enablement

### Backend Control Checklist

Stage 09 should also review the broader backend control plane, not only provider execution.

Authentication and session controls:

- add explicit CSRF protection for cookie-authenticated state-changing routes
- validate `Origin` / `Referer` on browser-initiated write requests
- rotate session token on sign-in and other privilege boundary changes
- define whether logout is client-only cookie clearing or server-side session invalidation
- add a session revocation strategy if long-lived sessions or admin roles are introduced

Authorization and data access:

- require ownership checks and test coverage for every user-scoped read/write endpoint
- keep a single authorization pattern for user-owned resources
- document whether future admin/support tools bypass user isolation and how they are audited
- consider row-level security or an equivalent defense if the system becomes multi-tenant

Input, upload, and parser safety:

- enforce request body size limits centrally, not only in individual handlers
- add content sniffing / file signature validation for uploads where feasible
- define quarantine or malware scanning policy for uploaded files if persistence is introduced later
- bound parser work with limits on message count, filename length, and processing time

Network and service isolation:

- define trusted proxy behavior explicitly rather than assuming current deployment topology
- add outbound egress policy / allowlist for provider access if infrastructure permits it
- separate high-risk local-tool execution from the main API runtime where possible
- isolate background workers from public edge traffic when deployment topology grows

Observability and operational security:

- treat structured logs as sensitive data and apply redaction centrally
- define which security events page an operator and which are only retained
- add alerts for repeated 401s, OTP lockouts, provider auth failures, and deletion job failures
- ensure audit, scan history, and operational logs have different retention classes

Supply chain and release controls:

- add dependency scanning for Python and frontend packages in CI
- generate an SBOM for release artifacts if the product will be customer-facing
- add SAST and secret scanning in CI
- pin or review high-risk packages that handle auth, crypto, uploads, or subprocesses

### Frontend Control Checklist

The frontend is already relatively thin, but Stage 09 should still define the browser-side security posture explicitly.

Browser session and request controls:

- keep auth in httpOnly cookies only; do not migrate tokens into local storage or session storage
- avoid persisting sensitive user data in client-side stores unless there is a clear need
- make CSRF assumptions explicit if cookie auth remains the browser model
- document how protected route checks in middleware relate to API-side authorization

Content security policy and script hygiene:

- keep CSP strict as the frontend grows; prefer nonces/hashes if inline scripts become necessary
- review any future third-party script, analytics, or support widget as a security exception
- do not allow arbitrary HTML rendering without sanitization
- keep dangerous React patterns out of the codebase (`dangerouslySetInnerHTML` should be exceptional and reviewed)

Caching and data exposure:

- ensure sensitive pages and API responses remain `no-store`
- review whether any static generation, prefetching, or server component caching could expose user data
- avoid leaking internal error details into browser-visible messages in production

Dependency and build controls:

- add frontend dependency audit and lockfile review to CI
- review build-time environment variables so secrets never cross into browser bundles
- treat browser-exposed env vars as public by default

### Product-Level Security Controls to Keep in Scope

If Zima grows beyond the MVP boundary, Stage 09 should leave room for these controls:

- support/admin access model with strong auditability
- customer-visible security settings and data-retention controls
- incident communications and breach-notification workflow
- formal key rotation cadence
- tabletop exercises for database compromise, provider compromise, and malicious insider scenarios

### Notification Outbox and Idempotency

Move notification sending to an explicit outbox model.

Benefits:

- safer retries
- no duplicate alerting on partial failures
- easier audit and monitoring

## 9.7 Secondary Improvements

These are useful, but should follow the earlier items:

- frozen config objects for provider construction
- hook pipeline for audit/dedup/metrics once execution context exists
- bootstrap credential verification stage
- operator config layering for provider enablement

## 9.8 Explicit Non-Goals

This stage should **not** introduce:

- a broad plugin marketplace
- arbitrary shell hooks
- open-ended dynamic provider loading
- complex routing heuristics for provider selection

Those would increase attack surface before the execution boundary is hardened enough.

## 9.9 Suggested Implementation Order

1. `ProviderResult` and policy decision types
2. `ScanExecutionContext` with provider result cache
3. scan history / scan events persistence
4. provider metadata registry
5. notification outbox and provider budgets
6. hardened isolation for local-tool providers
7. optional hook pipeline on top of the new execution model

## Exit Condition

This stage is complete when:

- provider allow/deny logic is centralized
- application-level protection exists for the highest-sensitivity stored user data
- production transport encryption is enforced at startup
- duplicate upstream fetches are eliminated within a scan
- provider outcomes are structured rather than exception-driven
- scan history is persisted and queryable
- local-tool providers run behind explicit policy and stronger isolation
- evidence redaction is enforced centrally
- evidence minimization and retention classes are enforced
- deletion coverage is complete for all user-derived tables
- notifications are idempotent and auditable
