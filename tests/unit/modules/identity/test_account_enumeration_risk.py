# tests/unit/modules/identity/test_account_enumeration_risk.py
import uuid
from unittest.mock import patch

import pytest

from backend.app.core.enums import EntityType, Severity
from backend.app.modules.identity.account_enumeration_risk.service import (
    AccountEnumerationRiskService,
)

USER_ID = uuid.uuid4()
ASSET_ID = uuid.uuid4()


def _emailrep_finding(
    suspicious: bool = False,
    blacklisted: bool = False,
    spam: bool = False,
    reputation: str = "medium",
) -> dict:  # type: ignore[type-arg]
    return {
        "title": "Email reputation",
        "description": None,
        "tags": [],
        "raw": {
            "suspicious": suspicious,
            "blacklisted": blacklisted,
            "spam": spam,
            "reputation": reputation,
            "references": 5,
            "profiles": [],
        },
    }


def _holehe_finding(site: str) -> dict:  # type: ignore[type-arg]
    return {
        "title": f"Account found: {site}",
        "description": None,
        "tags": [],
        "raw": {"site": site},
    }


@pytest.mark.asyncio
async def test_blacklisted_email_emits_medium_signal() -> None:
    service = AccountEnumerationRiskService()
    with (
        patch(
            "backend.app.modules.identity.account_enumeration_risk.service.EmailrepProvider.get_reputation",
            return_value=[_emailrep_finding(blacklisted=True)],
        ),
        patch(
            "backend.app.modules.identity.account_enumeration_risk.service.HoleheProvider.check_accounts_tool",
            return_value=[],
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="bad@example.com",
        )

    assert len(outcome.signals) == 1
    s = outcome.signals[0]
    assert s.signal_type == "account_enumeration_risk"
    assert s.severity == Severity.MEDIUM
    assert s.provider == "emailrep"
    assert s.entity_type == EntityType.EMAIL
    assert s.evidence["blacklisted"] is True


@pytest.mark.asyncio
async def test_suspicious_email_emits_medium_signal() -> None:
    service = AccountEnumerationRiskService()
    with (
        patch(
            "backend.app.modules.identity.account_enumeration_risk.service.EmailrepProvider.get_reputation",
            return_value=[_emailrep_finding(suspicious=True)],
        ),
        patch(
            "backend.app.modules.identity.account_enumeration_risk.service.HoleheProvider.check_accounts_tool",
            return_value=[],
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="suspicious@example.com",
        )

    assert len(outcome.signals) == 1
    assert outcome.signals[0].severity == Severity.MEDIUM
    assert outcome.signals[0].evidence["suspicious"] is True


@pytest.mark.asyncio
async def test_spam_email_emits_low_signal() -> None:
    service = AccountEnumerationRiskService()
    with (
        patch(
            "backend.app.modules.identity.account_enumeration_risk.service.EmailrepProvider.get_reputation",
            return_value=[_emailrep_finding(spam=True)],
        ),
        patch(
            "backend.app.modules.identity.account_enumeration_risk.service.HoleheProvider.check_accounts_tool",
            return_value=[],
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="spammer@example.com",
        )

    assert len(outcome.signals) == 1
    s = outcome.signals[0]
    assert s.severity == Severity.LOW
    assert s.provider == "emailrep"


@pytest.mark.asyncio
async def test_clean_email_emits_no_signal() -> None:
    service = AccountEnumerationRiskService()
    with (
        patch(
            "backend.app.modules.identity.account_enumeration_risk.service.EmailrepProvider.get_reputation",
            return_value=[_emailrep_finding()],
        ),
        patch(
            "backend.app.modules.identity.account_enumeration_risk.service.HoleheProvider.check_accounts_tool",
            return_value=[],
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="clean@example.com",
        )

    assert outcome.signals == []


@pytest.mark.asyncio
async def test_holehe_three_accounts_emits_enumeration_signal() -> None:
    service = AccountEnumerationRiskService()
    with (
        patch(
            "backend.app.modules.identity.account_enumeration_risk.service.EmailrepProvider.get_reputation",
            return_value=[_emailrep_finding()],
        ),
        patch(
            "backend.app.modules.identity.account_enumeration_risk.service.HoleheProvider.check_accounts_tool",
            return_value=[
                _holehe_finding("twitter"),
                _holehe_finding("instagram"),
                _holehe_finding("github"),
            ],
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="user@example.com",
        )

    assert len(outcome.signals) == 1
    s = outcome.signals[0]
    assert s.signal_type == "account_enumeration_risk"
    assert s.provider == "tool_holehe"
    assert s.severity == Severity.LOW
    assert s.evidence["account_count"] == 3


@pytest.mark.asyncio
async def test_holehe_two_accounts_does_not_emit_signal() -> None:
    service = AccountEnumerationRiskService()
    with (
        patch(
            "backend.app.modules.identity.account_enumeration_risk.service.EmailrepProvider.get_reputation",
            return_value=[_emailrep_finding()],
        ),
        patch(
            "backend.app.modules.identity.account_enumeration_risk.service.HoleheProvider.check_accounts_tool",
            return_value=[_holehe_finding("twitter"), _holehe_finding("instagram")],
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="user@example.com",
        )

    assert outcome.signals == []


@pytest.mark.asyncio
async def test_both_emailrep_and_holehe_can_emit_signals() -> None:
    service = AccountEnumerationRiskService()
    with (
        patch(
            "backend.app.modules.identity.account_enumeration_risk.service.EmailrepProvider.get_reputation",
            return_value=[_emailrep_finding(blacklisted=True)],
        ),
        patch(
            "backend.app.modules.identity.account_enumeration_risk.service.HoleheProvider.check_accounts_tool",
            return_value=[
                _holehe_finding("twitter"),
                _holehe_finding("instagram"),
                _holehe_finding("github"),
            ],
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="risky@example.com",
        )

    assert len(outcome.signals) == 2
    providers = {s.provider for s in outcome.signals}
    assert "emailrep" in providers
    assert "tool_holehe" in providers
