# backend/app/signals/redaction.py
"""
Evidence redaction for signal storage.

Before any signal evidence dict is written to the database, it is passed
through redact_evidence() to strip keys that contain raw credential or
identity material.

This is a defence-in-depth measure.  Providers and modules should already
avoid including plaintext credentials in evidence, but this layer catches
accidental leakage (e.g. a provider response that embeds a password field
that a module author forgot to drop).

Redacted keys are replaced with the sentinel string "[REDACTED]" so that
audit tooling can see that a field was present without seeing the value.
"""

from __future__ import annotations

from typing import Any

# Case-insensitive substrings — any key whose lower-cased name contains one of
# these strings will be redacted.  Keep the list conservative: false positives
# waste signal value; the provider / module is the primary defence.
_REDACTED_SUBSTRINGS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "credential",
        "auth_token",
        "access_token",
        "refresh_token",
        "private_key",
        "hash",  # covers password_hash, pwd_hash, etc.
        "salt",
        "ssn",
        "credit_card",
        "card_number",
        "cvv",
    }
)

_REDACTED_SENTINEL = "[REDACTED]"


def redact_evidence(evidence: dict[str, Any] | None) -> dict[str, Any]:
    """
    Return a shallow copy of evidence with sensitive keys replaced by
    the redaction sentinel.  Nested dicts are NOT recursed into — module
    authors should keep evidence flat.

    Passing None returns an empty dict.
    """
    if not evidence:
        return {}

    result: dict[str, Any] = {}
    for k, v in evidence.items():
        lower_key = k.lower()
        if any(sub in lower_key for sub in _REDACTED_SUBSTRINGS):
            result[k] = _REDACTED_SENTINEL
        else:
            result[k] = v
    return result
