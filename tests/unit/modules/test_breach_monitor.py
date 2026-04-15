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
    outcome = await service.run(
        user_id=uuid.uuid4(),
        asset_id=uuid.uuid4(),
        asset_value="test@example.com",
    )
    assert len(outcome.signals) == 2


@pytest.mark.asyncio
async def test_run_returns_empty_list_when_no_breaches(mock_hibp_no_breaches) -> None:
    service = BreachMonitorService()
    outcome = await service.run(
        user_id=uuid.uuid4(),
        asset_id=uuid.uuid4(),
        asset_value="clean@example.com",
    )
    assert outcome.signals == []


@pytest.mark.asyncio
async def test_run_returns_empty_list_on_provider_failure() -> None:
    """Provider failures must not propagate — degrade gracefully."""
    service = BreachMonitorService()
    with patch(
        "backend.app.modules.identity.breach_monitor.service.HibpProvider.search_breaches",
        side_effect=ProviderError("HIBP unavailable"),
    ):
        outcome = await service.run(
            user_id=uuid.uuid4(),
            asset_id=uuid.uuid4(),
            asset_value="test@example.com",
        )
    assert outcome.signals == []


@pytest.mark.asyncio
async def test_signal_has_correct_type_and_entity(mock_hibp_with_breaches) -> None:
    service = BreachMonitorService()
    outcome = await service.run(
        user_id=uuid.uuid4(),
        asset_id=uuid.uuid4(),
        asset_value="test@example.com",
    )
    for signal in outcome.signals:
        assert signal.signal_type == "email_breached"
        assert signal.entity_type == EntityType.EMAIL
        assert signal.source == "breach_monitor"
        assert signal.provider == "haveibeenpwned"
        assert signal.severity == Severity.HIGH
