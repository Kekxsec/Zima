# tests/integration/test_module_runner_inventory.py
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.db.repositories.assets import AssetRepository
from backend.app.db.repositories.discovered_accounts import DiscoveredAccountRepository
from backend.app.db.repositories.service_registry import ServiceRegistryRepository
from backend.app.db.repositories.signals import SignalRepository
from backend.app.jobs.runner import ModuleRunner
from backend.app.modules.base.outcome import ModuleOutcome
from backend.app.modules.base.service import BaseModuleService
from backend.app.signals.schemas import SignalCreate
from tests.factories import AssetFactory, UserFactory


class FakeInventoryModule(BaseModuleService):
    module_name = "fake_inventory"
    module_domain = "identity"
    required_entity_types = [EntityType.EMAIL]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
        ctx: object = None,
    ) -> ModuleOutcome:
        account_signal = SignalCreate(
            signal_type="account_discovered",
            category="identity_inventory",
            entity_type=EntityType.EMAIL,
            entity_id=asset_id,
            entity_value=asset_value,
            user_id=user_id,
            severity=Severity.INFO,
            confidence=Confidence.HIGH,
            source="account_inventory",
            provider="tool_holehe",
            summary="Account found registered on GitHub",
            details=None,
            evidence={"platform": "GitHub", "profile_url": None},
            tags=["account_discovered"],
            recommended_action=None,
            source_ref="holehe:github",
        )
        regular_signal = SignalCreate(
            signal_type="email_breached",
            category="identity_security",
            entity_type=EntityType.EMAIL,
            entity_id=asset_id,
            entity_value=asset_value,
            user_id=user_id,
            severity=Severity.HIGH,
            confidence=Confidence.HIGH,
            source="breach_monitor",
            provider="hibp",
            summary="Email found in breach",
            details=None,
            evidence={"breach_name": "Example"},
            tags=["breach"],
            recommended_action=None,
            source_ref="hibp:example",
        )
        return ModuleOutcome(
            signals=[regular_signal],
            account_signals=[account_signal],
        )


@pytest.mark.asyncio
async def test_runner_persists_scan_inventory_as_accounts_not_signals(
    db_session: AsyncSession,
) -> None:
    user = UserFactory.build(tier="plus")
    db_session.add(user)
    asset = AssetFactory.build(
        user_id=user.id,
        entity_type="email",
        value="inventory@example.com",
        is_verified=True,
        is_primary=True,
    )
    db_session.add(asset)
    await db_session.commit()

    runner = ModuleRunner(
        asset_repo=AssetRepository(db_session),
        signal_repo=SignalRepository(db_session),
        account_repo=DiscoveredAccountRepository(db_session),
        service_registry_repo=ServiceRegistryRepository(db_session),
    )

    count = await runner._run_module(FakeInventoryModule(), user.id)
    await db_session.commit()

    accounts = await DiscoveredAccountRepository(db_session).list_for_user(user.id)
    signals = await SignalRepository(db_session).get_open_for_user(user.id)

    assert count == 1
    assert len(accounts) == 1
    assert accounts[0].service_name == "github"
    assert accounts[0].source_type == "holehe"
    assert len(signals) == 1
    assert signals[0].signal_type == "email_breached"
