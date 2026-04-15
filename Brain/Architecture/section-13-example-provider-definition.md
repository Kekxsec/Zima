← [[../Zima|Home]] · [[section-12-example-module-definition|← §12 Example Module]] · [[section-14-observability|§14 Observability →]]

# Section 13 — Example Provider Definition

This section provides a fully worked example of a provider definition to serve as a reference template for all future provider development.

---

**Provider:** `hibp`
**Category:** `breach`

**Methods:**

- `get_breaches(email: str) -> list[BreachOccurrence]`
- `get_pastes(email: str) -> list[PasteOccurrence]`

**What it does:**

- contacts the Have I Been Pwned API
- handles throttling and 429 responses with exponential backoff
- parses JSON response bodies
- maps raw API responses into structured `BreachOccurrence` and `PasteOccurrence` models
- returns those models to the consuming module

**What it does not do:**

- does not decide whether a breach is severe or not
- does not emit Zima signals
- does not know which module or tier is consuming it
- does not produce any user-facing output

---

## Key Implementation Notes

- All API keys are loaded from the secrets manager, never hardcoded or read from environment variables directly in `client.py`
- Rate limiting is handled in `rate_limit.py` using exponential backoff with jitter
- `mapper.py` converts raw API dicts into typed Pydantic models before returning them
- `exceptions.py` defines `HIBPRateLimitError`, `HIBPAuthError`, and `HIBPNotFoundError` separately so consuming modules can handle them explicitly
- Tests use recorded fixture responses; no live API calls in CI

---

## Reminder

The provider never decides severity. The `breach_monitor` module receives the `BreachOccurrence` models and interprets each one as a signal with appropriate severity and confidence.
