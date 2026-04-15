# backend/app/modules/domain/dns_intelligence/service.py
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.outcome import ModuleOutcome
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.runner import run_provider
from backend.app.providers.domain.whois.client import WhoisProvider
from backend.app.signals.schemas import SignalCreate

if TYPE_CHECKING:
    from backend.app.jobs.context import ScanExecutionContext

logger = get_logger(__name__)


class DomainDNSIntelligenceService(BaseModuleService):
    module_name = "domain_dns_intelligence"
    module_domain = "domain"
    required_entity_types = [EntityType.DOMAIN]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
        ctx: ScanExecutionContext | None = None,
    ) -> ModuleOutcome:
        signals: list[SignalCreate] = []

        whois_key = (
            settings.whoisxmlapi_api_key.get_secret_value()
            if settings.whoisxmlapi_api_key
            else ""
        )
        whois_provider = WhoisProvider(api_key=whois_key)
        whois_result = await run_provider(
            provider_name="whois",
            call=lambda: whois_provider.lookup_whois(domain=asset_value),
            has_credentials=bool(whois_key),
            user_id=user_id,
            entity_type="domain",
            entity_value=asset_value,
            ctx=ctx,
        )

        for finding in whois_result.findings:
            signals.append(
                SignalCreate(
                    signal_type="domain_whois_info",
                    category="infrastructure_intelligence",
                    entity_type=EntityType.DOMAIN,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.INFO,
                    confidence=Confidence.HIGH,
                    source=self.module_name,
                    provider="whois",
                    summary=finding["title"],
                    details=finding["description"],
                    evidence={"raw_finding": finding},
                    tags=finding.get("tags", []) + ["domain", "whois", "passive"],
                    recommended_action=(
                        "Review WHOIS registration details for anomalies such as "
                        "recent re-registration, privacy-protected registrant, or "
                        "imminent expiry."
                    ),
                    source_ref=f"whois:{asset_value}",
                )
            )

        logger.info(
            "domain_dns_intelligence.completed",
            user_id=str(user_id),
            domain=asset_value,
            signals_emitted=len(signals),
        )
        return ModuleOutcome(signals=signals)
