# Phase 5 — API Endpoints

## Goal
Five REST endpoints for the email account identifier feature. Multipart file upload, background task queuing, status polling, account listing, account review, and CSV export.

---

## Files to Create / Modify

### 1. `backend/app/api/v1/email_accounts.py` (new)

```python
# backend/app/api/v1/email_accounts.py
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.assets.models import Asset
from backend.app.auth.models import User
from backend.app.core.enums import Tier
from backend.app.core.rate_limit import limiter
from backend.app.db.models.email_accounts import MboxUploadStatus
from backend.app.db.repositories.assets import AssetRepository
from backend.app.db.repositories.discovered_accounts import DiscoveredAccountRepository
from backend.app.db.repositories.mbox_uploads import MboxUploadRepository
from backend.app.jobs.mbox_processor import process_mbox_upload
from backend.app.providers.tools.mbox_parser.client import MboxParserProvider

router = APIRouter(prefix="/email-accounts", tags=["email-accounts"])

_MBOX_MAX_BYTES = 100 * 1024 * 1024   # 100 MB
_ALLOWED_TIERS = {Tier.PLUS, Tier.PRO, Tier.BUSINESS}

_parser = MboxParserProvider()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    upload_id: str
    status: str


class UploadStatusResponse(BaseModel):
    upload_id: str
    filename: str
    status: str
    accounts_discovered: int
    signals_created: int
    error_detail: str | None
    created_at: datetime
    processed_at: datetime | None


class DiscoveredAccountResponse(BaseModel):
    id: str
    service_name: str
    display_name: str
    email_used: str
    source_type: str
    login_url: str | None
    password_reset_url: str | None
    sender_domain: str
    email_count: int
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    is_reviewed: bool
    created_at: datetime


class DiscoveredAccountListResponse(BaseModel):
    accounts: list[DiscoveredAccountResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_tier(user: User) -> None:
    if Tier(user.tier) not in _ALLOWED_TIERS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email account discovery requires Plus tier or above.",
        )


async def _get_primary_email_asset(user: User, db: AsyncSession) -> Asset:
    asset_repo = AssetRepository(db)
    asset = await asset_repo.get_primary_email(user.id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No verified primary email asset found. Verify an email address first.",
        )
    return asset


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("2/hour")
async def upload_mbox(
    request: Request,  # required by slowapi
    background_tasks: BackgroundTasks,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UploadResponse:
    """
    Upload an mbox file. Returns immediately with upload_id; processing runs in background.
    Rate limited to 2 uploads per hour. Requires Plus tier or above.
    Idempotent: uploading the same file twice returns the existing upload_id.
    """
    _require_tier(current_user)

    # Read file into memory (enforced limit)
    raw_bytes = await file.read(_MBOX_MAX_BYTES + 1)
    if len(raw_bytes) > _MBOX_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {_MBOX_MAX_BYTES // (1024*1024)} MB.",
        )

    file_hash = _parser.compute_hash(raw_bytes)
    upload_repo = MboxUploadRepository(db)

    # Idempotency check
    existing = await upload_repo.get_by_hash(user_id=current_user.id, file_hash=file_hash)
    if existing:
        return UploadResponse(upload_id=str(existing.id), status=existing.status)

    # Get primary email asset (required for signal emission)
    asset = await _get_primary_email_asset(current_user, db)

    # Create upload record
    filename = file.filename or "upload.mbox"
    upload = await upload_repo.create(
        user_id=current_user.id,
        filename=filename[:512],
        file_hash=file_hash,
    )
    await db.commit()

    # Queue background task — pass only serialisable values
    background_tasks.add_task(
        process_mbox_upload,
        upload_id=upload.id,
        user_id=current_user.id,
        asset_id=asset.id,
        asset_value=asset.value,
        raw_bytes=raw_bytes,
    )

    return UploadResponse(upload_id=str(upload.id), status=MboxUploadStatus.PENDING)


@router.get("/upload/{upload_id}", response_model=UploadStatusResponse)
async def get_upload_status(
    upload_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UploadStatusResponse:
    """Poll this endpoint after uploading to check processing status."""
    try:
        upload_uuid = uuid.UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid upload ID format")

    upload_repo = MboxUploadRepository(db)
    upload = await upload_repo.get_by_id(upload_uuid, current_user.id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    return UploadStatusResponse(
        upload_id=str(upload.id),
        filename=upload.filename,
        status=upload.status,
        accounts_discovered=upload.accounts_discovered,
        signals_created=upload.signals_created,
        error_detail=upload.error_detail,
        created_at=upload.created_at,
        processed_at=upload.processed_at,
    )


@router.get("/discovered", response_model=DiscoveredAccountListResponse)
async def list_discovered_accounts(
    service_name: str | None = None,
    source_type: str | None = None,
    is_reviewed: bool | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DiscoveredAccountListResponse:
    """
    List all discovered accounts for the authenticated user.
    Supports filtering by service_name, source_type, and is_reviewed.
    """
    account_repo = DiscoveredAccountRepository(db)
    accounts = await account_repo.list_for_user(
        user_id=current_user.id,
        service_name=service_name,
        source_type=source_type,
        is_reviewed=is_reviewed,
        limit=min(limit, 200),
        offset=offset,
    )
    total = await account_repo.count_for_user(current_user.id)

    return DiscoveredAccountListResponse(
        accounts=[
            DiscoveredAccountResponse(
                id=str(a.id),
                service_name=a.service_name,
                display_name=a.display_name,
                email_used=a.email_used,
                source_type=a.source_type,
                login_url=a.login_url,
                password_reset_url=a.password_reset_url,
                sender_domain=a.sender_domain,
                email_count=a.email_count,
                first_seen_at=a.first_seen_at,
                last_seen_at=a.last_seen_at,
                is_reviewed=a.is_reviewed,
                created_at=a.created_at,
            )
            for a in accounts
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/discovered/{account_id}/review", status_code=status.HTTP_200_OK)
async def mark_account_reviewed(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Mark a discovered account as reviewed by the user."""
    try:
        account_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid account ID format")

    account_repo = DiscoveredAccountRepository(db)
    updated = await account_repo.mark_reviewed(account_uuid, current_user.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Account not found")

    await db.commit()
    return {"account_id": account_id, "is_reviewed": "true"}


@router.get("/export/csv")
async def export_accounts_csv(
    reviewed_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """
    Export discovered accounts as CSV compatible with common password managers.

    Column order matches 1Password / Bitwarden generic CSV import format:
    Title, Username, Password, URL, Notes, TOTP, Favorite, Type
    (Password and TOTP are left blank — user fills these in the password manager.)
    """
    account_repo = DiscoveredAccountRepository(db)
    accounts = await account_repo.get_all_for_user_export(current_user.id)

    if reviewed_only:
        accounts = [a for a in accounts if a.is_reviewed]

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)

    # Header row — compatible with 1Password / Bitwarden generic import
    writer.writerow([
        "Title",
        "Username",
        "Password",
        "URL",
        "Password Reset URL",
        "Notes",
        "TOTP",
        "Favorite",
        "Type",
    ])

    for account in accounts:
        writer.writerow([
            account.display_name,
            account.email_used,
            "",                            # Password — blank, user fills in PM
            account.login_url or "",
            account.password_reset_url or "",
            f"Source: {account.source_type}. Emails: {account.email_count}. Domain: {account.sender_domain}.",
            "",                            # TOTP — blank
            "0",
            "Login",
        ])

    csv_content = output.getvalue()
    filename = f"zima-accounts-{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8-sig")),  # utf-8-sig for Excel compatibility
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

---

### 2. `backend/app/main.py` — Register router (modify)

Add to the existing router includes section:

```python
from backend.app.api.v1.email_accounts import router as email_accounts_router
app.include_router(email_accounts_router, prefix="/api/v1")
```

---

### 3. `backend/app/core/config.py` — Add settings (modify)

Add to the `Settings` class:

```python
# Email account discovery
mbox_max_size_mb: int = 100
enable_account_discovery: bool = True
```

---

## Endpoint Summary

| Method | Path | Auth | Rate Limit | Description |
|--------|------|------|------------|-------------|
| POST | `/api/v1/email-accounts/upload` | JWT | 2/hour | Upload mbox file |
| GET | `/api/v1/email-accounts/upload/{upload_id}` | JWT | — | Poll upload status |
| GET | `/api/v1/email-accounts/discovered` | JWT | — | List discovered accounts |
| PATCH | `/api/v1/email-accounts/discovered/{id}/review` | JWT | — | Mark account reviewed |
| GET | `/api/v1/email-accounts/export/csv` | JWT | — | Download CSV |

---

## Notes

**Why `utf-8-sig` for CSV?**
The BOM (`\ufeff`) at the start of the file causes Excel on Windows to auto-detect UTF-8 encoding, preventing mojibake in service names with non-ASCII characters.

**Why `reviewed_only` query param instead of separate endpoint?**
Single endpoint is simpler and avoids route proliferation. Most password manager imports want all accounts; the flag is a convenience for users who want to curate before export.

**Why not store raw bytes in the DB?**
Privacy. We pass `raw_bytes` directly from the API layer to the background task as an in-memory parameter. The bytes live only in the worker process during processing, then are discarded. Never written to disk or DB.

**Tier gating**
`_require_tier()` raises HTTP 403 if `Tier(user.tier) not in {PLUS, PRO, BUSINESS}`. CORE users get a clear error message.

---

## Checklist
- [ ] `backend/app/api/v1/email_accounts.py` — all 5 endpoints
- [ ] Router registered in `backend/app/main.py`
- [ ] `mbox_max_size_mb` and `enable_account_discovery` added to `Settings`
- [ ] `UploadFile` dependency works with slowapi `@limiter.limit`
- [ ] CSV export tested against 1Password and Bitwarden import
- [ ] Passes mypy

## Dependencies
- Phase 1 (repositories)
- Phase 3 (MboxParserProvider.compute_hash)
- Phase 4 (process_mbox_upload background task)
