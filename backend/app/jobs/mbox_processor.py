# backend/app/jobs/mbox_processor.py
"""
Background task: process an uploaded mbox file.

IMPORTANT — Rule 3: creates its own AsyncSession.
NEVER accepts a request-scoped session.
All arguments are serialisable primitives (UUID, str).

Lifecycle:
  1. Mark upload as PROCESSING.
  2. Parse the mbox bytes via MboxParserProvider.
  3. Classify emails via AccountDiscoveryService.
  4. Upsert each DiscoveredAccount.
  5. Emit account_discovered signals via SignalRepository.
  6. Mark upload COMPLETED with counts.
  7. On any unhandled exception: mark FAILED and re-raise.
"""

import uuid

from backend.app.core.logging import get_logger
from backend.app.db.repositories.discovered_accounts import DiscoveredAccountRepository
from backend.app.db.repositories.mbox_uploads import MboxUploadRepository
from backend.app.db.repositories.signals import SignalRepository
from backend.app.db.session import AsyncSessionLocal
from backend.app.email_accounts.service import AccountDiscoveryService
from backend.app.modules.identity.account_discovery.service import build_signal
from backend.app.providers.tools.mbox_parser.client import MboxParserProvider

logger = get_logger(__name__)

_parser = MboxParserProvider()


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
