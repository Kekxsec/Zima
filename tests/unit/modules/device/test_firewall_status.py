# tests/unit/modules/device/test_firewall_status.py
import uuid
from unittest.mock import patch

import pytest

from backend.app.core.enums import EntityType, Severity
from backend.app.modules.device.firewall_status.service import FirewallStatusService
from backend.app.providers.base.exceptions import ProviderError

USER_ID = uuid.uuid4()
ASSET_ID = uuid.uuid4()


@pytest.mark.asyncio
async def test_iptables_rules_detected_emits_info_signal() -> None:
    service = FirewallStatusService()
    iptables_rows = [
        {"chain": "INPUT", "policy": "ACCEPT", "target": "ACCEPT", "protocol": "tcp"},
        {"chain": "OUTPUT", "policy": "ACCEPT", "target": "ACCEPT", "protocol": "all"},
    ]
    with (
        patch(
            "backend.app.modules.device.firewall_status.service.OsqueryProvider.query_named",
            return_value=iptables_rows,
        ),
        patch(
            "backend.app.modules.device.firewall_status.service.LynisProvider.audit",
            return_value={"warnings": [], "suggestions": []},
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    fw_signals = [
        s for s in outcome.signals if s.signal_type == "firewall_rules_detected"
    ]
    assert len(fw_signals) == 1
    s = fw_signals[0]
    assert s.severity == Severity.INFO
    assert s.entity_type == EntityType.DEVICE
    assert s.provider == "osquery"
    assert s.evidence["total_entries"] == 2


@pytest.mark.asyncio
async def test_empty_iptables_emits_medium_signal() -> None:
    """osquery returns an empty list → no rules configured."""
    service = FirewallStatusService()
    with (
        patch(
            "backend.app.modules.device.firewall_status.service.OsqueryProvider.query_named",
            return_value=[],
        ),
        patch(
            "backend.app.modules.device.firewall_status.service.LynisProvider.audit",
            return_value={"warnings": [], "suggestions": []},
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    no_rules = [
        s for s in outcome.signals if s.signal_type == "firewall_no_rules_detected"
    ]
    assert len(no_rules) == 1
    assert no_rules[0].severity == Severity.MEDIUM


@pytest.mark.asyncio
async def test_lynis_firewall_warnings_emit_high_signal() -> None:
    service = FirewallStatusService()
    with (
        patch(
            "backend.app.modules.device.firewall_status.service.OsqueryProvider.query_named",
            side_effect=ProviderError("osquery unavailable"),
        ),
        patch(
            "backend.app.modules.device.firewall_status.service.LynisProvider.audit",
            return_value={
                "warnings": ["FIRE-4512: iptables is not active"],
                "suggestions": [],
            },
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    warn_signals = [
        s for s in outcome.signals if s.signal_type == "firewall_lynis_warnings"
    ]
    assert len(warn_signals) == 1
    s = warn_signals[0]
    assert s.severity == Severity.HIGH
    assert s.provider == "lynis"
    assert len(s.evidence["firewall_warnings"]) == 1


@pytest.mark.asyncio
async def test_lynis_firewall_suggestions_only_emits_low_signal() -> None:
    service = FirewallStatusService()
    with (
        patch(
            "backend.app.modules.device.firewall_status.service.OsqueryProvider.query_named",
            side_effect=ProviderError("osquery unavailable"),
        ),
        patch(
            "backend.app.modules.device.firewall_status.service.LynisProvider.audit",
            return_value={
                "warnings": [],
                "suggestions": ["Consider enabling ufw for easier firewall management"],
            },
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    sug_signals = [
        s for s in outcome.signals if s.signal_type == "firewall_lynis_suggestions"
    ]
    assert len(sug_signals) == 1
    assert sug_signals[0].severity == Severity.LOW


@pytest.mark.asyncio
async def test_lynis_unavailable_does_not_prevent_osquery_signal() -> None:
    service = FirewallStatusService()
    iptables_rows = [
        {"chain": "INPUT", "target": "DROP", "protocol": "tcp"},
    ]
    with (
        patch(
            "backend.app.modules.device.firewall_status.service.OsqueryProvider.query_named",
            return_value=iptables_rows,
        ),
        patch(
            "backend.app.modules.device.firewall_status.service.LynisProvider.audit",
            side_effect=ProviderError("lynis not found"),
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    assert any(s.signal_type == "firewall_rules_detected" for s in outcome.signals)
    assert not any(s.signal_type == "firewall_lynis_warnings" for s in outcome.signals)


@pytest.mark.asyncio
async def test_no_providers_available_returns_empty() -> None:
    service = FirewallStatusService()
    with (
        patch(
            "backend.app.modules.device.firewall_status.service.OsqueryProvider.query_named",
            side_effect=ProviderError("osquery unavailable"),
        ),
        patch(
            "backend.app.modules.device.firewall_status.service.LynisProvider.audit",
            side_effect=ProviderError("lynis unavailable"),
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    assert outcome.signals == []
