# backend/app/jobs/mbox_processor.py
"""
Background task: process an uploaded mbox file.

IMPORTANT — Rule 3: creates its own AsyncSession.
NEVER accepts a request-scoped session.
All arguments are serialisable primitives (UUID, str).

Lifecycle:
  1. Mark upload as PROCESSING.
  2. Parse the mbox bytes via MboxParserProvider.
  3. Newsletter pre-pass: detect newsletters, scan unsubscribe URLs via VirusTotal,
     and upsert NewsletterSubscription rows.
  4. Emit phishing signals for any newsletter with a malicious unsubscribe URL.
  5. Classify emails via AccountDiscoveryService (newsletters already filtered).
  6. Upsert each DiscoveredAccount.
  7. Emit account_discovered signals via SignalRepository.
  8. Mark upload COMPLETED with counts.
  9. On any unhandled exception: mark FAILED and re-raise.
"""

import uuid

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.db.repositories.discovered_accounts import DiscoveredAccountRepository
from backend.app.db.repositories.mbox_uploads import MboxUploadRepository
from backend.app.db.repositories.newsletter_subscriptions import (
    NewsletterSubscriptionRepository,
)
from backend.app.db.repositories.signals import SignalRepository
from backend.app.db.session import AsyncSessionLocal
from backend.app.email_accounts.newsletter import (
    NewsletterDetectionService,
    NewsletterDraft,
)
from backend.app.email_accounts.service import AccountDiscoveryService
from backend.app.modules.identity.account_discovery.service import build_signal
from backend.app.providers.threat_intel.virustotal.client import VirusTotalProvider
from backend.app.providers.tools.mbox_parser.client import MboxParserProvider
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)

_parser = MboxParserProvider()
_newsletter_detector = NewsletterDetectionService()


async def _scan_newsletter_url(
    draft: NewsletterDraft, vt_api_key: str
) -> NewsletterDraft:
    """
    Scan the unsubscribe URL via VirusTotal.
    Returns a copy of the draft with is_phishing=True if the URL is malicious.
    Fails open: any VirusTotal error leaves is_phishing=False.
    """
    url = draft.unsubscribe_url
    if not url:
        return draft

    try:
        provider = VirusTotalProvider(api_key=vt_api_key)
        result = await provider.scan_url(url)
        if result.is_malicious:
            return draft.model_copy(update={"is_phishing": True})
    except Exception as exc:
        logger.warning(
            "mbox_processor.vt_scan_failed",
            url=url,
            error=str(exc),
        )

    return draft


async def process_mbox_upload(
    user_id: uuid.UUID,
    upload_id: uuid.UUID,
    asset_id: uuid.UUID,
    recipient_email: str,
    mbox_bytes: bytes,
) -> None:
    """
    Background task entry-point.

    Parameters
    ----------
    user_id:        The authenticated user who owns this upload.
    upload_id:      The MboxUpload row that tracks this job.
    asset_id:       The verified Asset UUID for *recipient_email*.
    recipient_email: The email address whose inbox is being analysed.
    mbox_bytes:     Raw mbox file content held in memory for the duration of
                    this call.
    """
    async with AsyncSessionLocal() as session:
        upload_repo = MboxUploadRepository(session)
        account_repo = DiscoveredAccountRepository(session)
        signal_repo = SignalRepository(session)
        newsletter_repo = NewsletterSubscriptionRepository(session)

        try:
            await upload_repo.set_processing(upload_id)
            await session.commit()

            # --- Parse ---
            parsed_emails = _parser.parse(mbox_bytes)
            logger.info(
                "mbox_processor.parsed",
                upload_id=str(upload_id),
                message_count=len(parsed_emails),
            )

            # --- Newsletter pre-pass (with VirusTotal URL scanning) ---
            newsletter_drafts = _newsletter_detector.detect(parsed_emails)

            vt_key = (
                settings.virustotal_api_key.get_secret_value()
                if settings.virustotal_api_key
                else ""
            )

            newsletters_upserted = 0
            phishing_detected = 0
            for draft in newsletter_drafts:
                # Scan unsubscribe URL if we have a VT key
                if vt_key and draft.unsubscribe_url:
                    draft = await _scan_newsletter_url(draft, vt_key)

                await newsletter_repo.upsert(
                    user_id=user_id,
                    upload_id=upload_id,
                    sender_domain=draft.sender_domain,
                    sender_name=draft.sender_name,
                    message_count=draft.message_count,
                    first_seen_at=draft.first_seen_at,
                    last_seen_at=draft.last_seen_at,
                    unsubscribe_url=draft.unsubscribe_url,
                    list_id=draft.list_id,
                    confidence=draft.confidence,
                    is_phishing=draft.is_phishing,
                )
                newsletters_upserted += 1

                # Emit phishing signal for malicious unsubscribe links
                if draft.is_phishing and draft.unsubscribe_url:
                    phishing_signal = SignalCreate(
                        signal_type="phishing_unsubscribe_link",
                        category="phishing",
                        entity_type=EntityType.EMAIL,
                        entity_id=asset_id,
                        entity_value=recipient_email,
                        user_id=user_id,
                        severity=Severity.HIGH,
                        confidence=Confidence.HIGH,
                        source="mbox_processor",
                        provider="virustotal",
                        title=(
                            "Phishing unsubscribe link detected from "
                            f"{draft.sender_domain}"
                        ),
                        description=(
                            f"The unsubscribe link in emails from "
                            f"{draft.sender_domain} was flagged as malicious "
                            f"by VirusTotal. Do NOT click the unsubscribe link. "
                            f"Delete these emails and block the sender."
                        ),
                        recommended_action=(
                            "Delete this email from your mailbox and block the sender. "
                            "Do not click the unsubscribe link."
                        ),
                        tags=["phishing", "newsletter", "virustotal", "malicious-url"],
                        source_ref=draft.sender_domain,
                    )
                    await signal_repo.upsert(phishing_signal)
                    phishing_detected += 1

            logger.info(
                "mbox_processor.newsletters_detected",
                upload_id=str(upload_id),
                newsletters_upserted=newsletters_upserted,
                phishing_detected=phishing_detected,
            )

            # --- Classify ---
            discovery_svc = AccountDiscoveryService(session)
            drafts = await discovery_svc.classify_emails(parsed_emails, recipient_email)
            logger.info(
                "mbox_processor.classified",
                upload_id=str(upload_id),
                draft_count=len(drafts),
            )

            # --- Upsert accounts & emit signals ---
            accounts_discovered = 0
            signals_created = 0

            for draft in drafts:
                account = await account_repo.upsert(
                    user_id=user_id,
                    upload_id=upload_id,
                    service_name=draft.service_name,
                    display_name=draft.display_name,
                    email_used=draft.email_used,
                    source_type=draft.source_type,
                    sender_domain=draft.sender_domain,
                    login_url=draft.login_url,
                    password_reset_url=draft.password_reset_url,
                    first_seen_at=draft.first_seen_at,
                    last_seen_at=draft.last_seen_at,
                    email_count=draft.email_count,
                )
                accounts_discovered += 1

                signal = build_signal(
                    user_id=user_id,
                    asset_id=asset_id,
                    email_value=recipient_email,
                    account=account,
                )
                await signal_repo.upsert(signal)
                signals_created += 1

            await upload_repo.set_completed(
                upload_id=upload_id,
                accounts_discovered=accounts_discovered,
                signals_created=signals_created,
            )
            await session.commit()

            logger.info(
                "mbox_processor.completed",
                upload_id=str(upload_id),
                accounts_discovered=accounts_discovered,
                signals_created=signals_created,
            )

        except Exception as exc:
            await session.rollback()
            try:
                async with AsyncSessionLocal() as err_session:
                    await MboxUploadRepository(err_session).set_failed(
                        upload_id=upload_id,
                        error_detail=str(exc)[:1024],
                    )
                    await err_session.commit()
            except Exception:
                logger.exception(
                    "mbox_processor.failed_to_mark_failed", upload_id=str(upload_id)
                )

            logger.exception(
                "mbox_processor.failed",
                upload_id=str(upload_id),
                error=str(exc),
            )
            raise
