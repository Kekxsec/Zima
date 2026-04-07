# backend/app/modules/identity/username_exposure/service.py
import uuid

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.runner import run_provider
from backend.app.providers.social.emailcrawlr.client import EmailcrawlrProvider
from backend.app.providers.social.gravatar.client import GravatarProvider
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)


def _emailcrawlr_severity(data: dict) -> Severity:
    """MEDIUM baseline; escalate to HIGH if phone, address, or full name present."""
    if any(
        [
            data.get("numbers"),
            data.get("location"),
            data.get("name"),
        ]
    ):
        return Severity.HIGH
    return Severity.MEDIUM


class UsernameExposureService(BaseModuleService):
    module_name = "username_exposure"
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

        # --- EmailCrawlr: per-email PII exposure ---
        ec_has_creds = bool(settings.emailcrawlr_api_key)
        if ec_has_creds:
            ec = EmailcrawlrProvider(
                api_key=settings.emailcrawlr_api_key.get_secret_value()  # type: ignore[union-attr]
            )

            ec_email_result = await run_provider(
                provider_name="emailcrawlr",
                call=lambda: ec.get_email(asset_value),
                has_credentials=True,
                user_id=user_id,
                entity_type="email",
                entity_value=asset_value,
                ctx=ctx,
            )

            for email_data in ec_email_result.findings:
                if not isinstance(email_data, dict) or not email_data:
                    continue
                severity = _emailcrawlr_severity(email_data)
                signals.append(
                    SignalCreate(
                        signal_type="email_public_exposure",
                        category="identity_security",
                        entity_type=EntityType.EMAIL,
                        entity_id=asset_id,
                        entity_value=asset_value,
                        user_id=user_id,
                        severity=severity,
                        confidence=Confidence.HIGH,
                        source=self.module_name,
                        provider="emailcrawlr",
                        summary=(
                            f"Email address '{asset_value}' found in "
                            "public data sources"
                        ),
                        details=(
                            "EmailCrawlr found public records associated with this "
                            "email address. May include name, location, phone, or "
                            "linked social profiles."
                        ),
                        evidence={
                            "source_provider": "emailcrawlr",
                            "email": asset_value,
                            "name": email_data.get("name"),
                            "job_title": email_data.get("job_title"),
                            "location": email_data.get("location"),
                            "phone_numbers": email_data.get("numbers", []),
                            "linkedin": email_data.get("linkedin"),
                            "twitter": email_data.get("twitter"),
                            "verified": email_data.get("verified"),
                            "references": email_data.get("references", []),
                        },
                        tags=["email_exposure", "emailcrawlr", "pii"],
                        recommended_action=(
                            "Review what personal information is publicly associated "
                            "with this email address. Consider data removal requests "
                            "where available."
                        ),
                        source_ref=f"emailcrawlr:email:{asset_value}",
                    )
                )

            # Domain-level email enumeration
            domain = asset_value.split("@", 1)[-1] if "@" in asset_value else ""
            if domain:
                ec_domain_result = await run_provider(
                    provider_name="emailcrawlr",
                    call=lambda: ec.search_emails(domain=domain),
                    has_credentials=True,
                    user_id=user_id,
                    entity_type="email",
                    entity_value=f"@{domain}",
                    ctx=ctx,
                )

                if ec_domain_result.findings:
                    domain_findings = ec_domain_result.findings
                    signals.append(
                        SignalCreate(
                            signal_type="email_public_exposure",
                            category="identity_security",
                            entity_type=EntityType.EMAIL,
                            entity_id=asset_id,
                            entity_value=asset_value,
                            user_id=user_id,
                            severity=Severity.MEDIUM,
                            confidence=Confidence.MEDIUM,
                            source=self.module_name,
                            provider="emailcrawlr",
                            summary=(
                                f"{len(domain_findings)} email address(es) publicly "
                                f"indexed for domain '{domain}'"
                            ),
                            details=(
                                f"EmailCrawlr found {len(domain_findings)} public "
                                f"email addresses on '{domain}', indicating this "
                                "email domain is indexed in data broker sources."
                            ),
                            evidence={
                                "source_provider": "emailcrawlr",
                                "domain": domain,
                                "email_count": len(domain_findings),
                                "sample_emails": [
                                    f.get("entity_value") for f in domain_findings[:5]
                                ],
                            },
                            tags=[
                                "email_exposure",
                                "emailcrawlr",
                                "domain_enumeration",
                            ],
                            recommended_action=(
                                "Assess whether email addresses on this domain should "
                                "be publicly discoverable. Consider opt-out requests "
                                "on data broker platforms."
                            ),
                            source_ref=f"emailcrawlr:domain:{domain}",
                        )
                    )

        # --- Gravatar: enrichment only — attach to existing signals ---
        if signals:
            api_key = (
                settings.gravatar_api_key.get_secret_value()
                if settings.gravatar_api_key
                else ""
            )
            gravatar = GravatarProvider(api_key=api_key)
            grav_result = await run_provider(
                provider_name="gravatar",
                call=lambda: gravatar.lookup(asset_value),
                has_credentials=True,
                user_id=user_id,
                entity_type="email",
                entity_value=asset_value,
                ctx=ctx,
            )
            if grav_result.success and grav_result.findings:
                gravatar_data = grav_result.findings[0]
                if gravatar_data:
                    for signal in signals:
                        signal.evidence["gravatar"] = gravatar_data

        logger.info(
            "username_exposure.completed",
            user_id=str(user_id),
            signals_emitted=len(signals),
        )
        return signals
