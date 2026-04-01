# backend/app/modules/identity/account_inventory/service.py
import uuid

from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.tools.holehe.client import HoleheProvider
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)


class AccountInventoryService(BaseModuleService):
    module_name = "account_inventory"
    module_domain = "identity"
    required_entity_types = [EntityType.EMAIL]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
    ) -> list[SignalCreate]:
        signals: list[SignalCreate] = []

        # --- Holehe: email-to-platform account confirmation ---
        holehe = HoleheProvider()
        try:
            findings = await holehe.check_accounts_tool(asset_value)
        except ProviderError as e:
            logger.error(
                "account_inventory.holehe_failure",
                error=str(e),
                asset_value=asset_value,
            )
            findings = []

        for finding in findings:
            raw = finding.get("raw", {})
            platform = raw.get("site", "") if isinstance(raw, dict) else ""
            if not platform:
                platform = finding.get("title", "unknown platform").replace(
                    "Account found: ", ""
                )

            signals.append(
                SignalCreate(
                    signal_type="account_discovered",
                    category="identity_inventory",
                    entity_type=EntityType.EMAIL,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.INFO,
                    confidence=Confidence.HIGH,
                    source=self.module_name,
                    provider="tool_holehe",
                    summary=f"Account found registered on {platform}",
                    details=finding.get("description"),
                    evidence={
                        "source_provider": "tool_holehe",
                        "platform": platform,
                        "profile_url": None,
                        "registration_confirmed": True,
                    },
                    tags=["account_discovered", "holehe", "account_inventory"],
                    recommended_action=(
                        "Review and secure the discovered account. "
                        "Close dormant accounts. Enable MFA where available."
                    ),
                    source_ref=f"holehe:{platform}",
                )
            )

        logger.info(
            "account_inventory.completed",
            user_id=str(user_id),
            signals_emitted=len(signals),
        )
        return signals
