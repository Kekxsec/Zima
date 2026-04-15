# backend/app/modules/domain/domain_reputation/service.py
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.outcome import ModuleOutcome
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.runner import run_provider
from backend.app.providers.threat_intel.virustotal.client import VirusTotalProvider
from backend.app.signals.schemas import SignalCreate

if TYPE_CHECKING:
    from backend.app.jobs.context import ScanExecutionContext

logger = get_logger(__name__)

_CRITICAL_THRESHOLD = 5  # 5+ malicious engines → CRITICAL
_HIGH_CONFIDENCE_MIN = 3  # 3+ malicious engines → HIGH confidence
_MEDIUM_CONFIDENCE_MIN = 1  # 1–2 malicious engines → MEDIUM confidence
# 0 malicious but ≥1 suspicious → LOW confidence


class DomainReputationService(BaseModuleService):
    module_name = "domain_reputation"
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

        vt_key = (
            settings.virustotal_api_key.get_secret_value()
            if settings.virustotal_api_key
            else ""
        )
        vt_provider = VirusTotalProvider(api_key=vt_key)
        vt_result = await run_provider(
            provider_name="virustotal",
            call=lambda: vt_provider.get_report(domain=asset_value),
            has_credentials=bool(vt_key),
            user_id=user_id,
            entity_type="domain",
            entity_value=asset_value,
            ctx=ctx,
        )

        for finding in vt_result.findings:
            # ProviderFinding TypedDict only has title/description/tags/raw/evidence.
            # VirusTotal mapper stores extra fields (malicious_count) at the top level
            # of the finding dict — cast once to access them without per-line ignores.
            _f: dict[str, Any] = finding  # type: ignore[assignment]
            malicious_count: int = int(_f.get("malicious_count") or 0)
            severity = (
                Severity.CRITICAL
                if malicious_count >= _CRITICAL_THRESHOLD
                else Severity.HIGH
            )
            if malicious_count >= _HIGH_CONFIDENCE_MIN:
                confidence = Confidence.HIGH
            elif malicious_count >= _MEDIUM_CONFIDENCE_MIN:
                confidence = Confidence.MEDIUM
            else:
                # 0 malicious but suspicious engines triggered this finding
                confidence = Confidence.LOW
            signals.append(
                SignalCreate(
                    signal_type="domain_reputation_risk",
                    category="infrastructure_security",
                    entity_type=EntityType.DOMAIN,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=severity,
                    confidence=confidence,
                    source=self.module_name,
                    provider="virustotal",
                    summary=_f["title"],
                    details=_f.get("description"),
                    evidence={"raw_finding": finding},
                    tags=_f.get("tags", []) + ["domain", "reputation"],
                    recommended_action=(
                        "Investigate this domain for malware hosting, phishing, or "
                        "C2 activity. Consider blocking at DNS or firewall level and "
                        "reviewing any traffic to/from this domain."
                    ),
                    source_ref=f"virustotal:domain:{asset_value}",
                )
            )

        logger.info(
            "domain_reputation.completed",
            user_id=str(user_id),
            domain=asset_value,
            signals_emitted=len(signals),
        )
        return ModuleOutcome(signals=signals)
