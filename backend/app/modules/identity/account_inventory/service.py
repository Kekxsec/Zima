# backend/app/modules/identity/account_inventory/service.py
from __future__ import annotations

import hashlib
import uuid
from typing import TYPE_CHECKING

from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.runner import run_provider
from backend.app.providers.tools.holehe.client import HoleheProvider
from backend.app.providers.tools.mailcat.client import MailcatProvider
from backend.app.providers.tools.whatsmyname.client import WhatsmyNameProvider
from backend.app.signals.schemas import SignalCreate

if TYPE_CHECKING:
    from backend.app.jobs.context import ScanExecutionContext

logger = get_logger(__name__)

_PROVIDER_NAME = "tool_holehe"


class AccountInventoryService(BaseModuleService):
    """Runs Holehe against EMAIL assets to discover registered accounts.

    Holehe is a local subprocess tool — policy gate and audit trail are
    handled by run_provider() plus an explicit local_tool_invoked event.
    """

    module_name = "account_inventory"
    module_domain = "identity"
    required_entity_types = [EntityType.EMAIL]

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

        provider = HoleheProvider()

        # run_provider handles policy check, caching, and error capture.
        # Local tools have no API key — has_credentials=True always.
        result = await run_provider(
            provider_name=_PROVIDER_NAME,
            call=lambda: provider.check_accounts_tool(asset_value),
            has_credentials=True,
            user_id=user_id,
            entity_type="email",
            entity_value=asset_value,
            ctx=ctx,
        )

        if not result.success:
            return signals

        for finding in result.findings:
            raw = finding.get("raw", {})
            platform = raw.get("site", "") if isinstance(raw, dict) else ""
            if not platform:
                platform = finding.get("title", "unknown platform").replace(
                    "Account found: ", ""
                )

            signals.append(
                SignalCreate(
                    signal_type="account_discovered",
                    category="identity_inventory",
                    entity_type=EntityType.EMAIL,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.INFO,
                    confidence=Confidence.HIGH,
                    source=self.module_name,
                    provider="tool_holehe",
                    summary=f"Account found registered on {platform}",
                    details=finding.get("description"),
                    evidence={
                        "source_provider": "tool_holehe",
                        "platform": platform,
                        "profile_url": None,
                        "registration_confirmed": True,
                    },
                    tags=["account_discovered", "holehe", "account_inventory"],
                    recommended_action=(
                        "Review and secure the discovered account. "
                        "Close dormant accounts. Enable MFA where available."
                    ),
                    source_ref=f"holehe:{platform}",
                )
            )

        # --- Mailcat: email addresses discovered from username prefix ---
        username_prefix = asset_value.split("@", 1)[0]
        if username_prefix:
            mailcat_provider = MailcatProvider()
            mailcat_result = await run_provider(
                provider_name="tool_mailcat",
                call=lambda: mailcat_provider.find_emails(username_prefix),
                has_credentials=True,
                user_id=user_id,
                entity_type="email",
                entity_value=asset_value,
                ctx=ctx,
            )
            for finding in mailcat_result.findings:
                raw = finding.get("raw", {})
                discovered_email = (
                    raw.get("email", "") if isinstance(raw, dict) else ""
                ) or finding.get("title", "").replace("Email discovered: ", "")

                signals.append(
                    SignalCreate(
                        signal_type="account_discovered",
                        category="identity_inventory",
                        entity_type=EntityType.EMAIL,
                        entity_id=asset_id,
                        entity_value=asset_value,
                        user_id=user_id,
                        severity=Severity.INFO,
                        confidence=Confidence.MEDIUM,
                        source=self.module_name,
                        provider="tool_mailcat",
                        summary=(
                            f"Email alias discovered via username: {discovered_email}"
                        ),
                        details=finding.get("description"),
                        evidence={
                            "source_provider": "tool_mailcat",
                            "discovered_email": discovered_email,
                            "username": username_prefix,
                        },
                        tags=["account_discovered", "mailcat", "email_alias"],
                        recommended_action=(
                            "Verify ownership of the discovered email alias. "
                            "Ensure it is not being used without your knowledge."
                        ),
                        source_ref=f"mailcat:{discovered_email}",
                    )
                )

        # --- WhatsmyName: username enumeration across 500+ platforms ---
        if username_prefix:
            wmn_provider = WhatsmyNameProvider()
            wmn_result = await run_provider(
                provider_name="tool_whatsmyname",
                call=lambda: wmn_provider.search_username(username_prefix),
                has_credentials=True,
                user_id=user_id,
                entity_type="email",
                entity_value=asset_value,
                ctx=ctx,
            )
            for finding in wmn_result.findings:
                raw = finding.get("raw", {})
                platform = (
                    raw.get("site", "") if isinstance(raw, dict) else ""
                ) or finding.get("title", "").replace("Username found: ", "")
                profile_url = raw.get("url") if isinstance(raw, dict) else None

                signals.append(
                    SignalCreate(
                        signal_type="account_discovered",
                        category="identity_inventory",
                        entity_type=EntityType.EMAIL,
                        entity_id=asset_id,
                        entity_value=asset_value,
                        user_id=user_id,
                        severity=Severity.INFO,
                        confidence=Confidence.HIGH,
                        source=self.module_name,
                        provider="tool_whatsmyname",
                        summary=f"Account found on {platform} via username",
                        details=finding.get("description"),
                        evidence={
                            "source_provider": "tool_whatsmyname",
                            "platform": platform,
                            "profile_url": profile_url,
                            "username": username_prefix,
                            "registration_confirmed": True,
                        },
                        tags=["account_discovered", "whatsmyname", "account_inventory"],
                        recommended_action=(
                            "Review and secure the discovered account. "
                            "Close dormant accounts. Enable MFA where available."
                        ),
                        source_ref=f"whatsmyname:{platform}",
                    )
                )

        logger.info(
            "account_inventory.completed",
            user_id=str(user_id),
            signals_emitted=len(signals),
        )
        return signals
