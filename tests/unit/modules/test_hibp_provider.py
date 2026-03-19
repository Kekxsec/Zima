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
    respx.get(url__regex=r".*breachedaccount.*").mock(return_value=httpx.Response(404))
    provider = HibpProvider(api_key="test-key")
    results = await provider.search_breaches(email="clean@example.com")
    assert results == []


@pytest.mark.asyncio
@respx.mock
async def test_search_breaches_raises_auth_on_401() -> None:
    respx.get(url__regex=r".*breachedaccount.*").mock(return_value=httpx.Response(401))
    with pytest.raises(ProviderAuthError):
        provider = HibpProvider(api_key="bad-key")
        await provider.search_breaches(email="test@example.com")


def test_search_breaches_raises_on_missing_api_key() -> None:
    import asyncio

    from backend.app.providers.base.exceptions import ProviderError

    provider = HibpProvider(api_key="")
    with pytest.raises(ProviderError, match="API key is required"):
        asyncio.get_event_loop().run_until_complete(
            provider.search_breaches(email="test@example.com")
        )
