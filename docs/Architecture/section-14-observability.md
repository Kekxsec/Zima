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
