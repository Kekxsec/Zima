# backend/app/modules/identity/stealer_log_exposure/service.py
import uuid

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.runner import run_provider
from backend.app.providers.breach.hudson_rock.client import HudsonRockProvider
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)


class StealerLogExposureService(BaseModuleService):
    module_name = "stealer_log_exposure"
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

        hr_has_creds = bool(settings.hudson_rock_api_key)
        if hr_has_creds:
            provider = HudsonRockProvider(
                api_key=settings.hudson_rock_api_key.get_secret_value()
            )
        else:
            provider = None

        result = await run_provider(
            provider_name="hudson_rock",
            call=lambda: provider.get_compromised_data(email=asset_value),  # type: ignore[union-attr]
            has_credentials=hr_has_creds,
            user_id=user_id,
            entity_type="email",
            entity_value=asset_value,
            ctx=ctx,
            check_quota=True,
        )

        for finding in result.findings:
            raw = finding.get("raw", {})
            computer_name = (
                raw.get("computer_name", "unknown")
                if isinstance(raw, dict)
                else "unknown"
            )
            operating_system = (
                raw.get("operating_system", "unknown")
                if isinstance(raw, dict)
                else "unknown"
            )
            malware_name = (
                raw.get("malware_name", "unknown")
                if isinstance(raw, dict)
                else "unknown"
            )
            cred_count = raw.get("credential_count", 0) if isinstance(raw, dict) else 0
            date_uploaded = (
                raw.get("date_uploaded", "unknown")
                if isinstance(raw, dict)
                else "unknown"
            )

            signals.append(
                SignalCreate(
                    signal_type="stealer_log_hit",
                    category="identity_security",
                    entity_type=EntityType.EMAIL,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.CRITICAL,
                    confidence=Confidence.HIGH,
                    source=self.module_name,
                    provider="hudson_rock",
                    summary=(
                        f"Device infected with {malware_name} — credentials "
                        "exfiltrated and found in stealer log"
                    ),
                    details=finding.get("description"),
                    evidence={
                        "source_provider": "hudson_rock",
                        "stealer_family": malware_name,
                        "date_compromised": date_uploaded,
                        "computer_name": computer_name,
                        "operating_system": operating_system,
                        "credentials_count": cred_count,
                    },
                    tags=finding.get("tags", []) + ["stealer_log", "device_compromise"],
                    recommended_action=(
                        "Assume device is compromised. Perform full credential "
                        "rotation for all accounts. "
                        "Consider wiping and reinstalling the operating system. "
                        "Enable MFA on all critical accounts immediately."
                    ),
                    source_ref=f"hudson_rock:{date_uploaded}",
                )
            )

        logger.info(
            "stealer_log_exposure.completed",
            user_id=str(user_id),
            signals_emitted=len(signals),
        )
        return signals
