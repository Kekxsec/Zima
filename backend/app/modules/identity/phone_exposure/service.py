# backend/app/modules/identity/phone_exposure/service.py
import uuid

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.phone.numverify.client import NumverifyProvider
from backend.app.providers.phone.twilio.client import TwilioProvider
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)


class PhoneExposureService(BaseModuleService):
    """Validates and enriches PHONE_NUMBER assets.

    Runs numverify (carrier/country/line-type) and Twilio Lookup
    (carrier + caller name) against each verified phone number asset.
    Emits an informational inventory signal per confirmed number.
    """

    module_name = "phone_exposure"
    module_domain = "identity"
    required_entity_types = [EntityType.PHONE_NUMBER]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
    ) -> list[SignalCreate]:
        signals: list[SignalCreate] = []

        # --- Numverify: validation + carrier + line type ---
        if settings.numverify_api_key:
            provider = NumverifyProvider(
                api_key=settings.numverify_api_key.get_secret_value()
            )
            try:
                findings = await provider.validate_phone(asset_value)
            except ProviderError as e:
                logger.error(
                    "phone_exposure.numverify_failure",
                    error=str(e),
                    asset_value=asset_value,
                )
                findings = []

            for finding in findings:
                raw = finding.get("raw", {})
                country = raw.get("country", "") if isinstance(raw, dict) else ""
                carrier = raw.get("carrier", "") if isinstance(raw, dict) else ""
                line_type = raw.get("line_type", "") if isinstance(raw, dict) else ""

                signals.append(
                    SignalCreate(
                        signal_type="phone_number_validated",
                        category="identity_inventory",
                        entity_type=EntityType.PHONE_NUMBER,
                        entity_id=asset_id,
                        entity_value=asset_value,
                        user_id=user_id,
                        severity=Severity.INFO,
                        confidence=Confidence.HIGH,
                        source=self.module_name,
                        provider="numverify",
                        summary=(
                            f"Phone {asset_value} validated: {line_type} in "
                            f"{country}"
                        ),
                        details=finding.get("description"),
                        evidence={
                            "source_provider": "numverify",
                            "country": country,
                            "carrier": carrier,
                            "line_type": line_type,
                        },
                        tags=["numverify", "phone", "passive"],
                        recommended_action=(
                            "No action required. This is an informational record of "
                            "your registered phone number's carrier and region."
                        ),
                        source_ref=f"numverify:{asset_value}",
                    )
                )

        # --- Twilio: carrier lookup + caller name ---
        if settings.twilio_account_sid and settings.twilio_auth_token:
            provider_twilio = TwilioProvider(
                account_sid=settings.twilio_account_sid.get_secret_value(),
                auth_token=settings.twilio_auth_token.get_secret_value(),
            )
            try:
                findings_twilio = await provider_twilio.lookup_phone(asset_value)
            except ProviderError as e:
                logger.error(
                    "phone_exposure.twilio_failure",
                    error=str(e),
                    asset_value=asset_value,
                )
                findings_twilio = []

            for finding in findings_twilio:
                raw = finding.get("raw", {})
                carrier_name = raw.get("carrier", "") if isinstance(raw, dict) else ""
                caller_name = (
                    raw.get("caller_name", "") if isinstance(raw, dict) else ""
                )
                line_type = raw.get("line_type", "") if isinstance(raw, dict) else ""

                # Only emit a signal if we got meaningful data beyond basic validation
                if caller_name:
                    signals.append(
                        SignalCreate(
                            signal_type="phone_caller_name_exposed",
                            category="identity_exposure",
                            entity_type=EntityType.PHONE_NUMBER,
                            entity_id=asset_id,
                            entity_value=asset_value,
                            user_id=user_id,
                            severity=Severity.LOW,
                            confidence=Confidence.HIGH,
                            source=self.module_name,
                            provider="twilio",
                            summary=(
                                f"Caller name '{caller_name}' is publicly "
                                f"associated with {asset_value}"
                            ),
                            details=finding.get("description"),
                            evidence={
                                "source_provider": "twilio",
                                "caller_name": caller_name,
                                "carrier": carrier_name,
                                "line_type": line_type,
                            },
                            tags=["twilio", "phone", "caller_name", "passive"],
                            recommended_action=(
                                "Your name is publicly visible in carrier CNAM records "
                                "for this number. Contact your carrier to request CNAM "
                                "suppression if you want to reduce personal exposure."
                            ),
                            source_ref=f"twilio:cnam:{asset_value}",
                        )
                    )
                elif carrier_name:
                    # Carrier-only finding: inventory signal, lower severity
                    signals.append(
                        SignalCreate(
                            signal_type="phone_carrier_identified",
                            category="identity_inventory",
                            entity_type=EntityType.PHONE_NUMBER,
                            entity_id=asset_id,
                            entity_value=asset_value,
                            user_id=user_id,
                            severity=Severity.INFO,
                            confidence=Confidence.HIGH,
                            source=self.module_name,
                            provider="twilio",
                            summary=(
                                f"Phone {asset_value}: {line_type} on "
                                f"{carrier_name}"
                            ),
                            details=finding.get("description"),
                            evidence={
                                "source_provider": "twilio",
                                "carrier": carrier_name,
                                "line_type": line_type,
                            },
                            tags=["twilio", "phone", "passive"],
                            recommended_action=(
                                "No action required. Carrier and line-type data is "
                                "informational."
                            ),
                            source_ref=f"twilio:carrier:{asset_value}",
                        )
                    )

        logger.info(
            "phone_exposure.completed",
            user_id=str(user_id),
            phone=asset_value,
            signals_emitted=len(signals),
        )
        return signals
