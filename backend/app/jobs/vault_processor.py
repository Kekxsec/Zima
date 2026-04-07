# backend/app/jobs/vault_processor.py
"""
Background task: process an uploaded password manager vault export.

IMPORTANT — Rule 3: creates its own AsyncSession.
NEVER accepts a request-scoped session.
All arguments are serialisable primitives (UUID, str, bytes).

Lifecycle:
  1. Mark import as PROCESSING.
  2. Parse the vault bytes with the appropriate provider (bitwarden/proton/1password).
  3. For each VaultEntry, look up ServiceRegistry and upsert a DiscoveredAccount.
  4. Mark import COMPLETED with account count.
  5. On any unhandled exception: mark FAILED and re-raise.
"""

import uuid

from backend.app.core.logging import get_logger
from backend.app.db.models.email_accounts import (
    DiscoveredAccountSourceType,
    VaultImportType,
)
from backend.app.db.repositories.discovered_accounts import DiscoveredAccountRepository
from backend.app.db.repositories.service_registry import ServiceRegistryRepository
from backend.app.db.repositories.vault_imports import VaultImportRepository
from backend.app.db.session import AsyncSessionLocal
from backend.app.providers.tools.bitwarden_export.client import BitwardenExportProvider
from backend.app.providers.tools.bitwarden_export.models import VaultEntry
from backend.app.providers.tools.onepassword_export.client import (
    OnePasswordExportProvider,
)
from backend.app.providers.tools.proton_pass_export.client import (
    ProtonPassExportProvider,
)

logger = get_logger(__name__)

_bitwarden = BitwardenExportProvider()
_proton_pass = ProtonPassExportProvider()
_onepassword = OnePasswordExportProvider()


def _extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return parsed.netloc.lower() or None
    except Exception:
        return None


async def process_vault_import(
    user_id: uuid.UUID,
    import_id: uuid.UUID,
    asset_id: uuid.UUID,
    recipient_email: str,
    import_type: str,
    vault_bytes: bytes,
) -> None:
    """
    Background task entry-point.

    Parameters
    ----------
    user_id:        The authenticated user who owns this import.
    import_id:      The VaultImport row that tracks this job.
    asset_id:       The verified Asset UUID for *recipient_email*.
    recipient_email: The email address to associate discovered accounts with.
    import_type:    One of VaultImportType constants.
    vault_bytes:    Raw vault export file content.
    """
    async with AsyncSessionLocal() as session:
        import_repo = VaultImportRepository(session)
        account_repo = DiscoveredAccountRepository(session)
        registry_repo = ServiceRegistryRepository(session)

        try:
            await import_repo.set_processing(import_id)
            await session.commit()

            # --- Parse ---
            entries: list[VaultEntry] = []
            if import_type == VaultImportType.BITWARDEN_JSON:
                entries = _bitwarden.parse(vault_bytes)
            elif import_type == VaultImportType.PROTON_PASS_JSON:
                entries = _proton_pass.parse(vault_bytes)
            elif import_type == VaultImportType.ONEPASSWORD_1PUX:
                entries = _onepassword.parse(vault_bytes)

            logger.info(
                "vault_processor.parsed",
                import_id=str(import_id),
                import_type=import_type,
                entry_count=len(entries),
            )

            # --- Upsert accounts ---
            accounts_discovered = 0

            for entry in entries:
                sender_domain = (
                    _extract_domain(entry.login_url) or entry.service_name.lower()
                )

                registry_entry = await registry_repo.find_by_domain(sender_domain)
                if registry_entry is not None:
                    service_name = registry_entry.service_name
                    display_name = registry_entry.display_name
                    login_url = registry_entry.login_url or entry.login_url
                    password_reset_url = registry_entry.password_reset_url
                else:
                    service_name = entry.service_name
                    display_name = entry.service_name
                    login_url = entry.login_url
                    password_reset_url = None

                email_used = entry.username or recipient_email

                await account_repo.upsert(
                    user_id=user_id,
                    upload_id=import_id,
                    service_name=service_name,
                    display_name=display_name,
                    email_used=email_used,
                    source_type=DiscoveredAccountSourceType.PASSWORD_MANAGER,
                    sender_domain=sender_domain,
                    login_url=login_url,
                    password_reset_url=password_reset_url,
                    first_seen_at=None,
                    last_seen_at=None,
                    email_count=1,
                    increment_email_count=False,
                )
                accounts_discovered += 1

            await import_repo.set_completed(
                import_id=import_id,
                accounts_discovered=accounts_discovered,
            )
            await session.commit()

            logger.info(
                "vault_processor.completed",
                import_id=str(import_id),
                accounts_discovered=accounts_discovered,
            )

        except Exception as exc:
            await session.rollback()
            try:
                async with AsyncSessionLocal() as err_session:
                    await VaultImportRepository(err_session).set_failed(
                        import_id=import_id,
                        error_detail=str(exc)[:1024],
                    )
                    await err_session.commit()
            except Exception:
                logger.exception(
                    "vault_processor.failed_to_mark_failed",
                    import_id=str(import_id),
                )

            logger.exception(
                "vault_processor.failed",
                import_id=str(import_id),
                error=str(exc),
            )
            raise
