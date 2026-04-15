# backend/app/modules/identity/phone_exposure/service.py
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.outcome import ModuleOutcome
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.runner import run_provider
from backend.app.providers.phone.callername.client import CallerNameProvider
from backend.app.providers.phone.numverify.client import NumverifyProvider
from backend.app.signals.schemas import SignalCreate

if TYPE_CHECKING:
    from backend.app.jobs.context import ScanExecutionContext

logger = get_logger(__name__)


class PhoneExposureService(BaseModuleService):
    """Validates and enriches PHONE_NUMBER assets.

    Runs numverify (carrier/country/line-type) and CallerName
    (reputation + geolocation) against each verified phone number asset.
    """

    module_name = "phone_exposure"
    module_domain = "identity"
    required_entity_types = [EntityType.PHONE_NUMBER]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
        ctx: ScanExecutionContext | None = None,
    ) -> ModuleOutcome:
        signals: list[SignalCreate] = []

        # --- Numverify: validation + carrier + line type ---
        nv_has_creds = bool(settings.numverify_api_key)
        if nv_has_creds:
            nv_provider = NumverifyProvider(
                api_key=settings.numverify_api_key.get_secret_value()  # type: ignore[union-attr]
            )
        else:
            nv_provider = None

        nv_result = await run_provider(
            provider_name="numverify",
            call=lambda: nv_provider.validate_phone(asset_value),  # type: ignore[union-attr]
            has_credentials=nv_has_creds,
            user_id=user_id,
            entity_type="phone",
            entity_value=asset_value,
            ctx=ctx,
        )

        for finding in nv_result.findings:
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
                        f"Phone {asset_value} validated: {line_type} in " f"{country}"
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

        # --- CallerName: reputation + geolocation (US numbers only) ---
        cn_provider = CallerNameProvider()
        cn_result = await run_provider(
            provider_name="callername",
            call=lambda: cn_provider.get_caller_info(asset_value),
            has_credentials=True,
            user_id=user_id,
            entity_type="phone",
            entity_value=asset_value,
            ctx=ctx,
        )

        for finding in cn_result.findings:
            raw = finding.get("raw", {})
            category = finding.get("category", "")
            if not isinstance(raw, dict):
                continue

            if category == "reputation" and raw.get("bad_votes", 0) > raw.get(
                "good_votes", 0
            ):
                signals.append(
                    SignalCreate(
                        signal_type="phone_flagged_unsafe",
                        category="identity_exposure",
                        entity_type=EntityType.PHONE_NUMBER,
                        entity_id=asset_id,
                        entity_value=asset_value,
                        user_id=user_id,
                        severity=Severity.MEDIUM,
                        confidence=Confidence.MEDIUM,
                        source=self.module_name,
                        provider="callername",
                        summary=(
                            f"Phone {asset_value} flagged as unsafe by "
                            "community votes on CallerName"
                        ),
                        details=finding.get("description"),
                        evidence={
                            "source_provider": "callername",
                            "good_votes": raw.get("good_votes", 0),
                            "bad_votes": raw.get("bad_votes", 0),
                        },
                        tags=["callername", "phone", "reputation", "passive"],
                        recommended_action=(
                            "Investigate whether this phone number has been "
                            "associated with spam or fraud reports."
                        ),
                        source_ref=f"callername:reputation:{asset_value}",
                    )
                )
            elif category == "identity_exposure" and raw.get("location"):
                signals.append(
                    SignalCreate(
                        signal_type="phone_location_exposed",
                        category="identity_inventory",
                        entity_type=EntityType.PHONE_NUMBER,
                        entity_id=asset_id,
                        entity_value=asset_value,
                        user_id=user_id,
                        severity=Severity.INFO,
                        confidence=Confidence.MEDIUM,
                        source=self.module_name,
                        provider="callername",
                        summary=(
                            f"Phone {asset_value} geolocated to "
                            f"{raw.get('location', 'unknown')}"
                        ),
                        details=finding.get("description"),
                        evidence={
                            "source_provider": "callername",
                            "location": raw.get("location"),
                            "phone": asset_value,
                        },
                        tags=["callername", "phone", "geolocation", "passive"],
                        recommended_action=(
                            "No action required. Location data is informational."
                        ),
                        source_ref=f"callername:location:{asset_value}",
                    )
                )

        logger.info(
            "phone_exposure.completed",
            user_id=str(user_id),
            phone=asset_value,
            signals_emitted=len(signals),
        )
        return ModuleOutcome(signals=signals)
