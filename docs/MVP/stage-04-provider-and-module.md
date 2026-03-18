# Stage 4 — First Provider and Module

**Exit condition:** The HIBP provider fetches and normalises breach data correctly against mocked responses. The `breach_monitor` module emits correctly structured signals. All provider failure modes are caught, logged, and degrade gracefully. Tests cover every success and failure path.

---

## 4.1 Provider Base Client

```python
# providers/base/client.py
from abc import ABC
from typing import Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from backend.app.core.exceptions import ProviderRateLimitException, ProviderTimeoutException, ProviderAuthException
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

class BaseProviderClient(ABC):
    base_url: str
    timeout_seconds: float = 10.0

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "BaseProviderClient":
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout_seconds),
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(ProviderRateLimitException),
    )
    async def _get(self, path: str, **kwargs: Any) -> httpx.Response:
        if not self._client:
            raise RuntimeError("Client not initialised. Use as async context manager.")
        try:
            response = await self._client.get(path, **kwargs)
        except httpx.TimeoutException as e:
            raise ProviderTimeoutException(f"Timeout: {path}") from e

        if response.status_code == 429:
            logger.warning("provider.rate_limit", path=path)
            raise ProviderRateLimitException("Rate limit exceeded")
        if response.status_code == 401:
            raise ProviderAuthException("Authentication failed")

        return response
```

---

## 4.2 HIBP Provider

```python
# providers/breach/hibp/client.py
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.breach.hibp.schemas import HIBPBreach
from backend.app.providers.breach.hibp.exceptions import HIBPNotFoundError
from backend.app.core.config import settings
from backend.app.core.exceptions import ProviderAuthException

class HIBPClient(BaseProviderClient):
    base_url = "https://haveibeenpwned.com/api/v3"

    async def get_breaches(self, email: str) -> list[HIBPBreach]:
        if not settings.hibp_api_key:
            raise ProviderAuthException("HIBP API key not configured")

        response = await self._get(
            f"/breachedaccount/{email}",
            params={"truncateResponse": "false"},
            headers={"hibp-api-key": settings.hibp_api_key.get_secret_value()},
        )

        if response.status_code == 404:
            return []  # No breaches found — not an error condition

        response.raise_for_status()
        return [HIBPBreach.model_validate(b) for b in response.json()]
```

```python
# providers/breach/hibp/schemas.py
from datetime import date
from pydantic import BaseModel

class HIBPBreach(BaseModel):
    Name: str
    Title: str
    Domain: str
    BreachDate: date
    DataClasses: list[str]
    IsVerified: bool
    IsSensitive: bool
    PwnCount: int
    Description: str
```

```python
# providers/breach/hibp/mapper.py
from dataclasses import dataclass
from datetime import date
from backend.app.providers.breach.hibp.schemas import HIBPBreach

@dataclass
class HIBPBreachRecord:
    """Normalised provider model returned to modules. No Zima severity here."""
    name: str
    title: str
    domain: str
    breach_date: date
    data_classes: list[str]
    is_verified: bool
    is_sensitive: bool
    pwn_count: int
    contains_passwords: bool
    contains_email_addresses: bool

def map_breaches(raw: list[HIBPBreach]) -> list[HIBPBreachRecord]:
    return [
        HIBPBreachRecord(
            name=b.Name,
            title=b.Title,
            domain=b.Domain,
            breach_date=b.BreachDate,
            data_classes=b.DataClasses,
            is_verified=b.IsVerified,
            is_sensitive=b.IsSensitive,
            pwn_count=b.PwnCount,
            contains_passwords="Passwords" in b.DataClasses,
            contains_email_addresses="Email addresses" in b.DataClasses,
        )
        for b in raw
    ]
```

---

## 4.3 Module Base Class

```python
# modules/base/service.py
from abc import ABC, abstractmethod
import uuid
from backend.app.signals.schemas import SignalCreate

class BaseModuleService(ABC):
    module_name: str
    module_domain: str
    required_entity_types: list[str]  # Modules declare what they need

    @abstractmethod
    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
    ) -> list[SignalCreate]:
        """
        Execute against one asset. Returns signals.
        Must never raise on provider failure — degrade gracefully.
        """
        ...
```

---

## 4.4 breach_monitor Module

```python
# modules/identity/breach_monitor/rules.py
from backend.app.providers.breach.hibp.mapper import HIBPBreachRecord
from backend.app.core.enums import Severity, Confidence

def classify_breach(breach: HIBPBreachRecord) -> tuple[Severity, Confidence]:
    if not breach.is_verified:
        return Severity.LOW, Confidence.LOW
    if breach.contains_passwords and breach.is_sensitive:
        return Severity.CRITICAL, Confidence.HIGH
    if breach.contains_passwords:
        return Severity.HIGH, Confidence.HIGH
    if breach.pwn_count > 1_000_000:
        return Severity.MEDIUM, Confidence.HIGH
    return Severity.LOW, Confidence.MEDIUM
```

```python
# modules/identity/breach_monitor/service.py
import uuid
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.breach.hibp.client import HIBPClient
from backend.app.providers.breach.hibp.mapper import map_breaches
from backend.app.modules.identity.breach_monitor.rules import classify_breach
from backend.app.signals.schemas import SignalCreate
from backend.app.core.enums import EntityType
from backend.app.core.exceptions import ProviderException
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

class BreachMonitorService(BaseModuleService):
    module_name = "breach_monitor"
    module_domain = "identity"
    required_entity_types = [EntityType.EMAIL]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
    ) -> list[SignalCreate]:
        try:
            async with HIBPClient() as client:
                raw_breaches = await client.get_breaches(asset_value)
        except ProviderException as e:
            logger.error(
                "breach_monitor.provider_failure",
                error=str(e),
                asset_value=asset_value,
            )
            return []  # Graceful degradation

        breach_records = map_breaches(raw_breaches)
        signals = []

        for breach in breach_records:
            severity, confidence = classify_breach(breach)
            signals.append(
                SignalCreate(
                    signal_type="email_breached",
                    category="identity_security",
                    entity_type=EntityType.EMAIL,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=severity,
                    confidence=confidence,
                    source=self.module_name,
                    provider="hibp",
                    summary=f"Email found in {breach.title} data breach",
                    details=(
                        f"Breach date: {breach.breach_date}. "
                        f"Data exposed: {', '.join(breach.data_classes)}."
                    ),
                    evidence={
                        "breach_name": breach.name,
                        "breach_date": breach.breach_date.isoformat(),
                        "data_classes": breach.data_classes,
                        "pwn_count": breach.pwn_count,
                        "contains_passwords": breach.contains_passwords,
                        "is_verified": breach.is_verified,
                    },
                    tags=["identity", "breach", "credential_risk"],
                    recommended_action=(
                        "Rotate the password used at this service immediately. "
                        "Enable MFA if not already active."
                    ),
                )
            )

        logger.info(
            "breach_monitor.completed",
            user_id=str(user_id),
            signals_emitted=len(signals),
        )
        return signals
```

---

## 4.5 Stage 4 Tests

```python
# tests/unit/modules/test_breach_monitor.py
import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.exceptions import ProviderException
from backend.app.modules.identity.breach_monitor.rules import classify_breach
from backend.app.modules.identity.breach_monitor.service import BreachMonitorService
from backend.app.providers.breach.hibp.mapper import HIBPBreachRecord


def _make_breach(
    contains_passwords: bool = True,
    is_verified: bool = True,
    is_sensitive: bool = False,
    pwn_count: int = 100,
) -> HIBPBreachRecord:
    return HIBPBreachRecord(
        name="Test",
        title="Test Breach",
        domain="test.com",
        breach_date=date(2023, 1, 1),
        data_classes=["Passwords", "Email addresses"] if contains_passwords else ["Email addresses"],
        is_verified=is_verified,
        is_sensitive=is_sensitive,
        pwn_count=pwn_count,
        contains_passwords=contains_passwords,
        contains_email_addresses=True,
    )


def test_classify_verified_password_breach_is_high() -> None:
    severity, confidence = classify_breach(_make_breach(contains_passwords=True, is_verified=True))
    assert severity == Severity.HIGH
    assert confidence == Confidence.HIGH


def test_classify_sensitive_password_breach_is_critical() -> None:
    severity, confidence = classify_breach(_make_breach(contains_passwords=True, is_sensitive=True))
    assert severity == Severity.CRITICAL
    assert confidence == Confidence.HIGH


def test_classify_unverified_breach_is_low() -> None:
    severity, confidence = classify_breach(_make_breach(is_verified=False))
    assert severity == Severity.LOW
    assert confidence == Confidence.LOW


def test_classify_large_non_password_breach_is_medium() -> None:
    severity, confidence = classify_breach(
        _make_breach(contains_passwords=False, is_verified=True, pwn_count=2_000_000)
    )
    assert severity == Severity.MEDIUM


@pytest.mark.asyncio
async def test_run_emits_one_signal_per_breach(mock_hibp_with_breaches) -> None:
    """mock_hibp_with_breaches fixture provides 2 breaches via respx."""
    service = BreachMonitorService()
    signals = await service.run(
        user_id=uuid.uuid4(),
        asset_id=uuid.uuid4(),
        asset_value="test@example.com",
    )
    assert len(signals) == 2


@pytest.mark.asyncio
async def test_run_returns_empty_list_when_no_breaches(mock_hibp_no_breaches) -> None:
    service = BreachMonitorService()
    signals = await service.run(
        user_id=uuid.uuid4(),
        asset_id=uuid.uuid4(),
        asset_value="clean@example.com",
    )
    assert signals == []


@pytest.mark.asyncio
async def test_run_returns_empty_list_on_provider_failure() -> None:
    """Provider failures must not propagate — degrade gracefully."""
    service = BreachMonitorService()
    with patch(
        "backend.app.modules.identity.breach_monitor.service.HIBPClient.__aenter__",
        side_effect=ProviderException("HIBP unavailable"),
    ):
        signals = await service.run(
            user_id=uuid.uuid4(),
            asset_id=uuid.uuid4(),
            asset_value="test@example.com",
        )
    assert signals == []


@pytest.mark.asyncio
async def test_signal_has_correct_type_and_entity(mock_hibp_with_breaches) -> None:
    service = BreachMonitorService()
    signals = await service.run(
        user_id=uuid.uuid4(),
        asset_id=uuid.uuid4(),
        asset_value="test@example.com",
    )
    for signal in signals:
        assert signal.signal_type == "email_breached"
        assert signal.entity_type == EntityType.EMAIL
        assert signal.source == "breach_monitor"
        assert signal.provider == "hibp"
```

```python
# tests/unit/modules/test_hibp_provider.py
import json
import httpx
import pytest
import respx
from datetime import date

from backend.app.core.exceptions import ProviderAuthException, ProviderRateLimitException
from backend.app.providers.breach.hibp.client import HIBPClient
from backend.app.providers.breach.hibp.schemas import HIBPBreach

SAMPLE_BREACH = {
    "Name": "Adobe",
    "Title": "Adobe",
    "Domain": "adobe.com",
    "BreachDate": "2013-10-04",
    "AddedDate": "2013-12-04T00:00:00Z",
    "DataClasses": ["Email addresses", "Passwords"],
    "IsVerified": True,
    "IsSensitive": False,
    "IsRetired": False,
    "IsFabricated": False,
    "PwnCount": 152445165,
    "Description": "Test",
}


@pytest.mark.asyncio
@respx.mock
async def test_get_breaches_returns_parsed_records_on_200() -> None:
    respx.get(url__regex=r".*breachedaccount.*").mock(
        return_value=httpx.Response(200, content=json.dumps([SAMPLE_BREACH]).encode())
    )
    async with HIBPClient() as client:
        results = await client.get_breaches("test@example.com")
    assert len(results) == 1
    assert results[0].Name == "Adobe"


@pytest.mark.asyncio
@respx.mock
async def test_get_breaches_returns_empty_list_on_404() -> None:
    respx.get(url__regex=r".*breachedaccount.*").mock(
        return_value=httpx.Response(404)
    )
    async with HIBPClient() as client:
        results = await client.get_breaches("clean@example.com")
    assert results == []


@pytest.mark.asyncio
@respx.mock
async def test_get_breaches_raises_auth_on_401() -> None:
    respx.get(url__regex=r".*breachedaccount.*").mock(
        return_value=httpx.Response(401)
    )
    with pytest.raises(ProviderAuthException):
        async with HIBPClient() as client:
            await client.get_breaches("test@example.com")
```

**Stage 4 Verification:**
```bash
uv run pytest tests/unit/modules/ -v
uv run python scripts/check_imports.py
```
