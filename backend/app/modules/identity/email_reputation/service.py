# backend/app/modules/identity/email_reputation/service.py
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.outcome import ModuleOutcome
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.runner import run_provider
from backend.app.providers.reputation.emailrep.client import EmailrepProvider
from backend.app.providers.threat_intel.intelx.client import IntelXProvider
from backend.app.signals.schemas import SignalCreate

if TYPE_CHECKING:
    from backend.app.jobs.context import ScanExecutionContext

logger = get_logger(__name__)


def _emailrep_severity(raw: dict[str, Any]) -> Severity:
    """CRITICAL if blacklisted; HIGH if suspicious; MEDIUM if spam only."""
    if raw.get("blacklisted"):
        return Severity.CRITICAL
    if raw.get("suspicious"):
        return Severity.HIGH
    if raw.get("spam"):
        return Severity.MEDIUM
    return Severity.LOW


class EmailReputationService(BaseModuleService):
    module_name = "email_reputation"
    module_domain = "identity"
    required_entity_types = [EntityType.EMAIL]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
        ctx: ScanExecutionContext | None = None,
    ) -> ModuleOutcome:
        signals: list[SignalCreate] = []

        # ── EmailRep ────────────────────────────────────────────────────────
        emailrep_key = (
            settings.emailrep_api_key.get_secret_value()
            if settings.emailrep_api_key
            else ""
        )
        emailrep_provider = EmailrepProvider(api_key=emailrep_key)
        emailrep_result = await run_provider(
            provider_name="emailrep",
            call=lambda: emailrep_provider.get_reputation(email=asset_value),
            has_credentials=True,  # emailrep works without a key (rate-limited)
            user_id=user_id,
            entity_type="email",
            entity_value=asset_value,
            ctx=ctx,
        )

        for finding in emailrep_result.findings:
            raw: dict[str, Any] = (
                finding.get("raw", {}) if isinstance(finding.get("raw"), dict) else {}
            )
            severity = _emailrep_severity(raw)
            # Only emit a signal if there is something worth reporting
            if (
                severity == Severity.LOW
                and not raw.get("suspicious")
                and not raw.get("spam")
                and not raw.get("blacklisted")
            ):
                continue
            signals.append(
                SignalCreate(
                    signal_type="email_reputation_risk",
                    category="identity_security",
                    entity_type=EntityType.EMAIL,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=severity,
                    confidence=Confidence.MEDIUM,
                    source=self.module_name,
                    provider="emailrep",
                    summary=finding.get(
                        "title", f"Email reputation risk: {asset_value}"
                    ),
                    details=finding.get("description"),
                    evidence={"raw_finding": finding},
                    tags=finding.get("tags", []) + ["identity", "reputation"],
                    recommended_action=(
                        "Review the email address reputation. If flagged as"
                        " suspicious or blacklisted, consider rotating the"
                        " address or investigating associated accounts for"
                        " compromise."
                    ),
                    source_ref=f"emailrep:{asset_value}",
                )
            )

        # ── IntelX ──────────────────────────────────────────────────────────
        intelx_key = (
            settings.intelx_api_key.get_secret_value()
            if settings.intelx_api_key
            else ""
        )
        if intelx_key:
            intelx_provider = IntelXProvider(api_key=intelx_key)
            intelx_result = await run_provider(
                provider_name="intelx",
                call=lambda: intelx_provider.search(asset_value),
                has_credentials=True,
                user_id=user_id,
                entity_type="email",
                entity_value=asset_value,
                ctx=ctx,
            )
            for finding in intelx_result.findings:
                signals.append(
                    SignalCreate(
                        signal_type="email_intelx_exposure",
                        category="identity_security",
                        entity_type=EntityType.EMAIL,
                        entity_id=asset_id,
                        entity_value=asset_value,
                        user_id=user_id,
                        severity=Severity.HIGH,
                        confidence=Confidence.MEDIUM,
                        source=self.module_name,
                        provider="intelx",
                        summary=finding.get(
                            "title", f"Email found in IntelligenceX: {asset_value}"
                        ),
                        details=finding.get("description"),
                        evidence={"raw_finding": finding},
                        tags=finding.get("tags", []) + ["identity", "darkweb", "leak"],
                        recommended_action=(
                            "This email address was found in IntelligenceX data"
                            " leak records. Rotate credentials for any associated"
                            " accounts and monitor for further exposure."
                        ),
                        source_ref=f"intelx:{asset_value}",
                    )
                )

        logger.info(
            "email_reputation.completed",
            user_id=str(user_id),
            signals_emitted=len(signals),
        )
        return ModuleOutcome(signals=signals)
