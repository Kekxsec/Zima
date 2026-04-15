# backend/app/modules/identity/breach_monitor/service.py
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.outcome import ModuleOutcome
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.runner import run_provider
from backend.app.providers.breach.breachdirectory.client import BreachDirectoryProvider
from backend.app.providers.breach.dehashed.client import DehashedProvider
from backend.app.providers.breach.hibp.client import HibpProvider
from backend.app.providers.breach.leakcheck.client import LeakCheckProvider
from backend.app.signals.schemas import SignalCreate

if TYPE_CHECKING:
    from backend.app.jobs.context import ScanExecutionContext

logger = get_logger(__name__)


def _breach_severity_dehashed(entries: list[dict[str, Any]]) -> Severity:
    """CRITICAL if any entry has plaintext or hashed password; HIGH otherwise."""
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("password") or entry.get("hashed_password"):
            return Severity.CRITICAL
    return Severity.HIGH


def _breach_severity_breachdirectory(raw: dict[str, Any]) -> Severity:
    """CRITICAL if plaintext present; HIGH otherwise."""
    if raw.get("has_plaintext"):
        return Severity.CRITICAL
    return Severity.HIGH


def _breach_severity_leakcheck(raw: dict[str, Any]) -> Severity:
    """CRITICAL if password columns present; HIGH otherwise."""
    if raw.get("has_password"):
        return Severity.CRITICAL
    return Severity.HIGH


class BreachMonitorService(BaseModuleService):
    module_name = "breach_monitor"
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

        # --- HIBP ---
        hibp_key = (
            settings.hibp_api_key.get_secret_value() if settings.hibp_api_key else ""
        )
        hibp_provider = HibpProvider(api_key=hibp_key)
        hibp_result = await run_provider(
            provider_name="haveibeenpwned",
            call=lambda: hibp_provider.search_breaches(email=asset_value),
            has_credentials=bool(hibp_key),
            user_id=user_id,
            entity_type="email",
            entity_value=asset_value,
            ctx=ctx,
        )

        for finding in hibp_result.findings:
            signals.append(
                SignalCreate(
                    signal_type="email_breached",
                    category="identity_security",
                    entity_type=EntityType.EMAIL,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.HIGH,
                    confidence=Confidence.HIGH,
                    source=self.module_name,
                    provider="haveibeenpwned",
                    summary=finding["title"],
                    details=finding["description"],
                    evidence={"raw_finding": finding},
                    tags=finding.get("tags", []) + ["identity", "breach"],
                    recommended_action=(
                        "Rotate the password used at this service immediately. "
                        "Enable MFA if not already active."
                    ),
                    source_ref=f"hibp:{finding['raw']['breach_name']}",
                )
            )

        # --- DeHashed ---
        dh_has_creds = bool(settings.dehashed_email and settings.dehashed_api_key)
        if dh_has_creds:
            assert settings.dehashed_email is not None
            assert settings.dehashed_api_key is not None
            dehashed_provider = DehashedProvider(
                api_email=settings.dehashed_email,
                api_key=settings.dehashed_api_key.get_secret_value(),
            )
        else:
            dehashed_provider = None

        dh_result = await run_provider(
            provider_name="dehashed",
            call=lambda: dehashed_provider.search_breaches(email=asset_value),  # type: ignore[union-attr]
            has_credentials=dh_has_creds,
            user_id=user_id,
            entity_type="email",
            entity_value=asset_value,
            ctx=ctx,
            check_quota=True,
        )

        for finding in dh_result.findings:
            raw = finding.get("raw", {})
            entries: list[dict[str, Any]] = (
                raw.get("entries", []) if isinstance(raw, dict) else []
            )
            severity = _breach_severity_dehashed(entries)
            total = raw.get("total", 0) if isinstance(raw, dict) else 0
            breach_title = finding.get("title", "dehashed_unknown")
            signals.append(
                SignalCreate(
                    signal_type="email_breached",
                    category="identity_security",
                    entity_type=EntityType.EMAIL,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=severity,
                    confidence=Confidence.HIGH,
                    source=self.module_name,
                    provider="dehashed",
                    summary=f"Email found in {total} DeHashed breach record(s)",
                    details=finding.get("description"),
                    evidence={"raw_finding": finding},
                    tags=finding.get("tags", []) + ["identity", "breach"],
                    recommended_action=(
                        "Rotate credentials for any services where this "
                        "email was used. "
                        "Enable MFA if not already active."
                    ),
                    source_ref=f"dehashed:{breach_title}",
                )
            )

        # --- BreachDirectory ---
        bd_has_creds = bool(settings.breachdirectory_rapidapi_key)
        if bd_has_creds:
            assert settings.breachdirectory_rapidapi_key is not None
            bd_provider = BreachDirectoryProvider(
                api_key=settings.breachdirectory_rapidapi_key.get_secret_value()
            )
        else:
            bd_provider = None

        bd_result = await run_provider(
            provider_name="breachdirectory",
            call=lambda: bd_provider.search_breaches(email=asset_value),  # type: ignore[union-attr]
            has_credentials=bd_has_creds,
            user_id=user_id,
            entity_type="email",
            entity_value=asset_value,
            ctx=ctx,
            check_quota=True,
        )

        for finding in bd_result.findings:
            raw = finding.get("raw", {})
            severity = _breach_severity_breachdirectory(
                raw if isinstance(raw, dict) else {}
            )
            bd_title = finding.get("title", f"bd:{asset_value}")
            signals.append(
                SignalCreate(
                    signal_type="email_breached",
                    category="identity_security",
                    entity_type=EntityType.EMAIL,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=severity,
                    confidence=Confidence.HIGH,
                    source=self.module_name,
                    provider="breachdirectory",
                    summary=bd_title,
                    details=finding.get("description"),
                    evidence={"raw_finding": finding},
                    tags=finding.get("tags", []) + ["identity", "breach"],
                    recommended_action=(
                        "Rotate credentials for any services where this "
                        "email was used. "
                        "Enable MFA if not already active."
                    ),
                    source_ref=f"breachdirectory:{bd_title}",
                )
            )

        # --- LeakCheck ---
        lc_key = (
            settings.leakcheck_api_key.get_secret_value()
            if settings.leakcheck_api_key
            else ""
        )
        lc_provider = LeakCheckProvider(api_key=lc_key)
        lc_result = await run_provider(
            provider_name="leakcheck",
            call=lambda: lc_provider.check_leaks(email=asset_value),
            has_credentials=True,  # public endpoint works without key (rate-limited)
            user_id=user_id,
            entity_type="email",
            entity_value=asset_value,
            ctx=ctx,
            check_quota=True,
        )

        for finding in lc_result.findings:
            raw = finding.get("raw", {})
            severity = _breach_severity_leakcheck(raw if isinstance(raw, dict) else {})
            breach_name = (
                raw.get("breach_name", "unknown")
                if isinstance(raw, dict)
                else "unknown"
            )
            signals.append(
                SignalCreate(
                    signal_type="email_breached",
                    category="identity_security",
                    entity_type=EntityType.EMAIL,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=severity,
                    confidence=Confidence.HIGH,
                    source=self.module_name,
                    provider="leakcheck",
                    summary=finding.get("title", f"LeakCheck breach: {asset_value}"),
                    details=finding.get("description"),
                    evidence={"raw_finding": finding},
                    tags=finding.get("tags", []) + ["identity", "breach"],
                    recommended_action=(
                        "Rotate credentials for any services where this "
                        "email was used. "
                        "Enable MFA if not already active."
                    ),
                    source_ref=f"leakcheck:{breach_name}",
                )
            )

        logger.info(
            "breach_monitor.completed",
            user_id=str(user_id),
            signals_emitted=len(signals),
        )
        return ModuleOutcome(signals=signals)
