# Section 8 — Signal Model

Signals are the standardized output of modules. They are the atomic unit of security intelligence in the Zima pipeline. Every finding, every score, and every remediation task ultimately traces back to one or more signals.

---

## Signal Schema

```json
{
  "signal_id": "sig_abc123",
  "signal_type": "mfa_missing",
  "category": "account_security",
  "entity_type": "account",
  "entity_id": "acct_001",
  "entity_value": "user@example.com",
  "severity": "high",
  "confidence": "high",
  "source": "mfa_posture",
  "provider": "google_workspace",
  "summary": "Multi-factor authentication is not enabled",
  "details": "Primary email account has no MFA configured",
  "evidence": {
    "mfa_enabled": false
  },
  "first_seen": "2026-03-17T12:00:00Z",
  "last_seen": "2026-03-17T12:00:00Z",
  "status": "open",
  "tags": ["identity", "account_takeover"],
  "recommended_action": "Enable authenticator-based MFA"
}
```

---

## Field Reference

| Field | Description |
|---|---|
| `signal_id` | Unique identifier for this signal instance |
| `signal_type` | Machine-readable type identifier (e.g. `mfa_missing`) |
| `category` | Security category the signal belongs to |
| `entity_type` | Type of asset the signal is attached to |
| `entity_id` | Identifier of the specific asset |
| `entity_value` | Human-readable value of the asset (e.g. an email address) |
| `severity` | Risk severity: `critical`, `high`, `medium`, `low`, `info` |
| `confidence` | Confidence in the finding: `high`, `medium`, `low` |
| `source` | Module that emitted the signal |
| `provider` | Provider that supplied the underlying data |
| `summary` | Short human-readable description |
| `details` | Extended description of the finding |
| `evidence` | Raw supporting data from the provider |
| `first_seen` | Timestamp when first detected |
| `last_seen` | Timestamp of the most recent detection |
| `status` | Lifecycle status: `open`, `resolved`, `suppressed`, `stale` |
| `tags` | Domain and category tags for filtering and correlation |
| `recommended_action` | Short remediation hint |

---

## Signal Lifecycle

A signal moves through the following states:

```
open → resolved
     → suppressed
     → stale
```

- **open** — currently detected and unresolved
- **resolved** — condition no longer detected on the most recent scan
- **suppressed** — acknowledged by the user; will not surface in the UI until reopened
- **stale** — provider has not returned data recently enough to confirm or deny the condition

---

## Signal Attachment

Signals always attach to one or more entities in the asset graph. This attachment is what enables:

- cross-domain correlation (e.g. linking a breached email to an account with missing MFA on the same user)
- score computation scoped to specific entities or domains
- remediation guidance targeted at specific assets
