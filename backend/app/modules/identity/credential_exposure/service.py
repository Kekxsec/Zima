# backend/app/modules/identity/credential_exposure/service.py
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.outcome import ModuleOutcome
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.runner import run_provider
from backend.app.providers.breach.breachdirectory.client import BreachDirectoryProvider
from backend.app.providers.breach.dehashed.client import DehashedProvider
from backend.app.providers.breach.leakcheck.client import LeakCheckProvider
from backend.app.signals.schemas import SignalCreate

if TYPE_CHECKING:
    from backend.app.jobs.context import ScanExecutionContext

logger = get_logger(__name__)


def _severity_for_credential(has_plaintext: bool, has_hash: bool) -> Severity:
    if has_plaintext:
        return Severity.CRITICAL
    if has_hash:
        return Severity.HIGH
    return Severity.HIGH


class CredentialExposureService(BaseModuleService):
    module_name = "credential_exposure"
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

        # --- DeHashed ---
        dh_has_creds = bool(settings.dehashed_email and settings.dehashed_api_key)
        if dh_has_creds:
            assert settings.dehashed_email is not None
            assert settings.dehashed_api_key is not None
            dehashed = DehashedProvider(
                api_email=settings.dehashed_email,
                api_key=settings.dehashed_api_key.get_secret_value(),
            )
        else:
            dehashed = None

        dh_result = await run_provider(
            provider_name="dehashed",
            call=lambda: dehashed.search_breaches(email=asset_value),  # type: ignore[union-attr]
            has_credentials=dh_has_creds,
            user_id=user_id,
            entity_type="email",
            entity_value=asset_value,
            ctx=ctx,
            check_quota=True,
        )

        for finding in dh_result.findings:
            raw = finding.get("raw", {})
            has_plaintext = (
                bool(raw.get("has_plaintext")) if isinstance(raw, dict) else False
            )
            has_hash = bool(raw.get("has_hash")) if isinstance(raw, dict) else False
            if not has_plaintext and not has_hash:
                continue
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
                    confidence=Confidence.HIGH,
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
        lc_has_creds = bool(settings.leakcheck_api_key)
        if lc_has_creds:
            assert settings.leakcheck_api_key is not None
            leakcheck = LeakCheckProvider(
                api_key=settings.leakcheck_api_key.get_secret_value()
            )
        else:
            leakcheck = None

        lc_result = await run_provider(
            provider_name="leakcheck",
            call=lambda: leakcheck.check_leaks(email=asset_value),  # type: ignore[union-attr]
            has_credentials=lc_has_creds,
            user_id=user_id,
            entity_type="email",
            entity_value=asset_value,
            ctx=ctx,
            check_quota=True,
        )

        for finding in lc_result.findings:
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
            signals.append(
                SignalCreate(
                    signal_type="password_exposed",
                    category="identity_security",
                    entity_type=EntityType.EMAIL,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.HIGH,
                    confidence=Confidence.HIGH,
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
        bd_has_creds = bool(settings.breachdirectory_rapidapi_key)
        if bd_has_creds:
            assert settings.breachdirectory_rapidapi_key is not None
            bd = BreachDirectoryProvider(
                api_key=settings.breachdirectory_rapidapi_key.get_secret_value()
            )
        else:
            bd = None

        bd_result = await run_provider(
            provider_name="breachdirectory",
            call=lambda: bd.search_breaches(email=asset_value),  # type: ignore[union-attr]
            has_credentials=bd_has_creds,
            user_id=user_id,
            entity_type="email",
            entity_value=asset_value,
            ctx=ctx,
            check_quota=True,
        )

        for finding in bd_result.findings:
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
                    confidence=Confidence.HIGH,
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
        return ModuleOutcome(signals=signals)
