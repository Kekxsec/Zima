# Section 14 — Observability

Observability is a first-class concern in Zima. Noisy modules, unstable providers, and unreliable scoring will degrade user trust quickly. The following metrics must be tracked to detect and address problems early.

---

## Metrics to Track

**Provider health:**

- error rates per provider (auth failures, timeouts, malformed responses)
- rate limit trigger frequency per provider
- average response time per provider

**Module execution:**

- module run duration per execution
- success and failure counts per module
- signal volume emitted per module per run

**Signal pipeline:**

- total signals by domain and severity
- deduplication rates (signals suppressed as duplicates)
- signal status distribution (open, resolved, suppressed, stale)
- time-to-resolve per signal type

**Correlation:**

- rule hit frequency per correlation rule
- finding production rate per rule
- false-positive rate (where measurable via user feedback)

**Scoring:**

- score distribution across users and domains
- score change deltas between scan cycles

**Remediation and automation:**

- remediation task completion rates
- automation workflow success and failure logs
- time from finding to remediation completion

---

## Implementation Guidance

- Use structured logging throughout (JSON logs with consistent field names)
- Emit metrics to a metrics backend (e.g. Prometheus or a hosted equivalent)
- Alert on provider error rate spikes and module failure streaks
- Track per-user score trends for anomaly detection
- Ensure all automation actions are written to an immutable audit log

## Logging Configuration

Logging is environment-aware via `core/logging.py::configure_logging()`:

- **Development** (`APP_ENV=development`): `ConsoleRenderer` (human-readable), `DEBUG` level
- **Production** (`APP_ENV=production`): `JSONRenderer` (machine-parseable), `INFO` level

**Do not switch to `ConsoleRenderer` in production.** Structured JSON fields are required for Railway log forwarding and any log aggregation pipeline (Datadog, Loki, etc.). `ConsoleRenderer` output is unstructured text that cannot be reliably parsed by log agents.

`configure_logging()` must be called once at application startup (in the FastAPI `lifespan` handler). It must not be called per-request.

## Token Cleanup

`auth_tokens` rows are purged by a background task started in the FastAPI `lifespan` handler (`main.py::_periodic_token_cleanup`). It calls `AuthTokenRepository.delete_expired(older_than_days=7)` every 24 hours in its own `AsyncSessionLocal()` session (Rule 3 compliant). The 7-day grace period retains recently expired tokens for forensic review before deletion. The task is cancelled cleanly on application shutdown.

Log event: `auth.tokens.cleanup_complete` with `deleted=<count>` on each run. Alert if `auth.tokens.cleanup_failed` appears — this indicates a DB connectivity issue during the maintenance window.
