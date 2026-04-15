# tests/unit/modules/identity/test_account_inventory.py
import uuid
from unittest.mock import patch

import pytest

from backend.app.core.enums import EntityType, Severity
from backend.app.modules.identity.account_inventory.service import (
    AccountInventoryService,
)

USER_ID = uuid.uuid4()
ASSET_ID = uuid.uuid4()


def _holehe_finding(site: str) -> dict:  # type: ignore[type-arg]
    return {
        "title": f"Account found: {site}",
        "description": f"Account registered on {site}",
        "tags": ["holehe"],
        "raw": {"site": site},
    }


def _mailcat_finding(email: str) -> dict:  # type: ignore[type-arg]
    return {
        "title": f"Email discovered: {email}",
        "description": f"Found email alias: {email}",
        "tags": ["mailcat"],
        "raw": {"username": "testuser", "email": email},
    }


def _wmn_finding(site: str, url: str) -> dict:  # type: ignore[type-arg]
    return {
        "title": f"Username found: {site}",
        "description": f"Profile found at {url}",
        "tags": ["whatsmyname"],
        "raw": {"site": site, "url": url, "username": "testuser"},
    }


@pytest.mark.asyncio
async def test_holehe_findings_populate_account_signals() -> None:
    service = AccountInventoryService()
    with (
        patch(
            "backend.app.modules.identity.account_inventory.service.HoleheProvider.check_accounts_tool",
            return_value=[_holehe_finding("twitter"), _holehe_finding("instagram")],
        ),
        patch(
            "backend.app.modules.identity.account_inventory.service.MailcatProvider.find_emails",
            return_value=[],
        ),
        patch(
            "backend.app.modules.identity.account_inventory.service.WhatsmyNameProvider.search_username",
            return_value=[],
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="testuser@example.com",
        )

    assert len(outcome.account_signals) == 2
    assert outcome.signals == []
    s = outcome.account_signals[0]
    assert s.signal_type == "account_discovered"
    assert s.severity == Severity.INFO
    assert s.entity_type == EntityType.EMAIL
    assert s.provider == "tool_holehe"


@pytest.mark.asyncio
async def test_all_providers_empty_returns_no_account_signals() -> None:
    service = AccountInventoryService()
    with (
        patch(
            "backend.app.modules.identity.account_inventory.service.HoleheProvider.check_accounts_tool",
            return_value=[],
        ),
        patch(
            "backend.app.modules.identity.account_inventory.service.MailcatProvider.find_emails",
            return_value=[],
        ),
        patch(
            "backend.app.modules.identity.account_inventory.service.WhatsmyNameProvider.search_username",
            return_value=[],
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="nobody@example.com",
        )

    assert outcome.account_signals == []
    assert outcome.signals == []


@pytest.mark.asyncio
async def test_mailcat_finding_included_in_account_signals() -> None:
    service = AccountInventoryService()
    with (
        patch(
            "backend.app.modules.identity.account_inventory.service.HoleheProvider.check_accounts_tool",
            return_value=[],
        ),
        patch(
            "backend.app.modules.identity.account_inventory.service.MailcatProvider.find_emails",
            return_value=[_mailcat_finding("testuser@gmail.com")],
        ),
        patch(
            "backend.app.modules.identity.account_inventory.service.WhatsmyNameProvider.search_username",
            return_value=[],
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="testuser@example.com",
        )

    assert len(outcome.account_signals) == 1
    s = outcome.account_signals[0]
    assert s.provider == "tool_mailcat"
    assert s.signal_type == "account_discovered"
    assert "testuser@gmail.com" in s.summary


@pytest.mark.asyncio
async def test_whatsmyname_finding_included_in_account_signals() -> None:
    service = AccountInventoryService()
    with (
        patch(
            "backend.app.modules.identity.account_inventory.service.HoleheProvider.check_accounts_tool",
            return_value=[],
        ),
        patch(
            "backend.app.modules.identity.account_inventory.service.MailcatProvider.find_emails",
            return_value=[],
        ),
        patch(
            "backend.app.modules.identity.account_inventory.service.WhatsmyNameProvider.search_username",
            return_value=[_wmn_finding("github", "https://github.com/testuser")],
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="testuser@example.com",
        )

    assert len(outcome.account_signals) == 1
    s = outcome.account_signals[0]
    assert s.provider == "tool_whatsmyname"
    assert s.evidence["profile_url"] == "https://github.com/testuser"


@pytest.mark.asyncio
async def test_signals_aggregated_from_all_three_providers() -> None:
    service = AccountInventoryService()
    with (
        patch(
            "backend.app.modules.identity.account_inventory.service.HoleheProvider.check_accounts_tool",
            return_value=[_holehe_finding("twitter")],
        ),
        patch(
            "backend.app.modules.identity.account_inventory.service.MailcatProvider.find_emails",
            return_value=[_mailcat_finding("testuser@gmail.com")],
        ),
        patch(
            "backend.app.modules.identity.account_inventory.service.WhatsmyNameProvider.search_username",
            return_value=[_wmn_finding("github", "https://github.com/testuser")],
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="testuser@example.com",
        )

    assert len(outcome.account_signals) == 3
    providers = {s.provider for s in outcome.account_signals}
    assert "tool_holehe" in providers
    assert "tool_mailcat" in providers
    assert "tool_whatsmyname" in providers
