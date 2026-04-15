# Phase 4 — Account Discovery Module & Background Task

## Goal
Two deliverables:
1. `AccountDiscoveryModule` — interprets `DiscoveredAccountDraft` objects and emits signals (one per discovered account). Follows `BaseModuleService` pattern.
2. `process_mbox_upload()` — background task that orchestrates the full mbox pipeline: parse → classify → persist → emit signals → update upload status. Creates its own `AsyncSession` (Rule 3).

---

## Files to Create

### 1. `backend/app/modules/identity/account_discovery/__init__.py`
Empty.

### 2. `backend/app/modules/identity/account_discovery/service.py`

```python
# backend/app/modules/identity/account_discovery/service.py
from __future__ import annotations

import uuid

from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.email_accounts.schemas import DiscoveredAccountDraft
from backend.app.modules.base.service import BaseModuleService
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)

# Signal severity by source_type
_SEVERITY_MAP: dict[str, Severity] = {
    "account_confirmation": Severity.INFO,
    "password_reset": Severity.LOW,
    "receipt": Severity.INFO,
    "newsletter": Severity.INFO,
    "security_alert": Severity.LOW,
    "other": Severity.INFO,
}


class AccountDiscoveryModule(BaseModuleService):
    """
    Converts a list of DiscoveredAccountDraft objects into SignalCreate objects.

    Does NOT:
    - Make HTTP requests
    - Access the database directly
    - Assign severity based on anything other than source_type

    Signal dedup key: (user_id, signal_type="account_discovered", entity_id=asset_id, source_ref=service_name)
    """

    module_name = "account_discovery"
    module_domain = "identity"
    required_entity_types = [EntityType.EMAIL]

    def emit_signals(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
        drafts: list[DiscoveredAccountDraft],
    ) -> list[SignalCreate]:
        """
        Build SignalCreate for each discovered account.
        Called by the background task — not part of the standard module run() flow
        because mbox uploads are user-initiated, not scan-driven.
        """
        signals: list[SignalCreate] = []

        for draft in drafts:
            severity = _SEVERITY_MAP.get(draft.source_type, Severity.INFO)
            signals.append(
                SignalCreate(
                    signal_type="account_discovered",
                    category="account_inventory",
                    entity_type=EntityType.EMAIL,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=severity,
                    confidence=Confidence.MEDIUM,
                    source=self.module_name,
                    provider="mbox_parser",
                    summary=f"Account found: {draft.display_name} ({draft.email_used})",
                    details=(
                        f"Discovered via mbox analysis. Source: {draft.source_type}. "
                        f"First seen: {draft.first_seen_at}. "
                        f"Emails from this service: {draft.email_count}."
                    ),
                    evidence={
                        "service_name": draft.service_name,
                        "display_name": draft.display_name,
                        "sender_domain": draft.sender_domain,
                        "source_type": draft.source_type,
                        "email_count": draft.email_count,
                        "login_url": draft.login_url,
                        "password_reset_url": draft.password_reset_url,
                    },
                    tags=["account_discovery", "mbox", draft.source_type],
                    recommended_action=(
                        f"Log in to {draft.display_name} and add this account to your password manager. "
                        f"Login: {draft.login_url or 'unknown'}"
                    ),
                    source_ref=f"mbox:{draft.service_name}",
                )
            )

        logger.info(
            "account_discovery.signals_built",
            user_id=str(user_id),
            signals_count=len(signals),
        )
        return signals

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
    ) -> list[SignalCreate]:
        """
        Standard module runner interface — not used for mbox processing.
        Mbox uploads are triggered via API, not the scan orchestrator.
        Returns empty list so the module can be registered without error.
        """
        return []
```

---

### 3. `backend/app/jobs/mbox_processor.py`

```python
# backend/app/jobs/mbox_processor.py
"""
Background task for processing mbox uploads.

CRITICAL: Creates its own AsyncSessionLocal() session — never receives a session parameter.
Receives only serialisable values: UUIDs (Rule 3).
"""
from __future__ import annotations

import uuid

from backend.app.core.logging import get_logger
from backend.app.db.models.email_accounts import MboxUploadStatus
from backend.app.db.repositories.discovered_accounts import DiscoveredAccountRepository
from backend.app.db.repositories.mbox_uploads import MboxUploadRepository
from backend.app.db.repositories.service_registry import ServiceRegistryRepository
from backend.app.db.repositories.signals import SignalRepository
from backend.app.db.session import AsyncSessionLocal
from backend.app.email_accounts.service import AccountDiscoveryService
from backend.app.modules.identity.account_discovery.service import AccountDiscoveryModule
from backend.app.providers.tools.mbox_parser.client import MboxParserProvider

logger = get_logger(__name__)

_parser = MboxParserProvider()
_module = AccountDiscoveryModule()


async def process_mbox_upload(
    upload_id: uuid.UUID,
    user_id: uuid.UUID,
    asset_id: uuid.UUID,
    asset_value: str,
    raw_bytes: bytes,
) -> None:
    """
    Full mbox processing pipeline. Entry point for FastAPI BackgroundTasks.

    Args:
        upload_id: ID of the MboxUpload row (already created by API endpoint)
        user_id: authenticated user
        asset_id: the Asset row id for the email address
        asset_value: the email address string (e.g. "user@example.com")
        raw_bytes: raw mbox file content (held in memory during background task)

    Steps:
        1. Mark upload PROCESSING
        2. Parse mbox → list[ParsedEmail]
        3. Load ServiceRegistry for domain matching
        4. Classify emails → list[DiscoveredAccountDraft]
        5. Upsert DiscoveredAccount rows
        6. Emit signals via SignalRepository.upsert()
        7. Mark upload COMPLETED
        On any exception → mark upload FAILED
    """
    async with AsyncSessionLocal() as session:
        upload_repo = MboxUploadRepository(session)
        account_repo = DiscoveredAccountRepository(session)
        registry_repo = ServiceRegistryRepository(session)
        signal_repo = SignalRepository(session)

        try:
            # Step 1 — mark processing
            await upload_repo.set_processing(upload_id)
            await session.commit()

            # Step 2 — parse mbox
            logger.info("mbox_processor.parsing", upload_id=str(upload_id))
            parsed_emails = _parser.parse(raw_bytes)
            logger.info(
                "mbox_processor.parsed",
                upload_id=str(upload_id),
                email_count=len(parsed_emails),
            )

            # Step 3 — load registry
            registry = await registry_repo.get_all_active()

            # Step 4 — classify
            discovery_service = AccountDiscoveryService(registry=registry)
            drafts = discovery_service.process(
                emails=parsed_emails,
                recipient_email=asset_value,
            )
            logger.info(
                "mbox_processor.classified",
                upload_id=str(upload_id),
                accounts_found=len(drafts),
            )

            # Step 5 — persist discovered accounts
            accounts_created = 0
            for draft in drafts:
                await account_repo.upsert(
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
                accounts_created += 1

            # Step 6 — emit signals
            signals = _module.emit_signals(
                user_id=user_id,
                asset_id=asset_id,
                asset_value=asset_value,
                drafts=drafts,
            )
            signals_created = 0
            for signal_data in signals:
                await signal_repo.upsert(signal_data)
                signals_created += 1

            # Step 7 — mark completed
            await upload_repo.set_completed(
                upload_id=upload_id,
                accounts_discovered=accounts_created,
                signals_created=signals_created,
            )
            await session.commit()

            logger.info(
                "mbox_processor.completed",
                upload_id=str(upload_id),
                accounts_discovered=accounts_created,
                signals_created=signals_created,
            )

        except Exception as exc:
            await session.rollback()
            logger.error(
                "mbox_processor.failed",
                upload_id=str(upload_id),
                error=str(exc),
                exc_info=True,
            )
            # Open a fresh transaction to mark failed
            async with AsyncSessionLocal() as err_session:
                err_repo = MboxUploadRepository(err_session)
                await err_repo.set_failed(upload_id=upload_id, error_detail=str(exc))
                await err_session.commit()
```

---

## Key Design Decisions

**Why does `AccountDiscoveryModule.run()` return `[]`?**
The standard `ModuleRunner` (used by the scan orchestrator) calls `run()`. Mbox uploads are user-initiated, not scan-driven. We add the module to the identity domain but its signal emission path is `emit_signals()`, called directly by `process_mbox_upload`. The empty `run()` lets the module be registered without breaking the runner.

**Why hold `raw_bytes` in memory during the background task?**
Simplicity. At ≤100 MB this is acceptable. The alternative (storing the file to temp disk) introduces cleanup complexity. `raw_bytes` is discarded when `process_mbox_upload` returns.

**Why a fresh session for the error path?**
If the main session throws an exception, it may be in a broken state. We rollback and open a fresh `AsyncSessionLocal` to write the failure status — this ensures the status update always commits even if the main pipeline crashes mid-transaction.

**Signal dedup**
`SignalRepository.upsert()` uses `on_conflict_do_update` on `uq_signal_id`. The signal ID is computed from `(user_id, signal_type, entity_id, source_ref)`. `source_ref = "mbox:{service_name}"` — so re-uploading the same mbox just refreshes the same signal, never creates duplicates.

---

## Checklist
- [ ] `backend/app/modules/identity/account_discovery/__init__.py`
- [ ] `backend/app/modules/identity/account_discovery/service.py` — `AccountDiscoveryModule` with `emit_signals()` and no-op `run()`
- [ ] `backend/app/jobs/mbox_processor.py` — `process_mbox_upload()` creates its own session, never receives one as param
- [ ] No `session` parameter in `process_mbox_upload` signature
- [ ] No HTTP calls in module
- [ ] Passes mypy

## Dependencies
- Phase 1 (repositories)
- Phase 2 (MboxParserProvider)
- Phase 3 (AccountDiscoveryService, DiscoveredAccountDraft)
