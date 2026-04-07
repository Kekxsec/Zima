# backend/app/modules/identity/public_profile_scan/service.py
"""Public profile scan — Gravatar + EmailCrawlr."""

from __future__ import annotations

import uuid

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.base.runner import run_provider
from backend.app.providers.social.emailcrawlr.client import EmailcrawlrProvider
from backend.app.providers.social.gravatar.client import GravatarProvider
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)


class PublicProfileScanService(BaseModuleService):
    """Discovers public profile data linked to an email address.

    Uses Gravatar for profile data and EmailCrawlr for social / domain
    enrichment. Emits ``public_profile_exposure`` signals when meaningful
    public data is found.
    """

    module_name = "public_profile_scan"
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

        # --- Gravatar ---
        gravatar_api_key = (
            settings.gravatar_api_key.get_secret_value()
            if settings.gravatar_api_key
            else ""
        )
        gravatar = GravatarProvider(api_key=gravatar_api_key)

        gravatar_result = await run_provider(
            provider_name="gravatar",
            call=lambda: gravatar.lookup(asset_value),
            has_credentials=True,
            user_id=user_id,
            entity_type="email",
            entity_value=asset_value,
            ctx=ctx,
        )

        if gravatar_result.success and gravatar_result.findings:
            # run_provider normalises dict → [dict], so findings[0] is the
            # flat profile dict returned by GravatarProvider.lookup().
            profile = gravatar_result.findings[0]
            display_name = profile.get("display_name") or ""
            profile_url = profile.get("profile_url") or ""
            verified_accounts: list = (
                profile.get("verified_accounts", [])
                if isinstance(profile.get("verified_accounts"), list)
                else []
            )
            gravatar_hash = profile.get("hash") or ""

            if display_name or profile_url:
                signals.append(
                    SignalCreate(
                        signal_type="public_profile_exposure",
                        category="identity_security",
                        entity_type=EntityType.EMAIL,
                        entity_id=asset_id,
                        entity_value=asset_value,
                        user_id=user_id,
                        severity=Severity.LOW,
                        confidence=Confidence.HIGH,
                        source=self.module_name,
                        provider="gravatar",
                        summary=(
                            "Public Gravatar profile found"
                            + (f": {display_name}" if display_name else "")
                        ),
                        details=None,
                        evidence={
                            "source_provider": "gravatar",
                            "display_name": display_name,
                            "profile_url": profile_url,
                            "avatar_url": profile.get("avatar_url"),
                            "location": profile.get("location"),
                            "verified_accounts": verified_accounts,
                            "linked_accounts_count": len(verified_accounts),
                        },
                        tags=["public_profile", "gravatar", "identity_exposure"],
                        recommended_action=(
                            "Review your Gravatar profile. "
                            "Remove personal information you do not wish to be public. "
                            "Audit linked verified accounts."
                        ),
                        source_ref=f"gravatar:{gravatar_hash}",
                    )
                )

        # --- EmailCrawlr: social profile enrichment per email ---
        if settings.emailcrawlr_api_key:
            ecrawlr_key = settings.emailcrawlr_api_key.get_secret_value()
            ecrawlr = EmailcrawlrProvider(api_key=ecrawlr_key)

            try:
                email_data = await ecrawlr.get_email(asset_value)
            except ProviderError as exc:
                logger.error(
                    "public_profile_scan.emailcrawlr_failure",
                    error=str(exc),
                    email=asset_value,
                )
                email_data = {}

            if email_data:
                linkedin = email_data.get("linkedin") or ""
                twitter = email_data.get("twitter") or ""
                name = email_data.get("name") or ""
                references = int(email_data.get("references") or 0)

                if linkedin or twitter or name:
                    signals.append(
                        SignalCreate(
                            signal_type="public_profile_exposure",
                            category="identity_security",
                            entity_type=EntityType.EMAIL,
                            entity_id=asset_id,
                            entity_value=asset_value,
                            user_id=user_id,
                            severity=Severity.LOW,
                            confidence=Confidence.MEDIUM,
                            source=self.module_name,
                            provider="emailcrawlr",
                            summary=(
                                "Social profiles linked to email"
                                + (f" ({name})" if name else "")
                            ),
                            details=(
                                f"EmailCrawlr found social data for {asset_value}"
                            ),
                            evidence={
                                "source_provider": "emailcrawlr",
                                "name": name,
                                "linkedin": linkedin,
                                "twitter": twitter,
                                "references": references,
                                "job_title": email_data.get("job_title"),
                                "location": email_data.get("location"),
                            },
                            tags=["public_profile", "emailcrawlr", "social_exposure"],
                            recommended_action=(
                                "Review social profiles associated with this email. "
                                "Consider using separate emails for public accounts."
                            ),
                            source_ref=f"emailcrawlr:{asset_value}",
                        )
                    )

        logger.info(
            "public_profile_scan.completed",
            user_id=str(user_id),
            signals_emitted=len(signals),
        )
        return signals
