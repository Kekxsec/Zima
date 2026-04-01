# backend/app/modules/identity/credential_exposure/service.py
import uuid

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.breach.breachdirectory.client import BreachDirectoryProvider
from backend.app.providers.breach.dehashed.client import DehashedProvider
from backend.app.providers.breach.leakcheck.client import LeakCheckProvider
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)


def _severity_for_credential(has_plaintext: bool, has_hash: bool) -> Severity:
    # TODO: calibrate after first 1000 scans
    if has_plaintext:
        return Severity.CRITICAL
    if has_hash:
        return Severity.HIGH
    return Severity.HIGH  # fallback — shouldn't be reached if caller checks first


class CredentialExposureService(BaseModuleService):
    module_name = "credential_exposure"
    module_domain = "identity"
    required_entity_types = [EntityType.EMAIL]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
    ) -> list[SignalCreate]:
        signals: list[SignalCreate] = []

        # --- DeHashed ---
        if settings.dehashed_email and settings.dehashed_api_key:
            dehashed = DehashedProvider(
                api_email=settings.dehashed_email,
                api_key=settings.dehashed_api_key.get_secret_value(),
            )
            try:
                findings = await dehashed.search_breaches(email=asset_value)
            except ProviderError as e:
                logger.error(
                    "credential_exposure.dehashed_failure",
                    error=str(e),
                    asset_value=asset_value,
                )
                findings = []

            for finding in findings:
                raw = finding.get("raw", {})
                # has_plaintext / has_hash flags are pre-computed by DehashedProvider
                # (entries are scrubbed of actual password values before returning)
                has_plaintext = (
                    bool(raw.get("has_plaintext")) if isinstance(raw, dict) else False
                )
                has_hash = bool(raw.get("has_hash")) if isinstance(raw, dict) else False
                if not has_plaintext and not has_hash:
                    continue  # no password data — not a credential_exposure signal
                severity = _severity_for_credential(has_plaintext, has_hash)
                summary = (
                    "Plaintext password exposed in DeHashed breach record"
                    if has_plaintext
                    else "Password hash exposed in DeHashed breach record"
                )
                breach_title = finding.get("title", "dehashed_unknown")
                signals.append(
                    SignalCreate(
                        signal_type="password_exposed",
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
                        summary=summary,
                        details=finding.get("description"),
                        evidence={
                            "source_provider": "dehashed",
                            "has_plaintext": has_plaintext,
                            "has_hash": has_hash,
                            "password_present": True,
                            "sample_count": raw.get("sample_count", 0)
                            if isinstance(raw, dict)
                            else 0,
                        },
                        tags=["credential_exposure", "password_exposed", "dehashed"],
                        recommended_action=(
                            "Rotate the exposed password immediately on all "
                            "services where it was used. "
                            "Use a unique password for each service. Enable MFA."
                        ),
                        source_ref=f"dehashed:{breach_title}",
                    )
                )

        # --- LeakCheck ---
        if settings.leakcheck_api_key:
            leakcheck = LeakCheckProvider(
                api_key=settings.leakcheck_api_key.get_secret_value()
            )
            try:
                findings = await leakcheck.check_leaks(email=asset_value)
            except ProviderError as e:
                logger.error(
                    "credential_exposure.leakcheck_failure",
                    error=str(e),
                    asset_value=asset_value,
                )
                findings = []

            for finding in findings:
                raw = finding.get("raw", {})
                has_password = (
                    bool(raw.get("has_password")) if isinstance(raw, dict) else False
                )
                if not has_password:
                    continue
                breach_name = (
                    raw.get("breach_name", "unknown")
                    if isinstance(raw, dict)
                    else "unknown"
                )
                breach_date = (
                    raw.get("breach_date", "unknown")
                    if isinstance(raw, dict)
                    else "unknown"
                )
                # LeakCheck doesn't distinguish plaintext vs hash at this level
                # has_password = True but we don't know the type → treat as HIGH
                signals.append(
                    SignalCreate(
                        signal_type="password_exposed",
                        category="identity_security",
                        entity_type=EntityType.EMAIL,
                        entity_id=asset_id,
                        entity_value=asset_value,
                        user_id=user_id,
                        severity=(
                            Severity.HIGH
                        ),  # TODO: calibrate after first 1000 scans
                        confidence=(
                            Confidence.HIGH
                        ),  # TODO: calibrate after first 1000 scans
                        source=self.module_name,
                        provider="leakcheck",
                        summary=f"Password hash exposed in {breach_name} breach",
                        details=finding.get("description"),
                        evidence={
                            "source_provider": "leakcheck",
                            "breach_name": breach_name,
                            "breach_date": breach_date,
                            "has_plaintext": False,
                            "has_hash": True,
                            "password_present": True,
                        },
                        tags=["credential_exposure", "password_exposed", "leakcheck"],
                        recommended_action=(
                            "Rotate the exposed password immediately on all "
                            "services where it was used. "
                            "Use a unique password for each service. Enable MFA."
                        ),
                        source_ref=f"leakcheck:{breach_name}",
                    )
                )

        # --- BreachDirectory ---
        if settings.breachdirectory_rapidapi_key:
            bd = BreachDirectoryProvider(
                api_key=settings.breachdirectory_rapidapi_key.get_secret_value()
            )
            try:
                findings = await bd.search_breaches(email=asset_value)
            except ProviderError as e:
                logger.error(
                    "credential_exposure.breachdirectory_failure",
                    error=str(e),
                    asset_value=asset_value,
                )
                findings = []

            for finding in findings:
                raw = finding.get("raw", {})
                has_plaintext = (
                    bool(raw.get("has_plaintext")) if isinstance(raw, dict) else False
                )
                is_hash = bool(raw.get("is_hash")) if isinstance(raw, dict) else False
                if not has_plaintext and not is_hash:
                    continue
                severity = _severity_for_credential(has_plaintext, is_hash)
                summary = (
                    "Plaintext password exposed in BreachDirectory record"
                    if has_plaintext
                    else "Password hash exposed in BreachDirectory record"
                )
                bd_title = finding.get("title", "bd_unknown")
                signals.append(
                    SignalCreate(
                        signal_type="password_exposed",
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
                        summary=summary,
                        details=finding.get("description"),
                        evidence={
                            "source_provider": "breachdirectory",
                            "has_plaintext": has_plaintext,
                            "has_hash": is_hash,
                            "password_present": True,
                        },
                        tags=[
                            "credential_exposure",
                            "password_exposed",
                            "breachdirectory",
                        ],
                        recommended_action=(
                            "Rotate the exposed password immediately on all "
                            "services where it was used. "
                            "Use a unique password for each service. Enable MFA."
                        ),
                        source_ref=f"breachdirectory:{bd_title}",
                    )
                )

        logger.info(
            "credential_exposure.completed",
            user_id=str(user_id),
            signals_emitted=len(signals),
        )
        return signals
