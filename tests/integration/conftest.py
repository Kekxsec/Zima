# tests/integration/conftest.py
# Override session-level fixtures that require external services (Redis, DB)
# for integration tests that do not use real infrastructure.
import pytest


@pytest.fixture(scope="session", autouse=True)
def flush_rate_limit_keys() -> None:  # type: ignore[override]
    """No-op override — e2e pillar tests mock all providers and do not need Redis."""
    return
