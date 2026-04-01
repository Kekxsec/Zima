# backend/app/modules/identity/breach_monitor/service.py
import uuid
from typing import Any

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.breach.breachdirectory.client import BreachDirectoryProvider
from backend.app.providers.breach.dehashed.client import DehashedProvider
from backend.app.providers.breach.hibp.client import HibpProvider
from backend.app.signals.schemas import SignalCreate

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


class BreachMonitorService(BaseModuleService):
    module_name = "breach_monitor"
    module_domain = "identity"
    required_entity_types = [EntityType.EMAIL]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
    ) -> list[SignalCreate]:
        signals: list[SignalCreate] = []

        # --- HIBP ---
        hibp_key = (
            settings.hibp_api_key.get_secret_value() if settings.hibp_api_key else ""
        )
        hibp_provider = HibpProvider(api_key=hibp_key)
        try:
            hibp_findings = await hibp_provider.search_breaches(email=asset_value)
        except ProviderError as e:
            logger.error(
                "breach_monitor.hibp_failure", error=str(e), asset_value=asset_value
            )
            hibp_findings = []

        for finding in hibp_findings:
            signals.append(
                SignalCreate(
                    signal_type="email_breached",
                    category="identity_security",
                    entity_type=EntityType.EMAIL,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.HIGH,
                    confidence=(
                        Confidence.HIGH
                    ),  # TODO: calibrate after first 1000 scans
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
        if settings.dehashed_email and settings.dehashed_api_key:
            dehashed_provider = DehashedProvider(
                api_email=settings.dehashed_email,
                api_key=settings.dehashed_api_key.get_secret_value(),
            )
            try:
                dehashed_findings = await dehashed_provider.search_breaches(
                    email=asset_value
                )
            except ProviderError as e:
                logger.error(
                    "breach_monitor.dehashed_failure",
                    error=str(e),
                    asset_value=asset_value,
                )
                dehashed_findings = []

            for finding in dehashed_findings:
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
                        confidence=(
                            Confidence.HIGH
                        ),  # TODO: calibrate after first 1000 scans
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
        if settings.breachdirectory_rapidapi_key:
            bd_provider = BreachDirectoryProvider(
                api_key=settings.breachdirectory_rapidapi_key.get_secret_value()
            )
            try:
                bd_findings = await bd_provider.search_breaches(email=asset_value)
            except ProviderError as e:
                logger.error(
                    "breach_monitor.breachdirectory_failure",
                    error=str(e),
                    asset_value=asset_value,
                )
                bd_findings = []

            for finding in bd_findings:
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
                        confidence=(
                            Confidence.HIGH
                        ),  # TODO: calibrate after first 1000 scans
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

        logger.info(
            "breach_monitor.completed",
            user_id=str(user_id),
            signals_emitted=len(signals),
        )
        return signals
