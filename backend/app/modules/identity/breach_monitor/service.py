# backend/app/modules/identity/breach_monitor/service.py
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
        api_key = (
            settings.hibp_api_key.get_secret_value() if settings.hibp_api_key else ""
        )
        provider = HibpProvider(api_key=api_key)
        try:
            findings: list[dict[str, Any]] = await provider.search_breaches(
                email=asset_value
            )
        except ProviderError as e:
            logger.error(
                "breach_monitor.provider_failure", error=str(e), asset_value=asset_value
            )
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

        logger.info(
            "breach_monitor.completed",
            user_id=str(user_id),
            signals_emitted=len(signals),
        )
        return signals
