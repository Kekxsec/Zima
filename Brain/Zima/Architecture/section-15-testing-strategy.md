← [[../Zima|Home]] · [[section-14-observability|← §14 Observability]] · [[section-16-security-requirements|§16 Security Requirements →]]

# Section 15 — Testing Strategy

Testing is a non-negotiable part of every layer. Use mocked provider responses by default. Live tests must always be opt-in and must never run in CI without explicit configuration.

---

## Test Types

**Unit tests**
Cover providers, mappers, rules, and scoring calculators in isolation. Each component is tested independently with controlled inputs and expected outputs.

**Contract tests**
Validate provider schemas and edge cases. Ensure that provider response models match real API response shapes. Run against recorded fixtures to catch drift.

**Integration tests**
Test modules end-to-end with mocked providers. Verify that a module correctly orchestrates provider calls, maps data, evaluates rules, and emits the expected signals for a given input.

**Negative tests**
Cover failure conditions explicitly: timeouts, authentication failures, malformed provider responses, empty result sets, and HTTP 429 rate limiting. Every provider and module must handle these gracefully.

**Correlation tests**
Verify that each correlation rule produces the expected finding given a known set of input signals, and does not fire on signal sets that do not meet conditions.

**Scoring tests**
Verify that score calculators produce deterministic, expected outputs for fixed signal inputs. Test score change behaviour when signals are added, resolved, or suppressed.

**Smoke tests**
Optional live tests for providers requiring real credentials. These are never run in CI without explicit opt-in. They verify that the provider client can successfully authenticate and retrieve data from the real API.

---

## Test Structure

Each module and provider contains a `tests/` directory co-located with the code. Cross-cutting integration and end-to-end tests live in the top-level `tests/` directory.

```text
tests/
├── e2e/
├── integration/
├── fixtures/
└── conftest.py
```

---

## Principles

- Never make live API calls in CI unless explicitly configured for smoke tests
- Use factory fixtures to generate realistic signal and provider response data
- Test correlation rules with both positive cases (rule fires) and negative cases (rule does not fire)
- Treat negative cases — failures, errors, edge inputs — as first-class test requirements, not afterthoughts
