# backend/app/api/v1/email_accounts.py
"""
Email Account Identifier endpoints.

POST   /email-accounts/uploads          — Upload an mbox file (rate-limited)
GET    /email-accounts/uploads          — List uploads for the current user
GET    /email-accounts/uploads/{id}     — Upload status / progress
GET    /email-accounts/accounts         — Paginated list of discovered accounts
PATCH  /email-accounts/accounts/{id}/reviewed — Mark account as reviewed
GET    /email-accounts/export           — Download all accounts as CSV
"""

import csv
import hashlib
import io
import uuid
from datetime import UTC, datetime

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.auth.models import User
from backend.app.core.rate_limit import limiter
from backend.app.db.models.email_accounts import MboxUploadStatus
from backend.app.db.repositories.assets import AssetRepository
from backend.app.db.repositories.discovered_accounts import DiscoveredAccountRepository
from backend.app.db.repositories.mbox_uploads import MboxUploadRepository
from backend.app.db.repositories.signals import SignalRepository
from backend.app.email_accounts.priority import AccountPriority
from backend.app.email_accounts.priority import score as priority_score
from backend.app.jobs.mbox_processor import process_mbox_upload

router = APIRouter(prefix="/email-accounts", tags=["email-accounts"])

# Max mbox size: 100 MB
_MAX_UPLOAD_BYTES: int = 100 * 1024 * 1024


# ---------------------------------------------------------------------------
# Upload endpoints
# ---------------------------------------------------------------------------


@router.post("/uploads", status_code=202)
@limiter.limit("2/hour")
async def upload_mbox(
    request: Request,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """
    Accept an mbox file and queue it for processing.

    - Tier-gated: Plus / Pro / Business only.
    - Rate-limited: 2 uploads per hour per user.
    - Idempotent: same file hash returns the existing upload record.
    - Raw bytes are processed in a background task and NEVER persisted to disk.
    """

    # Validate content type loosely. Accept application/mbox, text/plain,
    # and application/octet-stream.
    content_type = (file.content_type or "").lower()
    if content_type not in {
        "application/mbox",
        "text/plain",
        "application/octet-stream",
        "",
    }:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Expected an mbox file.",
        )

    data = await file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
        )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file."
        )

    file_hash = hashlib.sha256(data).hexdigest()

    # Resolve the user's primary verified email asset
    asset_repo = AssetRepository(db)
    asset = await asset_repo.get_primary_email(current_user.id)
    if asset is None or not asset.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No verified email address found. Please verify an email before "
                "uploading."
            ),
        )

    upload_repo = MboxUploadRepository(db)

    # Idempotency: if same file was already uploaded, return existing record
    existing = await upload_repo.get_by_hash(
        user_id=current_user.id, file_hash=file_hash
    )
    if existing is not None:
        return {
            "upload_id": str(existing.id),
            "status": existing.status,
            "message": "This file has already been uploaded.",
        }

    upload = await upload_repo.create(
        user_id=current_user.id,
        filename=file.filename or "upload.mbox",
        file_hash=file_hash,
    )
    await db.commit()

    # Pass only serialisable values to the background task (Rule 3)
    background_tasks.add_task(
        process_mbox_upload,
        user_id=current_user.id,
        upload_id=upload.id,
        asset_id=asset.id,
        recipient_email=str(asset.value),
        mbox_bytes=data,
    )

    return {"upload_id": str(upload.id), "status": MboxUploadStatus.PENDING}


@router.get("/uploads")
async def list_uploads(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    upload_repo = MboxUploadRepository(db)
    uploads = await upload_repo.list_for_user(
        user_id=current_user.id, limit=limit, offset=offset
    )
    return {
        "uploads": [_upload_to_dict(u) for u in uploads],
        "limit": limit,
        "offset": offset,
    }


@router.get("/uploads/{upload_id}")
async def get_upload_status(
    upload_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    try:
        uid = uuid.UUID(upload_id)
    except ValueError as err:
        raise HTTPException(
            status_code=422,
            detail="Invalid upload ID format.",
        ) from err

    upload_repo = MboxUploadRepository(db)
    upload = await upload_repo.get_by_id(upload_id=uid, user_id=current_user.id)
    if upload is None:
        raise HTTPException(status_code=404, detail="Upload not found.")
    return _upload_to_dict(upload)


# ---------------------------------------------------------------------------
# Discovered accounts endpoints
# ---------------------------------------------------------------------------


@router.get("/accounts")
async def list_accounts(
    service_name: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    is_reviewed: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    account_repo = DiscoveredAccountRepository(db)
    accounts = await account_repo.list_for_user(
        user_id=current_user.id,
        service_name=service_name,
        source_type=source_type,
        is_reviewed=is_reviewed,
        limit=limit,
        offset=offset,
    )
    total = await account_repo.count_for_user(current_user.id)
    return {
        "accounts": [_account_to_dict(a) for a in accounts],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/accounts/{account_id}/reviewed", status_code=200)
async def mark_account_reviewed(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    try:
        aid = uuid.UUID(account_id)
    except ValueError as err:
        raise HTTPException(
            status_code=422,
            detail="Invalid account ID format.",
        ) from err

    account_repo = DiscoveredAccountRepository(db)
    updated = await account_repo.mark_reviewed(account_id=aid, user_id=current_user.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Account not found.")
    await db.commit()
    return {"account_id": account_id, "is_reviewed": True}


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

# Generic / Zima format
_GENERIC_HEADERS = [
    "priority_tier",
    "priority_label",
    "is_breached",
    "display_name",
    "category",
    "email_used",
    "source_type",
    "login_url",
    "password_reset_url",
    "email_count",
    "first_seen",
    "last_seen",
    "notes",
]

# 1Password CSV import format
# https://support.1password.com/import-csv/
_1PASSWORD_HEADERS = ["Title", "Username", "Password", "Website", "Notes"]

# Bitwarden CSV import format
# https://bitwarden.com/help/condition-bitwarden-import/
_BITWARDEN_HEADERS = [
    "folder",
    "favorite",
    "type",
    "name",
    "notes",
    "fields",
    "reprompt",
    "login_uri",
    "login_username",
    "login_password",
    "login_totp",
]


def _build_notes(
    priority: AccountPriority,
    source_type: str,
    is_breached: bool,
    category: str | None,
    email_count: int,
    password_reset_url: str | None,
) -> str:
    parts = [
        f"Priority: {priority.label}",
        priority.reason,
        f"Category: {category or 'unknown'}",
        f"Signal: {source_type}",
        f"Emails in inbox: {email_count}",
    ]
    if is_breached:
        parts.append("⚠ Email found in a data breach")
    if password_reset_url:
        parts.append(f"Reset password at: {password_reset_url}")
    parts.append("Discovered by Zima")
    return " | ".join(parts)


@router.get("/export")
async def export_accounts(
    export_format: str = Query(
        default="generic",
        alias="format",
        pattern="^(generic|1password|bitwarden)$",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """
    Download all discovered accounts as a CSV file, sorted by priority.

    ?format=generic     Zima native format — all fields including priority tier,
                        breach flag, and reset URLs. Best for review.
    ?format=1password   Ready to import into 1Password (Title/Username/Website/Notes).
    ?format=bitwarden   Ready to import into Bitwarden (folder per priority tier).

    Accounts are sorted P1 → P4 so the most critical appear first.
    The BOM (utf-8-sig) ensures Excel opens the file without encoding issues.
    """

    account_repo = DiscoveredAccountRepository(db)
    signal_repo = SignalRepository(db)

    accounts_with_category = await account_repo.get_all_for_user_export_with_category(
        user_id=current_user.id
    )
    breached_emails = await signal_repo.get_breached_entity_values_for_user(
        user_id=current_user.id
    )

    # Score and sort
    scored: list[tuple[AccountPriority, object, str | None]] = []
    for account, category in accounts_with_category:
        is_breached = account.email_used in breached_emails
        p = priority_score(category, account.source_type, is_breached)
        scored.append((p, account, category))

    scored.sort(key=lambda x: x[0].sort_key)

    buf = io.StringIO()
    buf.write("\ufeff")  # BOM for Excel

    if export_format == "1password":
        headers = _1PASSWORD_HEADERS
    elif export_format == "bitwarden":
        headers = _BITWARDEN_HEADERS
    else:
        headers = _GENERIC_HEADERS

    writer = csv.DictWriter(buf, fieldnames=headers, lineterminator="\r\n")
    writer.writeheader()

    for priority, a, category in scored:  # type: ignore[assignment]
        is_breached = a.email_used in breached_emails  # type: ignore[union-attr]
        notes = _build_notes(
            priority,
            a.source_type,  # type: ignore[union-attr]
            is_breached,
            category,
            a.email_count,  # type: ignore[union-attr]
            a.password_reset_url,  # type: ignore[union-attr]
        )

        if export_format == "1password":
            writer.writerow(
                {
                    "Title": a.display_name,  # type: ignore[union-attr]
                    "Username": a.email_used,  # type: ignore[union-attr]
                    "Password": "",
                    "Website": a.login_url or "",  # type: ignore[union-attr]
                    "Notes": notes,
                }
            )
        elif export_format == "bitwarden":
            writer.writerow(
                {
                    "folder": f"Zima / {priority.label}",
                    "favorite": "1" if priority.tier == 1 else "0",
                    "type": "login",
                    "name": a.display_name,  # type: ignore[union-attr]
                    "notes": notes,
                    "fields": "",
                    "reprompt": "0",
                    "login_uri": a.login_url or "",  # type: ignore[union-attr]
                    "login_username": a.email_used,  # type: ignore[union-attr]
                    "login_password": "",
                    "login_totp": "",
                }
            )
        else:
            writer.writerow(
                {
                    "priority_tier": priority.tier,
                    "priority_label": priority.label,
                    "is_breached": str(is_breached).lower(),
                    "display_name": a.display_name,  # type: ignore[union-attr]
                    "category": category or "unknown",
                    "email_used": a.email_used,  # type: ignore[union-attr]
                    "source_type": a.source_type,  # type: ignore[union-attr]
                    "login_url": a.login_url or "",  # type: ignore[union-attr]
                    "password_reset_url": a.password_reset_url or "",  # type: ignore[union-attr]
                    "email_count": a.email_count,  # type: ignore[union-attr]
                    "first_seen": _fmt_dt(a.first_seen_at),  # type: ignore[union-attr]
                    "last_seen": _fmt_dt(a.last_seen_at),  # type: ignore[union-attr]
                    "notes": priority.reason,
                }
            )

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"zima_accounts_{export_format}_{timestamp}.csv"

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _fmt_dt(dt: object) -> str:
    if dt is None:
        return ""
    if hasattr(dt, "isoformat"):
        return dt.isoformat()  # type: ignore[union-attr]
    return str(dt)


def _upload_to_dict(u: object) -> dict[str, object]:
    return {
        "id": str(u.id),  # type: ignore[union-attr]
        "filename": u.filename,  # type: ignore[union-attr]
        "status": u.status,  # type: ignore[union-attr]
        "accounts_discovered": u.accounts_discovered,  # type: ignore[union-attr]
        "signals_created": u.signals_created,  # type: ignore[union-attr]
        "error_detail": u.error_detail,  # type: ignore[union-attr]
        "processed_at": _fmt_dt(u.processed_at),  # type: ignore[union-attr]
        "created_at": _fmt_dt(u.created_at),  # type: ignore[union-attr]
    }


def _account_to_dict(a: object) -> dict[str, object]:
    return {
        "id": str(a.id),  # type: ignore[union-attr]
        "service_name": a.service_name,  # type: ignore[union-attr]
        "display_name": a.display_name,  # type: ignore[union-attr]
        "email_used": a.email_used,  # type: ignore[union-attr]
        "source_type": a.source_type,  # type: ignore[union-attr]
        "sender_domain": a.sender_domain,  # type: ignore[union-attr]
        "login_url": a.login_url,  # type: ignore[union-attr]
        "password_reset_url": a.password_reset_url,  # type: ignore[union-attr]
        "email_count": a.email_count,  # type: ignore[union-attr]
        "first_seen_at": _fmt_dt(a.first_seen_at),  # type: ignore[union-attr]
        "last_seen_at": _fmt_dt(a.last_seen_at),  # type: ignore[union-attr]
        "is_reviewed": a.is_reviewed,  # type: ignore[union-attr]
        "created_at": _fmt_dt(a.created_at),  # type: ignore[union-attr]
    }
