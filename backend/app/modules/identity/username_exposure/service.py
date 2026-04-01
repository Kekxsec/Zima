# backend/app/modules/identity/username_exposure/service.py
import uuid

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.social.epieos.client import EpieosProvider
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)


class UsernameExposureService(BaseModuleService):
    module_name = "username_exposure"
    module_domain = "identity"
    required_entity_types = [EntityType.EMAIL]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
    ) -> list[SignalCreate]:
        signals: list[SignalCreate] = []

        # --- Epieos: confirmed Google/Apple account linkage ---
        if settings.epieos_api_key:
            epieos = EpieosProvider(api_key=settings.epieos_api_key.get_secret_value())
            try:
                findings = await epieos.validate_email(asset_value)
            except ProviderError as e:
                logger.error(
                    "username_exposure.epieos_failure",
                    error=str(e),
                    asset_value=asset_value,
                )
                findings = []

            for finding in findings:
                raw = finding.get("raw", {})
                # Google account: platform = "google", username = email local-part
                if "google" in finding.get("title", "").lower():
                    platform = "Google"
                    google_id = raw.get("google_id") if isinstance(raw, dict) else None
                    username = (
                        asset_value.split("@")[0] if "@" in asset_value else asset_value
                    )
                    signals.append(
                        SignalCreate(
                            signal_type="username_exposure",
                            category="identity_inventory",
                            entity_type=EntityType.EMAIL,
                            entity_id=asset_id,
                            entity_value=asset_value,
                            user_id=user_id,
                            severity=Severity.INFO,
                            confidence=Confidence.HIGH,
                            source=self.module_name,
                            provider="epieos",
                            summary=(
                                f"Username '{username}' linked to this email "
                                f"on {platform}"
                            ),
                            details=finding.get("description"),
                            evidence={
                                "source_provider": "epieos",
                                "username": username,
                                "platform": platform,
                                "profile_url": f"https://google.com/maps/contrib/{google_id}"
                                if google_id
                                else None,
                                "confirmed": True,
                            },
                            tags=["username_exposure", "epieos", "account_enumeration"],
                            recommended_action=(
                                "Review accounts on discovered platforms. "
                                "Ensure account privacy settings are configured. "
                                "Close dormant accounts."
                            ),
                            source_ref=f"epieos:{platform}",
                        )
                    )
                # Apple ID: platform = "apple"
                elif "apple" in finding.get("title", "").lower():
                    platform = "Apple"
                    username = (
                        asset_value.split("@")[0] if "@" in asset_value else asset_value
                    )
                    signals.append(
                        SignalCreate(
                            signal_type="username_exposure",
                            category="identity_inventory",
                            entity_type=EntityType.EMAIL,
                            entity_id=asset_id,
                            entity_value=asset_value,
                            user_id=user_id,
                            severity=Severity.INFO,
                            confidence=Confidence.HIGH,
                            source=self.module_name,
                            provider="epieos",
                            summary=(
                                f"Username '{username}' linked to this email "
                                f"on {platform}"
                            ),
                            details=finding.get("description"),
                            evidence={
                                "source_provider": "epieos",
                                "username": username,
                                "platform": platform,
                                "confirmed": True,
                            },
                            tags=["username_exposure", "epieos", "account_enumeration"],
                            recommended_action=(
                                "Review accounts on discovered platforms. "
                                "Ensure account privacy settings are configured. "
                                "Close dormant accounts."
                            ),
                            source_ref=f"epieos:{platform}",
                        )
                    )

        # Maigret is intentionally not run against email local-parts.
        # Deriving a username from "alice@example.com" -> "alice" creates
        # high-noise results that are not specific enough to this email.

        logger.info(
            "username_exposure.completed",
            user_id=str(user_id),
            signals_emitted=len(signals),
        )
        return signals
