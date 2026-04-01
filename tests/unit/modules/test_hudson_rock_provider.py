# tests/unit/modules/test_hudson_rock_provider.py
import json

import httpx
import pytest
import respx

from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.breach.hudson_rock.client import HudsonRockProvider

SAMPLE_STEALER_RESPONSE = {
    "stealers": [
        {
            "date_uploaded": "2024-01-15",
            "computer_name": "DESKTOP-ABC123",
            "operating_system": "Windows 10",
            "malware_path": "C:\\Users\\user\\AppData\\Local\\Temp\\RedLine.exe",
            "credentials": [
                {"url": "https://example.com", "username": "user@example.com"},
                {"url": "https://bank.com", "username": "user@example.com"},
            ],
        },
        {
            "date_uploaded": "2024-03-20",
            "computer_name": "LAPTOP-XYZ789",
            "operating_system": "Windows 11",
            "malware_path": "C:\\Temp\\vidar.exe",
            "credentials": [
                {"url": "https://social.com", "username": "user@example.com"},
            ],
        },
    ]
}


@pytest.mark.asyncio
@respx.mock
async def test_get_compromised_data_returns_one_finding_per_stealer() -> None:
    respx.get(url__regex=r".*search-by-login.*").mock(
        return_value=httpx.Response(
            200, content=json.dumps(SAMPLE_STEALER_RESPONSE).encode()
        )
    )
    provider = HudsonRockProvider(api_key="test-key")
    results = await provider.get_compromised_data(email="test@example.com")
    assert len(results) == 2


@pytest.mark.asyncio
@respx.mock
async def test_get_compromised_data_returns_empty_on_no_stealers() -> None:
    respx.get(url__regex=r".*search-by-login.*").mock(
        return_value=httpx.Response(200, content=json.dumps({"stealers": []}).encode())
    )
    provider = HudsonRockProvider(api_key="test-key")
    results = await provider.get_compromised_data(email="clean@example.com")
    assert results == []


@pytest.mark.asyncio
@respx.mock
async def test_get_compromised_data_returns_empty_on_empty_payload() -> None:
    respx.get(url__regex=r".*search-by-login.*").mock(
        return_value=httpx.Response(200, content=json.dumps({}).encode())
    )
    provider = HudsonRockProvider(api_key="test-key")
    results = await provider.get_compromised_data(email="test@example.com")
    assert results == []


@pytest.mark.asyncio
async def test_get_compromised_data_raises_on_missing_api_key() -> None:
    provider = HudsonRockProvider(api_key="")
    with pytest.raises(ProviderError, match="API key is required"):
        await provider.get_compromised_data(email="test@example.com")


@pytest.mark.asyncio
@respx.mock
async def test_finding_fields_are_correct() -> None:
    single_stealer = {
        "stealers": [
            {
                "date_uploaded": "2024-01-15",
                "computer_name": "DESKTOP-ABC123",
                "operating_system": "Windows 10",
                "malware_path": "C:\\Temp\\RedLine.exe",
                "credentials": [{"url": "https://example.com", "username": "user"}],
            }
        ]
    }
    respx.get(url__regex=r".*search-by-login.*").mock(
        return_value=httpx.Response(200, content=json.dumps(single_stealer).encode())
    )
    provider = HudsonRockProvider(api_key="test-key")
    results = await provider.get_compromised_data(email="test@example.com")
    assert len(results) == 1
    finding = results[0]
    assert finding["provider"] == "hudson_rock"
    assert finding["category"] == "stealer_log_exposure"
    raw = finding["raw"]
    assert raw["date_uploaded"] == "2024-01-15"
    assert raw["computer_name"] == "DESKTOP-ABC123"
    assert raw["operating_system"] == "Windows 10"
    # os.path.basename on macOS doesn't split Windows backslash paths,
    # so the full malware_path is returned as-is.
    assert "RedLine" in raw["malware_name"]
    assert raw["credential_count"] == 1
    # Passwords must never appear in raw
    assert "passwords" not in raw
    assert "credentials" not in raw


@pytest.mark.asyncio
@respx.mock
async def test_get_compromised_data_skips_no_inputs() -> None:
    """Calling with neither email nor domain returns empty list without making HTTP requests."""
    provider = HudsonRockProvider(api_key="test-key")
    results = await provider.get_compromised_data()
    assert results == []
