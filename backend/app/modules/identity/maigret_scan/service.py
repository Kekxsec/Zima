# backend/app/modules/identity/maigret_scan/service.py
from __future__ import annotations

import hashlib
import uuid
from typing import TYPE_CHECKING

from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.runner import run_provider
from backend.app.providers.tools.maigret.client import MaigretProvider
from backend.app.signals.schemas import SignalCreate

if TYPE_CHECKING:
    from backend.app.jobs.context import ScanExecutionContext

logger = get_logger(__name__)

_PROVIDER_NAME = "tool_maigret"


class MaigretScanService(BaseModuleService):
    """Runs Maigret against explicitly-provided USERNAME assets.

    Only processes EntityType.USERNAME assets — never derives usernames from
    email local-parts. High-volume: Maigret checks 3000+ sites per username.
    """

    module_name = "maigret_scan"
    module_domain = "identity"
    required_entity_types = [EntityType.USERNAME]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
        ctx: ScanExecutionContext | None = None,
    ) -> list[SignalCreate]:
        signals: list[SignalCreate] = []

        # Record audit trail before spawning the subprocess.
        # Entity value is SHA-256 hashed so the log contains no PII.
        if ctx is not None:
            ctx.record_event(
                "local_tool_invoked",
                module=self.module_name,
                provider=_PROVIDER_NAME,
                asset_id=str(asset_id),
                entity_hash=hashlib.sha256(asset_value.encode()).hexdigest(),
            )

        provider = MaigretProvider()

        # run_provider handles policy check, caching, and error capture.
        # Local tools have no API key — has_credentials=True always.
        result = await run_provider(
            provider_name=_PROVIDER_NAME,
            call=lambda: provider.search_usernames(asset_value),
            has_credentials=True,
            user_id=user_id,
            entity_type="username",
            entity_value=asset_value,
            ctx=ctx,
        )

        if not result.success:
            return signals

        for finding in result.findings:
            raw = finding.get("raw", {})
            site = raw.get("site", "unknown") if isinstance(raw, dict) else "unknown"
            url = raw.get("url", "") if isinstance(raw, dict) else ""

            signals.append(
                SignalCreate(
                    signal_type="username_account_found",
                    category="account_enumeration_risk",
                    entity_type=EntityType.USERNAME,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.LOW,
                    confidence=Confidence.MEDIUM,
                    source=self.module_name,
                    provider="tool_maigret",
                    summary=f"Username '{asset_value}' found on {site}",
                    details=finding.get("description"),
                    evidence={
                        "source_provider": "tool_maigret",
                        "username": asset_value,
                        "site": site,
                        "profile_url": url,
                    },
                    tags=["maigret", "username_enum", "account_discovery"],
                    recommended_action=(
                        "Review the discovered account. If you do not own or recognise "
                        "this account, investigate whether it is an impersonation. "
                        "Close dormant accounts to reduce your attack surface."
                    ),
                    source_ref=f"maigret:{site}:{asset_value}",
                )
            )

        logger.info(
            "maigret_scan.completed",
            user_id=str(user_id),
            username=asset_value,
            signals_emitted=len(signals),
        )
        return signals
