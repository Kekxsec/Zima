# Section 10 — Dependency Flow

To avoid circular imports and maintain architectural clarity, all dependencies flow in one direction only. No layer may import from a layer above it.

---

## Dependency Direction

```
core → providers → modules → correlation → scoring → remediation → automation → api
```

---

## Rules Table

| Layer | May import from | Must not import from |
|---|---|---|
| `core` | Nothing | Everything above |
| `providers` | `core` | `modules`, `correlation`, `scoring`, `remediation`, `automation`, `api` |
| `modules` | `core`, `providers`, `signals`, `assets` | `correlation`, `scoring`, `remediation`, `automation`, `api` |
| `correlation` | `core`, `signals`, `assets`, `modules` (read-only via signal model) | `scoring`, `remediation`, `automation`, `api` |
| `scoring` | `core`, `signals`, `correlation` findings | `remediation`, `automation`, `api` |
| `remediation` | `core`, `signals`, `scoring` | `automation`, `api` |
| `automation` | `core`, `remediation` | `api` |
| `api` | All layers (read-only) | — |

---

## Why This Matters

Violating the dependency direction introduces coupling that:

- makes isolated unit testing impossible without mocking unrelated layers
- creates circular import errors that are difficult to debug
- makes the system harder to reason about when modifying a single layer

Any case where a lower layer appears to need data from a higher layer is a signal that the concern is in the wrong place. Refactor the responsibility rather than break the rule.
