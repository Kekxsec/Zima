# backend/app/modules/identity/alias_correlation/service.py
import uuid

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.social.epieos.client import EpieosProvider
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
    ) -> list[SignalCreate]:
        signals: list[SignalCreate] = []

        if not settings.epieos_api_key:
            return signals

        epieos = EpieosProvider(api_key=settings.epieos_api_key.get_secret_value())
        try:
            findings = await epieos.validate_email(asset_value)
        except ProviderError as e:
            logger.error(
                "alias_correlation.provider_failure",
                error=str(e),
                asset_value=asset_value,
            )
            return signals

        for finding in findings:
            raw = finding.get("raw", {})
            if not isinstance(raw, dict):
                continue

            # Emit alias_exposure_detected when a real name is linked to the
            # email via a confirmed Google account.
            if "google" not in finding.get("title", "").lower():
                continue

            alias_name = str(raw.get("name", "")).strip()
            if not alias_name:
                continue

            signals.append(
                SignalCreate(
                    signal_type="alias_exposure_detected",
                    category="identity_security",
                    entity_type=EntityType.EMAIL,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.LOW,  # TODO: calibrate after first 1000 scans
                    confidence=(
                        Confidence.MEDIUM
                    ),  # TODO: calibrate after first 1000 scans
                    source=self.module_name,
                    provider="epieos",
                    summary=(
                        f"Alias '{alias_name}' linked to this identity via "
                        "Google account"
                    ),
                    details=finding.get("description"),
                    evidence={
                        "source_provider": "epieos",
                        "alias_email": alias_name,  # real name exposed as alias
                        "platform": "Google",
                    },
                    tags=["alias_exposure", "epieos", "identity_linkage"],
                    recommended_action=(
                        "Review alias email and linked accounts. "
                        "Check if alias appears in any breach records."
                    ),
                )
            )

        logger.info(
            "alias_correlation.completed",
            user_id=str(user_id),
            signals_emitted=len(signals),
        )
        return signals
