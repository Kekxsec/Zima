← [[../Zima|Home]] · [[section-04-backend-architecture|← §4 Backend Architecture]] · [[section-06-module-architecture|§6 Module Architecture →]]

# Section 5 — Provider Architecture

Providers fetch data from external APIs or local collectors. They are the only layer that communicates with the outside world, and they return normalized models to modules. They never make security judgments.

---

## Provider Folder Structure

```text
backend/app/providers/<category>/<provider>/
├── client.py
├── auth.py
├── schemas.py
├── mapper.py
├── config.py
├── rate_limit.py
├── exceptions.py
└── tests/
    ├── test_client.py
    ├── test_auth.py
    └── fixtures/
```

---

## Provider Responsibilities

- authenticate to the source
- perform requests or local collection
- handle pagination and retries
- handle rate limiting and timeouts
- parse raw responses
- normalize responses into provider-specific models

---

## Provider Anti-Patterns

Providers must **not**:

- assign Zima severity or confidence
- emit final Zima signals
- know about tiers or which modules consume them
- implement remediation logic
- produce user-facing narratives or messages

They only return normalized provider models to modules.

---

## Example Provider Definition

**Provider:** `hibp`
**Category:** `breach`

**Methods:**

- `get_breaches(email)`
- `get_pastes(email)`

**What it does:**

- contacts the HIBP API
- handles throttling and 429 responses with exponential backoff
- parses JSON response
- returns structured breach occurrence models

The provider never decides severity. The module interprets each breach occurrence as a signal.
