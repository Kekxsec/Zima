# backend/app/gdpr/erasure.py
"""
GDPR right-to-erasure orchestrator.

Deletes all personal data for a user in FK-safe dependency order so that
referential integrity constraints are never violated mid-erasure.

Deletion order (leaf tables first, parent tables last):
  1.  scan_events          (FK → scans, users)
  2.  notification_outbox  (FK → users)
  3.  signals              (FK → assets, users)
  4.  findings             (FK → users)
  5.  scores               (FK → users)
  6.  discovered_accounts  (FK → users)
  7.  mbox_uploads         (FK → users)
  8.  scans                (FK → users)
  9.  assets               (FK → users)
  10. auth_tokens          (keyed by email — must run after assets still exist)
  11. audit_events         anonymised (user_id → NULL); rows are retained
  12. users                soft-deleted + PII scrubbed

The caller is responsible for committing the session after this method
returns.  If an exception is raised, the caller should roll back.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import get_logger
from backend.app.db.repositories.assets import AssetRepository
from backend.app.db.repositories.audit import AuditRepository
from backend.app.db.repositories.auth_tokens import AuthTokenRepository
from backend.app.db.repositories.discovered_accounts import DiscoveredAccountRepository
from backend.app.db.repositories.findings import FindingRepository
from backend.app.db.repositories.mbox_uploads import MboxUploadRepository
from backend.app.db.repositories.notification_outbox import NotificationOutboxRepository
from backend.app.db.repositories.scan_events import ScanEventRepository
from backend.app.db.repositories.scans import ScanRepository
from backend.app.db.repositories.scores import ScoreRepository
from backend.app.db.repositories.signals import SignalRepository
from backend.app.db.repositories.users import UserRepository

logger = get_logger(__name__)


class GDPRErasureService:
    """
    Orchestrates full account erasure for a given user_id.

    All repositories receive the same session so the entire erasure is
    atomic — either all data is deleted or none of it is (depending on
    whether the caller commits or rolls back).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._scan_event_repo = ScanEventRepository(session)
        self._outbox_repo = NotificationOutboxRepository(session)
        self._signal_repo = SignalRepository(session)
        self._finding_repo = FindingRepository(session)
        self._score_repo = ScoreRepository(session)
        self._account_repo = DiscoveredAccountRepository(session)
        self._mbox_repo = MboxUploadRepository(session)
        self._scan_repo = ScanRepository(session)
        self._asset_repo = AssetRepository(session)
        self._token_repo = AuthTokenRepository(session)
        self._audit_repo = AuditRepository(session)
        self._user_repo = UserRepository(session)

    async def erase_user(self, user_id: uuid.UUID) -> None:
        """
        Delete or anonymise all personal data for user_id.

        Must be called inside an open AsyncSession.  The caller commits.
        Raises on any unexpected error; the caller should roll back.
        """
        logger.info("gdpr.erasure_started", user_id=str(user_id))

        # Step 1 — look up all email addresses before deleting assets
        # (auth_tokens are keyed by email, so we must gather them first).
        primary = await self._asset_repo.get_primary_email(user_id)
        all_emails: list[str] = []
        if primary:
            all_emails.append(primary.value)
        # Also gather any secondary verified emails.
        all_assets = await self._asset_repo.get_all_for_user(user_id)
        for a in all_assets:
            if a.entity_type == "email" and a.value not in all_emails:
                all_emails.append(a.value)

        # Step 2 — delete leaf rows in FK-safe order
        await self._scan_event_repo.delete_all_for_user(user_id)
        await self._outbox_repo.delete_all_for_user(user_id)
        await self._signal_repo.delete_all_for_user(user_id)
        await self._finding_repo.delete_all_for_user(user_id)
        await self._score_repo.delete_all_for_user(user_id)
        await self._account_repo.delete_all_for_user(user_id)
        await self._mbox_repo.delete_all_for_user(user_id)
        await self._scan_repo.delete_all_for_user(user_id)
        await self._asset_repo.delete_all_for_user(user_id)

        # Step 3 — delete auth_tokens (keyed by email)
        for email in all_emails:
            await self._token_repo.delete_for_email(email)

        # Step 4 — anonymise audit log (retain rows, null user_id)
        await self._audit_repo.anonymise_for_user(user_id)

        # Step 5 — soft-delete and scrub PII from the user row itself
        await self._user_repo.soft_delete(user_id)
        await self._user_repo.scrub_pii(user_id)

        logger.info("gdpr.erasure_complete", user_id=str(user_id))
