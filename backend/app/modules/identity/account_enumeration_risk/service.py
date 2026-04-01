# backend/app/modules/identity/account_enumeration_risk/service.py
import uuid

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.reputation.emailrep.client import EmailrepProvider
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)


def _severity_for_emailrep(
    suspicious: bool, blacklisted: bool, spam: bool
) -> Severity | None:
    # TODO: calibrate after first 1000 scans
    if blacklisted or suspicious:
        return Severity.MEDIUM
    if spam:
        return Severity.LOW
    return None  # no risk indicators — no signal


class AccountEnumerationRiskService(BaseModuleService):
    module_name = "account_enumeration_risk"
    module_domain = "identity"
    required_entity_types = [EntityType.EMAIL]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
    ) -> list[SignalCreate]:
        signals: list[SignalCreate] = []

        emailrep_key = (
            settings.emailrep_api_key.get_secret_value()
            if settings.emailrep_api_key
            else ""
        )
        provider = EmailrepProvider(api_key=emailrep_key)
        try:
            findings = await provider.get_reputation(asset_value)
        except ProviderError as e:
            logger.error(
                "account_enumeration_risk.provider_failure",
                error=str(e),
                asset_value=asset_value,
            )
            return signals

        for finding in findings:
            raw = finding.get("raw", {})
            if not isinstance(raw, dict):
                continue

            suspicious = bool(raw.get("suspicious", False))
            blacklisted = bool(raw.get("blacklisted", False))
            spam = bool(raw.get("spam", False))
            reputation = str(raw.get("reputation", ""))
            references = int(raw.get("references") or 0)
            profiles: list[str] = (
                raw.get("profiles", []) if isinstance(raw.get("profiles"), list) else []
            )

            severity = _severity_for_emailrep(suspicious, blacklisted, spam)
            if severity is None:
                continue  # clean reputation — no signal

            signals.append(
                SignalCreate(
                    signal_type="account_enumeration_risk",
                    category="identity_security",
                    entity_type=EntityType.EMAIL,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=severity,
                    confidence=(
                        Confidence.MEDIUM
                    ),  # TODO: calibrate after first 1000 scans
                    source=self.module_name,
                    provider="emailrep",
                    summary="Email reputation flagged as suspicious or blacklisted",
                    details=finding.get("description"),
                    evidence={
                        "source_provider": "emailrep",
                        "reputation_score": reputation,
                        "suspicious": suspicious,
                        "spam": spam,
                        "blacklisted": blacklisted,
                        "references": references,
                        "profiles": profiles,
                    },
                    tags=["account_enumeration_risk", "emailrep", "email_reputation"],
                    recommended_action=(
                        "Investigate email reputation flags. "
                        "Check for signs of spam or abuse from this address. "
                        "Review account activity."
                    ),
                )
            )

        logger.info(
            "account_enumeration_risk.completed",
            user_id=str(user_id),
            signals_emitted=len(signals),
        )
        return signals
