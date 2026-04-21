# backend/app/providers/ai/ollama/schemas.py
from typing import NotRequired, TypedDict


class OllamaAccountContext(TypedDict):
    """Compact context sent to Ollama for account interpretation. No PII."""

    sender_domain: str
    sample_subjects: list[str]
    current_guess: str
    email_count: int
    login_url: NotRequired[str | None]
    unsubscribe_url: NotRequired[str | None]


class OllamaAccountInterpretation(TypedDict, total=False):
    """Structured JSON response from Ollama for account identification."""

    service_name: str
    display_name: str
    confidence: int
    reason: NotRequired[str]


class OllamaBatchContext(TypedDict):
    """Input wrapper for batch account interpretation."""

    accounts: list[OllamaAccountContext]


class OllamaBatchInterpretation(TypedDict):
    """Output wrapper for batch account interpretation.

    results[i] corresponds to accounts[i] in the request. None indicates
    a parse failure for that entry; the caller should fail open.
    """

    results: list[OllamaAccountInterpretation | None]
