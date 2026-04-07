# tests/unit/conftest.py
# Override session-level fixtures that require external services (Redis, DB)
# so that pure unit tests run without infrastructure dependencies.
import pytest


@pytest.fixture(scope="session", autouse=True)
def flush_rate_limit_keys() -> None:  # type: ignore[override]
    """No-op override — unit tests do not need Redis rate-limit flushing."""
    return
