# backend/app/modules/identity/alias_correlation/service.py
import uuid

from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.base.runner import run_provider
from backend.app.providers.social.emailformat.client import EmailformatProvider
from backend.app.providers.tools.whatsmyname.client import WhatsmyNameProvider
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)


class AliasCorrelationService(BaseModuleService):
    module_name = "alias_correlation"
    module_domain = "identity"
    required_entity_types = [EntityType.EMAIL]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
        ctx: object = None,
    ) -> list[SignalCreate]:
        signals: list[SignalCreate] = []

        # --- EmailFormat: domain email-pattern enrichment (enrichment only) ---
        domain = asset_value.split("@", 1)[-1] if "@" in asset_value else ""
        emailformat_formats: list[dict] = []
        if domain:
            ef = EmailformatProvider()
            try:
                emailformat_formats = await ef.get_formats(domain)
            except ProviderError as e:
                logger.error(
                    "alias_correlation.emailformat_failure",
                    error=str(e),
                    domain=domain,
                )

        # --- WhatsmyName: cross-platform username enumeration for alias linkage ---
        username_prefix = asset_value.split("@", 1)[0]
        if not username_prefix:
            return signals

        wmn_provider = WhatsmyNameProvider()
        wmn_result = await run_provider(
            provider_name="tool_whatsmyname",
            call=lambda: wmn_provider.search_username(username_prefix),
            has_credentials=True,
            user_id=user_id,
            entity_type="email",
            entity_value=asset_value,
            ctx=ctx,
        )

        for finding in wmn_result.findings:
            raw = finding.get("raw", {})
            platform = (
                raw.get("site", "") if isinstance(raw, dict) else ""
            ) or finding.get("title", "").replace("Username found: ", "")
            profile_url = raw.get("url") if isinstance(raw, dict) else None

            evidence: dict = {
                "source_provider": "tool_whatsmyname",
                "username": username_prefix,
                "platform": platform,
                "profile_url": profile_url,
                "alias_detected": True,
            }
            if emailformat_formats:
                evidence["emailformat_patterns"] = emailformat_formats

            signals.append(
                SignalCreate(
                    signal_type="alias_exposure_detected",
                    category="identity_security",
                    entity_type=EntityType.EMAIL,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.LOW,
                    confidence=Confidence.HIGH,
                    source=self.module_name,
                    provider="tool_whatsmyname",
                    summary=(
                        f"Username alias '{username_prefix}' found on "
                        f"{platform} — identity linkage risk"
                    ),
                    details=finding.get("description"),
                    evidence=evidence,
                    tags=["alias_exposure", "whatsmyname", "username_linkage"],
                    recommended_action=(
                        "Review linked accounts. "
                        "Consider using separate usernames per platform "
                        "to reduce identity correlation risk."
                    ),
                    source_ref=f"whatsmyname:{platform}",
                )
            )

        logger.info(
            "alias_correlation.completed",
            user_id=str(user_id),
            signals_emitted=len(signals),
        )
        return signals
