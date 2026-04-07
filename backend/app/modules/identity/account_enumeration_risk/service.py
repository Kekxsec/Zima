# backend/app/modules/identity/account_enumeration_risk/service.py
import uuid

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.runner import run_provider
from backend.app.providers.reputation.emailrep.client import EmailrepProvider
from backend.app.providers.tools.holehe.client import HoleheProvider
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)

_HOLEHE_PROVIDER_NAME = "tool_holehe"


def _severity_for_emailrep(
    suspicious: bool, blacklisted: bool, spam: bool
) -> Severity | None:
    if blacklisted or suspicious:
        return Severity.MEDIUM
    if spam:
        return Severity.LOW
    return None


class AccountEnumerationRiskService(BaseModuleService):
    module_name = "account_enumeration_risk"
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

        emailrep_key = (
            settings.emailrep_api_key.get_secret_value()
            if settings.emailrep_api_key
            else ""
        )
        provider = EmailrepProvider(api_key=emailrep_key)

        # emailrep has a free anonymous tier — always has_credentials=True
        result = await run_provider(
            provider_name="emailrep",
            call=lambda: provider.get_reputation(asset_value),
            has_credentials=True,
            user_id=user_id,
            entity_type="email",
            entity_value=asset_value,
            ctx=ctx,
        )

        for finding in result.findings:
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
                continue

            signals.append(
                SignalCreate(
                    signal_type="account_enumeration_risk",
                    category="identity_security",
                    entity_type=EntityType.EMAIL,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=severity,
                    confidence=Confidence.MEDIUM,
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

        # --- Holehe: account count as enumeration surface indicator ---
        holehe_provider = HoleheProvider()
        holehe_result = await run_provider(
            provider_name=_HOLEHE_PROVIDER_NAME,
            call=lambda: holehe_provider.check_accounts_tool(asset_value),
            has_credentials=True,
            user_id=user_id,
            entity_type="email",
            entity_value=asset_value,
            ctx=ctx,
        )

        if holehe_result.success and holehe_result.findings:
            account_count = len(holehe_result.findings)
            # Only emit a risk signal when the account footprint is large enough
            # to represent a meaningful enumeration surface (≥3 services).
            if account_count >= 3:
                signals.append(
                    SignalCreate(
                        signal_type="account_enumeration_risk",
                        category="identity_security",
                        entity_type=EntityType.EMAIL,
                        entity_id=asset_id,
                        entity_value=asset_value,
                        user_id=user_id,
                        severity=Severity.LOW,
                        confidence=Confidence.HIGH,
                        source=self.module_name,
                        provider=_HOLEHE_PROVIDER_NAME,
                        summary=(
                            f"Email registered on {account_count} services "
                            "— large enumeration surface"
                        ),
                        details=(
                            f"Holehe found {account_count} registered accounts, "
                            "increasing the risk of targeted enumeration attacks."
                        ),
                        evidence={
                            "source_provider": _HOLEHE_PROVIDER_NAME,
                            "account_count": account_count,
                            "sites": [
                                f.get("raw", {}).get("site", "")
                                for f in holehe_result.findings
                                if isinstance(f.get("raw"), dict)
                            ],
                        },
                        tags=[
                            "account_enumeration_risk",
                            "holehe",
                            "email_footprint",
                        ],
                        recommended_action=(
                            "Reduce your account footprint by closing dormant "
                            "accounts. Use email aliases for new registrations."
                        ),
                    )
                )

        logger.info(
            "account_enumeration_risk.completed",
            user_id=str(user_id),
            signals_emitted=len(signals),
        )
        return signals
