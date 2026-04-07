# backend/app/api/v1/imports.py
"""
Password manager vault import endpoints.

POST /imports/vault   — Upload a PM vault export file and queue processing
GET  /imports/vault   — List vault imports for the current user
GET  /imports/vault/{id} — Import status / progress
"""

import hashlib
import uuid

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
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.auth.models import User
from backend.app.core.rate_limit import limiter
from backend.app.db.models.email_accounts import VaultImportStatus, VaultImportType
from backend.app.db.repositories.assets import AssetRepository
from backend.app.db.repositories.vault_imports import VaultImportRepository
from backend.app.jobs.vault_processor import process_vault_import

router = APIRouter(prefix="/imports", tags=["imports"])

# Max vault export size: 10 MB
_MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
_UPLOAD_CHUNK_BYTES: int = 1024 * 1024

_ACCEPTED_TYPES: dict[str, str] = {
    "bitwarden": VaultImportType.BITWARDEN_JSON,
    "proton_pass": VaultImportType.PROTON_PASS_JSON,
    "1password": VaultImportType.ONEPASSWORD_1PUX,
}

_CONTENT_TYPES: dict[str, set[str]] = {
    VaultImportType.BITWARDEN_JSON: {
        "application/json",
        "text/plain",
        "application/octet-stream",
        "",
    },
    VaultImportType.PROTON_PASS_JSON: {
        "application/json",
        "text/plain",
        "application/octet-stream",
        "",
    },
    VaultImportType.ONEPASSWORD_1PUX: {
        "application/zip",
        "application/x-zip-compressed",
        "application/octet-stream",
        "",
    },
}


async def _read_upload_limited(file: UploadFile, max_bytes: int) -> bytes:
    """Read an upload incrementally and stop once the size cap is exceeded."""
    data = bytearray()
    while True:
        chunk = await file.read(_UPLOAD_CHUNK_BYTES)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds the {max_bytes // (1024 * 1024)} MB limit.",
            )
    return bytes(data)


@router.post("/vault", status_code=202)
@limiter.limit("5/hour")
async def upload_vault_export(
    request: Request,
    file: UploadFile,
    source: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """
    Accept a password manager vault export and queue it for processing.

    Query parameter:
      source — one of: bitwarden, proton_pass, 1password

    - Rate-limited: 5 imports per hour per user.
    - Idempotent: same file hash returns the existing import record.
    - Raw bytes are processed in a background task and NEVER persisted to disk.
    """
    import_type = _ACCEPTED_TYPES.get(source)
    if import_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unknown source '{source}'. "
                f"Valid values: {', '.join(_ACCEPTED_TYPES)}."
            ),
        )

    content_type = (file.content_type or "").lower()
    allowed_ct = _CONTENT_TYPES[import_type]
    if content_type not in allowed_ct:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unexpected content type for {source} export.",
        )

    data = await _read_upload_limited(file, _MAX_UPLOAD_BYTES)
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
                "importing."
            ),
        )

    import_repo = VaultImportRepository(db)

    existing = await import_repo.get_by_hash(
        user_id=current_user.id, file_hash=file_hash
    )
    if existing is not None:
        return {
            "import_id": str(existing.id),
            "status": existing.status,
            "message": "This file has already been imported.",
        }

    record = await import_repo.create(
        user_id=current_user.id,
        filename=file.filename or f"export.{source}",
        file_hash=file_hash,
        import_type=import_type,
    )
    await db.commit()

    background_tasks.add_task(
        process_vault_import,
        user_id=current_user.id,
        import_id=record.id,
        asset_id=asset.id,
        recipient_email=str(asset.value),
        import_type=import_type,
        vault_bytes=data,
    )

    return {
        "import_id": str(record.id),
        "status": VaultImportStatus.PENDING,
        "message": "Vault export queued for processing.",
    }


@router.get("/vault", status_code=200)
async def list_vault_imports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    """List vault imports for the current user."""
    import_repo = VaultImportRepository(db)
    records = await import_repo.list_for_user(
        user_id=current_user.id, limit=limit, offset=offset
    )
    return {
        "imports": [
            {
                "import_id": str(r.id),
                "filename": r.filename,
                "import_type": r.import_type,
                "status": r.status,
                "accounts_discovered": r.accounts_discovered,
                "created_at": r.created_at.isoformat(),
                "processed_at": r.processed_at.isoformat() if r.processed_at else None,
            }
            for r in records
        ],
        "limit": limit,
        "offset": offset,
    }


@router.get("/vault/{import_id}", status_code=200)
async def get_vault_import(
    import_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """Get status of a specific vault import."""
    import_repo = VaultImportRepository(db)
    record = await import_repo.get_by_id(import_id, current_user.id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Import not found."
        )

    return {
        "import_id": str(record.id),
        "filename": record.filename,
        "import_type": record.import_type,
        "status": record.status,
        "accounts_discovered": record.accounts_discovered,
        "error_detail": record.error_detail,
        "created_at": record.created_at.isoformat(),
        "processed_at": record.processed_at.isoformat()
        if record.processed_at
        else None,
    }
