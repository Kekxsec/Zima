# backend/app/modules/identity/darkweb_identity_monitor/service.py
"""Dark web identity monitor — powered by IntelX."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.outcome import ModuleOutcome
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.runner import run_provider
from backend.app.providers.threat_intel.intelx.client import IntelXProvider
from backend.app.signals.schemas import SignalCreate

if TYPE_CHECKING:
    from backend.app.jobs.context import ScanExecutionContext

logger = get_logger(__name__)

_PROVIDER_NAME = "intelx"


class DarkwebIdentityMonitorService(BaseModuleService):
    """Searches IntelX dark web indexes for leaked identity records.

    Runs against EMAIL assets. Emits a ``darkweb_identity_exposure`` signal
    for each matching record found.
    """

    module_name = "darkweb_identity_monitor"
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

        if not settings.intelx_api_key:
            logger.debug(
                "darkweb_identity_monitor.skipped",
                reason="INTELX_API_KEY not configured",
            )
            return ModuleOutcome(signals=signals)

        api_key = settings.intelx_api_key.get_secret_value()
        provider = IntelXProvider(api_key=api_key)

        result = await run_provider(
            provider_name=_PROVIDER_NAME,
            call=lambda: provider.search(asset_value),
            has_credentials=True,
            user_id=user_id,
            entity_type="email",
            entity_value=asset_value,
            ctx=ctx,
            check_quota=True,
        )

        if not result.success:
            return ModuleOutcome(signals=signals)

        for finding in result.findings:
            raw: dict[str, Any] = (
                finding.get("raw", {}) if isinstance(finding.get("raw"), dict) else {}
            )

            # Determine if this record contains credential-level data.
            # IntelX media type 1 = pastes (often credentials), type 13 = darkweb.
            media_type: int = int(raw.get("media", 0) or 0)
            has_credentials = media_type in (1, 13)

            severity = Severity.CRITICAL if has_credentials else Severity.HIGH

            signals.append(
                SignalCreate(
                    signal_type="darkweb_identity_exposure",
                    category="identity_security",
                    entity_type=EntityType.EMAIL,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=severity,
                    confidence=Confidence.MEDIUM,
                    source=self.module_name,
                    provider=_PROVIDER_NAME,
                    summary=finding.get("title", "Dark web record found"),
                    details=finding.get("description"),
                    evidence={
                        "source_provider": _PROVIDER_NAME,
                        "record_id": raw.get("storageid"),
                        "media_type": media_type,
                        "bucket": raw.get("bucket"),
                        "date": raw.get("date"),
                        "has_credentials": has_credentials,
                        "raw_finding": finding,
                    },
                    tags=["darkweb", "intelx", "identity_leak"],
                    recommended_action=(
                        "Rotate all passwords associated with this identity "
                        "immediately. "
                        "Enable MFA on all accounts. "
                        "Monitor for fraudulent use of your identity."
                    ),
                    source_ref=f"intelx:{raw.get('storageid', 'unknown')}",
                )
            )

        logger.info(
            "darkweb_identity_monitor.completed",
            user_id=str(user_id),
            signals_emitted=len(signals),
        )
        return ModuleOutcome(signals=signals)
