# Stage 4 — First Provider and Module

**Exit condition:** The HIBP provider fetches and normalises breach data correctly against mocked responses. The `breach_monitor` module emits correctly structured signals. All provider failure modes are caught, logged, and degrade gracefully. Tests cover every success and failure path.

---

## 4.1 Provider Base Client

**Already implemented.** `backend/app/providers/base/client.py` was created during scaffolding. Do not recreate it.

The actual `_get()` signature differs from the original spec — it takes a full URL (not a relative path) and keyword-only arguments:

```python
async def _get(
    self,
    url: str,
    *,
    label: str = "",
    headers: dict[str, str] | None = None,
    timeout: int | None = None,
) -> Any:
    """GET request. Returns parsed JSON body, or {} for 404/empty."""
```

Error types are defined in `backend/app/providers/base/exceptions.py`:
- `ProviderAuthError` — 401/403 responses
- `ProviderRateLimitError` — 429 responses (auto-retried via tenacity)
- `ProviderTimeoutError` — network timeouts
- `ProviderUpstreamError` — 5xx responses
- `ProviderSchemaError` — JSON parse failures

Use these when writing modules that catch provider errors.

---

## 4.2 HIBP Provider

**Pre-scaffolded provider exists** at `backend/app/providers/breach/haveibeenpwned/client.py`. This is a `HaveIBeenPwnedProvider(BaseProviderClient)` adapted from SpiderFoot. It calls the HIBP API but returns raw `list[dict]` findings rather than typed models.

Stage 4 implements `backend/app/providers/breach/hibp/client.py` following the same pattern as all other providers: a single `client.py` with a `{Name}Provider(BaseProviderClient)` class returning `list[dict[str, Any]]`. The `schemas.py`, `mapper.py`, and `exceptions.py` stubs in that directory are not used.

```python
# backend/app/providers/breach/hibp/client.py
from __future__ import annotations

import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import ProviderError


class HibpProvider(BaseProviderClient):
    name = "haveibeenpwned"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_breaches(
        self, *, email: str | None = None, phone_number: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(message="HaveIBeenPwned API key is required", retryable=False)

        findings = []
        _inputs: list[tuple[str, str]] = []
        if email is not None:
            _inputs.append(("email", email))
        if phone_number is not None:
            _inputs.append(("phone_number", phone_number))

        for _entity_type, _value in _inputs:
            if _entity_type not in {"email", "phone"}:
                continue
            target_value = _value.strip()
            if not target_value:
                continue
            target = urllib.parse.quote(target_value)
            url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{target}"
            headers = {
                "Accept": "application/vnd.haveibeenpwned.v3+json",
                "hibp-api-key": api_key,
            }
            payload = await self._get(url, label="HaveIBeenPwned", headers=headers, timeout=self._timeout_seconds)
            if not payload:
                continue
            if not isinstance(payload, list):
                raise ProviderError(message="HaveIBeenPwned schema changed: expected list payload", retryable=False)

            for breach in payload:
                if not isinstance(breach, dict):
                    continue
                breach_name = str(breach.get("Name", "")).strip()
                if not breach_name:
                    raise ProviderError(message="HaveIBeenPwned schema changed: missing breach Name", retryable=False)
                findings.append(dict(
                    provider=self.name,
                    category="breach_detection",
                    title="Credential exposure in breach",
                    description=f"{_value} appears in breach dataset: {breach_name}",
                    entity_type=_entity_type,
                    entity_value=_value,
                    confidence=0.9,
                    tags=["breach", "credential_exposure", "passive"],
                ))

        return findings
```

The API key is passed at instantiation: `HibpProvider(api_key=settings.hibp_api_key.get_secret_value())`.

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

No `rules.py` needed — `HibpProvider` returns findings dicts; the module maps each finding to a signal. Severity is `HIGH` for all confirmed breach findings (the provider already filters out noise).

```python
# modules/identity/breach_monitor/service.py
import uuid
from typing import Any

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.breach.hibp.client import HibpProvider
from backend.app.signals.schemas import SignalCreate

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
        api_key = settings.hibp_api_key.get_secret_value() if settings.hibp_api_key else ""
        provider = HibpProvider(api_key=api_key)
        try:
            findings: list[dict[str, Any]] = await provider.search_breaches(email=asset_value)
        except ProviderError as e:
            logger.error("breach_monitor.provider_failure", error=str(e), asset_value=asset_value)
            return []  # Graceful degradation

        signals = []
        for finding in findings:
            signals.append(
                SignalCreate(
                    signal_type="email_breached",
                    category="identity_security",
                    entity_type=EntityType.EMAIL,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.HIGH,
                    confidence=Confidence.HIGH,
                    source=self.module_name,
                    provider="haveibeenpwned",
                    summary=finding["title"],
                    details=finding["description"],
                    evidence={"raw_finding": finding},
                    tags=finding.get("tags", []) + ["identity", "breach"],
                    recommended_action=(
                        "Rotate the password used at this service immediately. "
                        "Enable MFA if not already active."
                    ),
                )
            )

        logger.info("breach_monitor.completed", user_id=str(user_id), signals_emitted=len(signals))
        return signals
```

---

## 4.5 Stage 4 Tests

```python
# tests/unit/modules/test_breach_monitor.py
import uuid
from unittest.mock import patch

import pytest

from backend.app.core.enums import EntityType, Severity
from backend.app.modules.identity.breach_monitor.service import BreachMonitorService
from backend.app.providers.base.exceptions import ProviderError


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
        "backend.app.modules.identity.breach_monitor.service.HibpProvider.search_breaches",
        side_effect=ProviderError("HIBP unavailable"),
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
        assert signal.provider == "haveibeenpwned"
        assert signal.severity == Severity.HIGH
```

```python
# tests/unit/modules/test_hibp_provider.py
import json

import httpx
import pytest
import respx

from backend.app.providers.base.exceptions import ProviderAuthError
from backend.app.providers.breach.hibp.client import HibpProvider

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
async def test_search_breaches_returns_findings_on_200() -> None:
    respx.get(url__regex=r".*breachedaccount.*").mock(
        return_value=httpx.Response(200, content=json.dumps([SAMPLE_BREACH]).encode())
    )
    provider = HibpProvider(api_key="test-key")
    results = await provider.search_breaches(email="test@example.com")
    assert len(results) == 1
    assert results[0]["provider"] == "haveibeenpwned"
    assert results[0]["category"] == "breach_detection"
    assert "Adobe" in results[0]["description"]


@pytest.mark.asyncio
@respx.mock
async def test_search_breaches_returns_empty_list_on_404() -> None:
    respx.get(url__regex=r".*breachedaccount.*").mock(
        return_value=httpx.Response(404)
    )
    provider = HibpProvider(api_key="test-key")
    results = await provider.search_breaches(email="clean@example.com")
    assert results == []


@pytest.mark.asyncio
@respx.mock
async def test_search_breaches_raises_auth_on_401() -> None:
    respx.get(url__regex=r".*breachedaccount.*").mock(
        return_value=httpx.Response(401)
    )
    with pytest.raises(ProviderAuthError):
        provider = HibpProvider(api_key="bad-key")
        await provider.search_breaches(email="test@example.com")


def test_search_breaches_raises_on_missing_api_key() -> None:
    from backend.app.providers.base.exceptions import ProviderError
    import asyncio
    provider = HibpProvider(api_key="")
    with pytest.raises(ProviderError, match="API key is required"):
        asyncio.get_event_loop().run_until_complete(
            provider.search_breaches(email="test@example.com")
        )
```

**Stage 4 Verification:**
```bash
uv run pytest tests/unit/modules/ -v
uv run python scripts/check_imports.py
```
