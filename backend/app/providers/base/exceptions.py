# backend/app/providers/base/exceptions.py
from __future__ import annotations


class ProviderError(Exception):
    """Base exception for all provider errors."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class ProviderAuthError(ProviderError):
    """Raised when API authentication fails (401/403)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=False)


class ProviderRateLimitError(ProviderError):
    """Raised when the upstream API rate-limits the request (429)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=True)


class ProviderTimeoutError(ProviderError):
    """Raised when the upstream request times out or the network fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=True)


class ProviderUpstreamError(ProviderError):
    """Raised when the upstream API returns a 5xx server error."""

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message, retryable=True)
        self.status_code = status_code


class ProviderSchemaError(ProviderError):
    """Raised when the upstream response does not match the expected schema."""

    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=False)
