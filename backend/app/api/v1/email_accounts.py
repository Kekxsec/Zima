# backend/app/api/v1/email_accounts.py
"""
Email Account Identifier endpoints.

POST /email-accounts/uploads                  — Upload an mbox file (rate-limited)
POST /email-accounts/uploads/folder           — Upload a mailbox export folder
GET  /email-accounts/uploads                  — List uploads for the current user
GET  /email-accounts/uploads/{id}             — Upload status / progress
GET  /email-accounts/accounts                 — Paginated list of discovered accounts
PATCH /email-accounts/accounts/{id}/reviewed  — Mark account as reviewed
PATCH /email-accounts/accounts/{id}/verdict   — Set triage verdict
POST /email-accounts/accounts/{id}/alias      — Create email alias for an account
GET  /email-accounts/export                   — Download all accounts as CSV
"""

import asyncio
import csv
import hashlib
import io
import os
import re
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.auth.models import User
from backend.app.core.config import settings
from backend.app.core.crypto import CryptoError, decrypt_field
from backend.app.core.logging import get_logger
from backend.app.core.rate_limit import limiter
from backend.app.db.models.email_accounts import (
    DiscoveredAccount,
    MboxUpload,
    MboxUploadStatus,
    ServiceRegistry,
)
from backend.app.db.models.integrations import IntegrationProvider
from backend.app.db.repositories.assets import AssetRepository
from backend.app.db.repositories.discovered_accounts import DiscoveredAccountRepository
from backend.app.db.repositories.mbox_uploads import MboxUploadRepository
from backend.app.db.repositories.service_registry import ServiceRegistryRepository
from backend.app.db.repositories.signals import SignalRepository
from backend.app.db.repositories.user_integrations import UserIntegrationRepository
from backend.app.email_accounts.priority import AccountPriority
from backend.app.email_accounts.priority import score as priority_score
from backend.app.jobs.mbox_processor import process_mbox_upload
from backend.app.providers.actions.addy_io.client import AddyIoProvider
from backend.app.providers.actions.simplelogin.client import SimpleLoginProvider
from backend.app.providers.base.exceptions import ProviderAuthError, ProviderError

router = APIRouter(prefix="/email-accounts", tags=["email-accounts"])
logger = get_logger(__name__)

# Max mailbox export size: configurable, defaults to 1 GB
_MAX_UPLOAD_BYTES: int = settings.mailbox_upload_max_mb * 1024 * 1024
_UPLOAD_CHUNK_BYTES: int = 1024 * 1024
_MAX_CHUNK_UPLOAD_CHUNKS = 512  # 512 × 2 MB = 1 GB max
_MAX_FOLDER_UPLOAD_FILES = 50_000
_MAIL_UPLOAD_CONTENT_TYPES: set[str] = {
    "application/mbox",
    "application/zip",
    "application/x-zip-compressed",
    "text/plain",
    "application/octet-stream",
    "",
}

_GENERIC_ACCOUNT_NAME_TOKENS: frozenset[str] = frozenset(
    {
        "your",
        "account",
        "service",
        "email",
        "message",
        "support",
        "team",
        "notification",
        "update",
        "security",
        "noreply",
        "unknown",
    }
)

_MULTIPART_PUBLIC_SUFFIXES: frozenset[str] = frozenset(
    {
        "co.uk",
        "org.uk",
        "gov.uk",
        "ac.uk",
        "com.au",
        "net.au",
        "org.au",
        "co.nz",
        "co.jp",
        "com.br",
        "com.mx",
        "co.za",
    }
)


def _upload_suffix(filename: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix in {".mbox", ".zip"}:
        return suffix
    return ".upload"


def _normalise_upload_path(filename: str | None, index: int) -> Path:
    raw = (filename or f"file-{index}").replace("\\", "/")
    parts = [part for part in PurePosixPath(raw).parts if part not in {"", "."}]
    if not parts or any(part == ".." for part in parts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid folder upload path.",
        )
    return Path(*parts)


async def _stream_upload_to_tempfile(
    file: UploadFile,
    max_bytes: int,
) -> tuple[str, str]:
    """Stream a mailbox export upload to a temp file with hashing."""
    bytes_seen = 0
    hasher = hashlib.sha256()
    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=_upload_suffix(file.filename),
        prefix="zima-upload-",
    )

    try:
        while True:
            chunk = await file.read(_UPLOAD_CHUNK_BYTES)
            if not chunk:
                break
            bytes_seen += len(chunk)
            if bytes_seen > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds the {max_bytes // (1024 * 1024)} MB limit.",
                )
            hasher.update(chunk)
            temp_file.write(chunk)
    except Exception:
        temp_file.close()
        os.unlink(temp_file.name)
        raise

    temp_file.close()
    if bytes_seen == 0:
        os.unlink(temp_file.name)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file.",
        )

    return temp_file.name, hasher.hexdigest()


async def _write_upload_files_to_tempdir(
    files: list[UploadFile],
    max_bytes: int,
) -> tuple[str, str, str]:
    """Write uploaded files to a temp directory with hashing and validation."""
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty folder upload.",
        )
    if len(files) > _MAX_FOLDER_UPLOAD_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files. Max is {_MAX_FOLDER_UPLOAD_FILES}.",
        )

    temp_dir = Path(tempfile.mkdtemp(prefix="zima-upload-dir-"))
    bytes_seen = 0
    hasher = hashlib.sha256()
    seen_paths: set[Path] = set()
    eml_found = False
    eml_file_count = 0
    root_label = "proton-export"

    try:
        for index, upload_file in enumerate(files):
            relative_path = _normalise_upload_path(upload_file.filename, index)

            if relative_path in seen_paths:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Folder upload contains duplicate file paths.",
                )
            seen_paths.add(relative_path)

            if index == 0 and len(relative_path.parts) > 1:
                root_label = relative_path.parts[0]
            elif index == 0:
                root_label = relative_path.stem or root_label

            hasher.update(relative_path.as_posix().encode("utf-8"))
            hasher.update(b"\0")

            dest_path = temp_dir / relative_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            with dest_path.open("wb") as dest_file:
                while True:
                    chunk = await upload_file.read(_UPLOAD_CHUNK_BYTES)
                    if not chunk:
                        break
                    bytes_seen += len(chunk)
                    if bytes_seen > max_bytes:
                        mb = max_bytes // (1024 * 1024)
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Folder exceeds {mb} MB limit.",
                        )
                    hasher.update(chunk)
                    dest_file.write(chunk)

            if relative_path.suffix.lower() == ".eml":
                eml_found = True
                eml_file_count += 1

    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    if bytes_seen == 0:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty folder upload.",
        )
    if not eml_found:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Folder upload must include at least one .eml file.",
        )

    logger.info(
        "email_accounts.folder_upload_written",
        root_label=root_label,
        file_count=len(files),
        eml_file_count=eml_file_count,
        bytes_seen=bytes_seen,
    )
    return str(temp_dir), hasher.hexdigest(), root_label


async def _write_batch_files_to_dir(
    files: list[UploadFile],
    dest_dir: Path,
    max_total_bytes: int,
) -> None:
    """Append a batch of uploaded files into an accumulation directory."""
    if not files:
        return
    existing_bytes = sum(f.stat().st_size for f in dest_dir.rglob("*") if f.is_file())
    bytes_seen = existing_bytes
    for index, upload_file in enumerate(files):
        relative_path = _normalise_upload_path(upload_file.filename, index)
        dest_path = dest_dir / relative_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with dest_path.open("wb") as dest_file:
            while True:
                chunk = await upload_file.read(_UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                bytes_seen += len(chunk)
                if bytes_seen > max_total_bytes:
                    mb = max_total_bytes // (1024 * 1024)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Folder exceeds {mb} MB limit.",
                    )
                dest_file.write(chunk)


def _hash_and_label_directory(dir_path: Path) -> tuple[str, str, bool]:
    """Return (sha256_hex, root_label, eml_found) for all files in dir_path."""
    hasher = hashlib.sha256()
    eml_found = False
    root_label = "proton-export"
    sorted_files = sorted(
        (f for f in dir_path.rglob("*") if f.is_file()),
        key=lambda f: f.relative_to(dir_path).as_posix(),
    )
    for i, file_path in enumerate(sorted_files):
        rel = file_path.relative_to(dir_path)
        if i == 0:
            parts = rel.parts
            root_label = parts[0] if len(parts) > 1 else (rel.stem or root_label)
        hasher.update(rel.as_posix().encode("utf-8"))
        hasher.update(b"\0")
        with file_path.open("rb") as f:
            while chunk := f.read(_UPLOAD_CHUNK_BYTES):
                hasher.update(chunk)
        if rel.suffix.lower() == ".eml":
            eml_found = True
    return hasher.hexdigest(), root_label, eml_found


async def _require_verified_primary_email(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> None:
    asset_repo = AssetRepository(db)
    asset = await asset_repo.get_primary_email(user_id)
    if asset is None or not asset.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No verified email address found. Please verify an email before "
                "uploading."
            ),
        )
    return asset


def _enqueue_mailbox_processing(
    background_tasks: BackgroundTasks,
    *,
    user_id: uuid.UUID,
    upload_id: uuid.UUID,
    asset_id: uuid.UUID,
    recipient_email: str,
    mbox_path: str,
) -> None:
    background_tasks.add_task(
        process_mbox_upload,
        user_id=user_id,
        upload_id=upload_id,
        asset_id=asset_id,
        recipient_email=recipient_email,
        mbox_path=mbox_path,
    )


# ---------------------------------------------------------------------------
# Upload endpoints
# ---------------------------------------------------------------------------


@router.post("/uploads", status_code=202)
@limiter.limit("2/hour")
async def upload_mbox(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """
    Accept a mailbox export and queue it for processing.

    - Rate-limited: 2 uploads per hour per user.
    - Idempotent: same file hash returns the existing upload record.
    - Upload bytes are streamed to a temp file to avoid holding large inboxes
      in memory before background processing starts.
    """
    # Validate content type loosely. Accept mbox files and Proton export archives.
    content_type = (file.content_type or "").lower()
    if content_type not in _MAIL_UPLOAD_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Expected an .mbox file or Proton Mail export .zip archive.",
        )

    temp_path, file_hash = await _stream_upload_to_tempfile(file, _MAX_UPLOAD_BYTES)

    try:
        asset = await _require_verified_primary_email(db, current_user.id)
        upload_repo = MboxUploadRepository(db)

        # Idempotency: block duplicate only when prior upload succeeded or is in-flight.
        # A FAILED upload is treated as if it never happened — delete it and retry.
        existing = await upload_repo.get_by_hash(
            user_id=current_user.id, file_hash=file_hash
        )
        if existing is not None:
            if existing.status == MboxUploadStatus.FAILED:
                await upload_repo.delete_by_id(existing.id)
                await db.commit()
            else:
                os.unlink(temp_path)
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "upload_id": str(existing.id),
                        "status": existing.status,
                        "message": "This file has already been uploaded.",
                    },
                )

        upload = await upload_repo.create(
            user_id=current_user.id,
            filename=file.filename or "upload.mbox",
            file_hash=file_hash,
        )
        await db.commit()

        _enqueue_mailbox_processing(
            background_tasks,
            user_id=current_user.id,
            upload_id=upload.id,
            asset_id=asset.id,
            recipient_email=str(asset.value),
            mbox_path=temp_path,
        )
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

    return {"upload_id": str(upload.id), "status": MboxUploadStatus.PENDING}


@router.post("/uploads/chunked", status_code=200)
async def upload_mbox_chunk(
    background_tasks: BackgroundTasks,
    token: str = Form(...),
    index: int = Form(...),
    total: int = Form(...),
    filename: str = Form("upload.mbox"),
    chunk: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """
    Accept one chunk of a client-side chunked mailbox upload.

    The client splits the file into ≤2 MB pieces, POSTs each chunk in order,
    and tracks progress locally.  This approach gives real-time byte-level
    progress on any network because each chunk receives an immediate
    acknowledgement before the next is sent.

    - token:    client-generated UUID identifying this upload session
    - index:    0-based position of this chunk
    - total:    total number of chunks in the upload
    - filename: original filename (used for the upload record)
    - chunk:    raw file data for this chunk

    Intermediate chunks return {"status": "received"}.
    The final chunk assembles the file, rate-checks, and enqueues processing,
    returning {"upload_id": "...", "status": "pending"}.
    """
    try:
        uuid.UUID(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload token."
        ) from exc

    if not (0 <= index < total <= _MAX_CHUNK_UPLOAD_CHUNKS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chunk parameters.",
        )

    chunk_dir = Path(tempfile.gettempdir()) / f"zima-chunk-{current_user.id}-{token}"
    chunk_dir.mkdir(exist_ok=True)

    chunk_data = await chunk.read()
    if not chunk_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Empty chunk."
        )

    # Guard cumulative upload size
    existing_size = sum(f.stat().st_size for f in chunk_dir.iterdir() if f.is_file())
    if existing_size + len(chunk_data) > _MAX_UPLOAD_BYTES:
        shutil.rmtree(chunk_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Upload exceeds {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
        )

    (chunk_dir / f"{index:06d}").write_bytes(chunk_data)

    # Intermediate chunk — acknowledge and wait for the next one
    if index < total - 1:
        return {"status": "received", "index": index}

    # Last chunk: verify all pieces arrived
    received = {int(f.name) for f in chunk_dir.iterdir() if f.name.isdigit()}
    missing = set(range(total)) - received
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing chunks: {sorted(missing)[:5]}",
        )

    # Assemble into a single temp file
    hasher = hashlib.sha256()
    assembled = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=_upload_suffix(filename),
        prefix="zima-upload-",
    )
    try:
        for i in range(total):
            data = (chunk_dir / f"{i:06d}").read_bytes()
            hasher.update(data)
            assembled.write(data)
        assembled.close()
        shutil.rmtree(chunk_dir, ignore_errors=True)
    except Exception:
        assembled.close()
        os.unlink(assembled.name)
        shutil.rmtree(chunk_dir, ignore_errors=True)
        raise

    file_hash = hasher.hexdigest()
    temp_path = assembled.name

    try:
        asset = await _require_verified_primary_email(db, current_user.id)
        upload_repo = MboxUploadRepository(db)

        # Rate-limit: max 2 new upload records created per hour
        recent_count = await upload_repo.count_recent(user_id=current_user.id, hours=1)
        if recent_count >= 2:
            os.unlink(temp_path)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Import limit reached (2/hr). Try again later.",
            )

        existing = await upload_repo.get_by_hash(
            user_id=current_user.id, file_hash=file_hash
        )
        if existing is not None:
            if existing.status == MboxUploadStatus.FAILED:
                await upload_repo.delete_by_id(existing.id)
                await db.commit()
            else:
                os.unlink(temp_path)
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "upload_id": str(existing.id),
                        "status": existing.status,
                        "message": "This file has already been uploaded.",
                    },
                )

        upload = await upload_repo.create(
            user_id=current_user.id,
            filename=filename or "upload.mbox",
            file_hash=file_hash,
        )
        await db.commit()

        _enqueue_mailbox_processing(
            background_tasks,
            user_id=current_user.id,
            upload_id=upload.id,
            asset_id=asset.id,
            recipient_email=str(asset.value),
            mbox_path=temp_path,
        )
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

    return {"upload_id": str(upload.id), "status": MboxUploadStatus.PENDING}


@router.post("/uploads/folder", status_code=202)
async def upload_mail_folder(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """
    Accept a batched mailbox export folder upload and queue it for processing.

    Clients split the folder into batches of ≤500 files and POST each batch with:
      - token:         client UUID identifying the upload session
      - batch_index:   0-based index of this batch
      - total_batches: total number of batches
      - files:         the file parts for this batch

    Intermediate batches return {"status": "received", "batch_index": N}.
    The final batch finalises, rate-checks, and enqueues processing.
    """
    content_type_header = request.headers.get("content-type", "<missing>")
    content_length_header = request.headers.get("content-length", "<missing>")
    logger.info(
        "folder_upload_request_headers",
        content_type=content_type_header,
        content_length=content_length_header,
        client_host=request.client.host if request.client else "<none>",
    )

    try:
        form = await request.form(
            max_files=_MAX_FOLDER_UPLOAD_FILES,
            max_fields=_MAX_FOLDER_UPLOAD_FILES + 10,
            max_part_size=_MAX_UPLOAD_BYTES,
        )
    except Exception as exc:
        logger.error(
            "folder_upload_form_parse_error",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Form parse error: {exc}",
        ) from exc

    raw_token = form.get("token")
    if not isinstance(raw_token, str) or not raw_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing upload token."
        )
    try:
        uuid.UUID(raw_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload token."
        ) from exc

    try:
        batch_index = int(form.get("batch_index", "0"))  # type: ignore[arg-type]
        total_batches = int(form.get("total_batches", "1"))  # type: ignore[arg-type]
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid batch parameters."
        ) from exc

    if not (0 <= batch_index < total_batches <= _MAX_FOLDER_UPLOAD_FILES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid batch_index or total_batches.",
        )

    raw_files_items = form.getlist("files")
    files: list[UploadFile] = [v for v in raw_files_items if not isinstance(v, str)]

    logger.info(
        "folder_batch_received",
        batch_index=batch_index,
        total_batches=total_batches,
        file_count=len(files),
        raw_items_count=len(raw_files_items),
        raw_item_types=sorted({type(v).__name__ for v in raw_files_items}),
        all_form_keys=sorted(set(form.keys())),
        sample_filenames=[f.filename for f in files[:5]],
    )

    batch_dir = (
        Path(tempfile.gettempdir()) / f"zima-folder-{current_user.id}-{raw_token}"
    )
    batch_dir.mkdir(exist_ok=True)

    try:
        await _write_batch_files_to_dir(files, batch_dir, _MAX_UPLOAD_BYTES)
    except HTTPException:
        shutil.rmtree(batch_dir, ignore_errors=True)
        raise

    # Intermediate batch — acknowledge and wait for the next one
    if batch_index < total_batches - 1:
        return {"status": "received", "batch_index": batch_index}

    # Final batch: hash, validate, and enqueue
    all_disk_files = list(batch_dir.rglob("*"))
    all_disk_files_filtered = [f for f in all_disk_files if f.is_file()]
    suffixes = {f.suffix.lower() for f in all_disk_files_filtered}
    logger.info(
        "folder_final_batch_dir_scan",
        batch_dir=str(batch_dir),
        total_files_on_disk=len(all_disk_files_filtered),
        unique_suffixes=sorted(suffixes),
        sample_paths=[
            str(f.relative_to(batch_dir)) for f in all_disk_files_filtered[:5]
        ],
    )

    file_hash, folder_name, eml_found = await asyncio.to_thread(
        _hash_and_label_directory, batch_dir
    )

    if not eml_found:
        shutil.rmtree(batch_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Folder upload must include at least one .eml file.",
        )

    temp_dir = str(batch_dir)

    try:
        asset = await _require_verified_primary_email(db, current_user.id)
        upload_repo = MboxUploadRepository(db)

        recent_count = await upload_repo.count_recent(user_id=current_user.id, hours=1)
        if recent_count >= 2:
            shutil.rmtree(batch_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Import limit reached (2/hr). Try again later.",
            )

        existing = await upload_repo.get_by_hash(
            user_id=current_user.id, file_hash=file_hash
        )
        if existing is not None:
            if existing.status == MboxUploadStatus.FAILED:
                await upload_repo.delete_by_id(existing.id)
                await db.commit()
            else:
                shutil.rmtree(batch_dir, ignore_errors=True)
                logger.info(
                    "email_accounts.folder_upload_duplicate",
                    user_id=str(current_user.id),
                    upload_id=str(existing.id),
                    folder_name=folder_name,
                )
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "upload_id": str(existing.id),
                        "status": existing.status,
                        "message": "This folder has already been uploaded.",
                    },
                )

        upload = await upload_repo.create(
            user_id=current_user.id,
            filename=folder_name,
            file_hash=file_hash,
        )
        await db.commit()

        _enqueue_mailbox_processing(
            background_tasks,
            user_id=current_user.id,
            upload_id=upload.id,
            asset_id=asset.id,
            recipient_email=str(asset.value),
            mbox_path=temp_dir,
        )
        logger.info(
            "email_accounts.folder_upload_queued",
            user_id=str(current_user.id),
            upload_id=str(upload.id),
            folder_name=folder_name,
            asset_id=str(asset.id),
        )
    except Exception:
        shutil.rmtree(batch_dir, ignore_errors=True)
        raise

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


_TIER_SCORE_RANGES: dict[str, tuple[int, int]] = {
    "confirmed": (70, 100),
    "likely": (40, 69),
    "review": (0, 39),
}


@router.get("/accounts")
async def list_accounts(
    service_name: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    is_reviewed: bool | None = Query(default=None),
    tier: str | None = Query(default=None, pattern="^(confirmed|likely|review)$"),
    include_dismissed: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    account_repo = DiscoveredAccountRepository(db)
    service_registry_repo = ServiceRegistryRepository(db)

    if tier is not None:
        min_score, max_score = _TIER_SCORE_RANGES[tier]
        accounts_plain = await account_repo.list_by_confidence(
            user_id=current_user.id,
            min_score=min_score,
            max_score=max_score,
            include_dismissed=include_dismissed,
            limit=limit,
            offset=offset,
        )
        accounts_with_cat: list[tuple[DiscoveredAccount, str | None]] = [
            (a, None) for a in accounts_plain
        ]
    elif service_name is not None:
        # service_name filter falls back to basic list (no category join needed)
        accounts_plain = await account_repo.list_for_user(
            user_id=current_user.id,
            service_name=service_name,
            source_type=source_type,
            is_reviewed=is_reviewed,
            limit=limit,
            offset=offset,
        )
        accounts_with_cat = [(a, None) for a in accounts_plain]
    else:
        accounts_with_cat = await account_repo.list_for_user_with_category(
            user_id=current_user.id,
            source_type=source_type,
            is_reviewed=is_reviewed,
            limit=limit,
            offset=offset,
        )

    registry_by_domain: dict[str, ServiceRegistry | None] = {}
    account_dicts: list[dict[str, object]] = []
    for account, cat in accounts_with_cat:
        domain = (account.sender_domain or "").strip().lower()
        registry_entry: ServiceRegistry | None = None
        if domain:
            if domain not in registry_by_domain:
                registry_by_domain[domain] = await service_registry_repo.find_by_domain(
                    domain
                )
            registry_entry = registry_by_domain[domain]
        account_dicts.append(
            _account_to_dict(account, cat, registry_entry=registry_entry)
        )

    total = await account_repo.count_for_user(current_user.id)
    return {
        "accounts": account_dicts,
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


_VALID_VERDICTS: frozenset[str] = frozenset(
    {"confirmed", "dismissed", "newsletter", "receipt"}
)


class SetVerdictRequest(BaseModel):
    verdict: str


@router.patch("/accounts/{account_id}/verdict", status_code=200)
async def set_account_verdict(
    account_id: str,
    body: SetVerdictRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    if body.verdict not in _VALID_VERDICTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid verdict '{body.verdict}'. "
                f"Valid values: {', '.join(sorted(_VALID_VERDICTS))}."
            ),
        )

    try:
        aid = uuid.UUID(account_id)
    except ValueError as err:
        raise HTTPException(
            status_code=422,
            detail="Invalid account ID format.",
        ) from err

    account_repo = DiscoveredAccountRepository(db)
    updated = await account_repo.set_verdict(
        account_id=aid, user_id=current_user.id, verdict=body.verdict
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Account not found.")
    await db.commit()
    return {"account_id": account_id, "user_verdict": body.verdict, "is_reviewed": True}


# ---------------------------------------------------------------------------
# Alias creation
# ---------------------------------------------------------------------------

_VALID_ALIAS_PROVIDERS: frozenset[str] = frozenset(
    {IntegrationProvider.SIMPLELOGIN, IntegrationProvider.ADDY_IO}
)


class CreateAliasRequest(BaseModel):
    provider: str
    # SimpleLogin: mailbox ID to receive forwarded mail
    mailbox_id: int | None = None
    # Addy.io: domain to create alias under (e.g. "anonaddy.me")
    domain: str | None = None
    # Optional override for the alias local-part / prefix
    alias_prefix: str | None = None


def _derive_alias_prefix(service_name: str) -> str:
    """
    Derive a safe alias prefix from a service name.

    Examples:
        "GitHub" → "github"
        "Amazon AWS" → "amazon-aws"
        "hello.world.com" → "hello-world-com"
    """
    slug = service_name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:40] or "zima"


@router.post("/accounts/{account_id}/alias", status_code=201)
@limiter.limit("5/minute")
async def create_alias_for_account(
    request: Request,
    account_id: str,
    body: CreateAliasRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """
    Create an email alias for a discovered account.

    The alias is created via the user's connected SimpleLogin or Addy.io
    integration.  The user must have already connected the integration via
    PUT /api/v1/integrations/{provider} and confirmed the alias proposal in
    the UI before calling this endpoint.

    Returns the created alias address.
    """
    if body.provider not in _VALID_ALIAS_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unknown provider '{body.provider}'. "
                f"Valid values: {', '.join(sorted(_VALID_ALIAS_PROVIDERS))}."
            ),
        )

    # Resolve account
    try:
        aid = uuid.UUID(account_id)
    except ValueError as err:
        raise HTTPException(status_code=422, detail="Invalid account ID.") from err

    account_repo = DiscoveredAccountRepository(db)
    account = await account_repo.get_by_id(account_id=aid, user_id=current_user.id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found.")

    # Retrieve + decrypt API key
    integration_repo = UserIntegrationRepository(db)
    record = await integration_repo.get(user_id=current_user.id, provider=body.provider)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"No {body.provider} integration found. "
                f"Connect it first via PUT /api/v1/integrations/{body.provider}."
            ),
        )

    try:
        api_key = decrypt_field(record.api_key_ciphertext)
    except CryptoError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt stored API key.",
        ) from exc

    prefix = body.alias_prefix or _derive_alias_prefix(account.service_name)

    # Create alias via provider
    try:
        if body.provider == IntegrationProvider.SIMPLELOGIN:
            if body.mailbox_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "mailbox_id is required for SimpleLogin. "
                        "Use GET /api/v1/integrations/simplelogin/mailboxes"
                        " to find yours."
                    ),
                )
            sl = SimpleLoginProvider(api_key=api_key)
            result = await sl.create_alias(
                prefix=prefix,
                mailbox_id=body.mailbox_id,
                note=f"Created by Zima for {account.display_name}",
            )
            return {
                "provider": body.provider,
                "alias": result.alias,
                "alias_id": result.alias_id,
                "mailbox": result.mailbox,
                "service_name": account.service_name,
            }

        else:  # addy_io
            if body.domain is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "domain is required for Addy.io (e.g. 'anonaddy.me'). "
                        "Use GET /api/v1/integrations/addy_io/account"
                        " to find available domains."
                    ),
                )
            addy = AddyIoProvider(api_key=api_key)
            addy_result = await addy.create_alias(
                domain=body.domain,
                description=f"Zima: {account.display_name}",
                local_part=prefix,
            )
            return {
                "provider": body.provider,
                "alias": addy_result.alias,
                "alias_id": addy_result.alias_id,
                "local_part": addy_result.local_part,
                "domain": addy_result.domain,
                "service_name": account.service_name,
            }

    except ProviderAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{body.provider} API key is invalid or expired.",
        ) from exc
    except ProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Alias creation failed: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

# Generic / Zima format
_GENERIC_HEADERS = [
    "priority_tier",
    "priority_label",
    "priority_tags",
    "is_breached",
    "recommended_next_step",
    "verification_guidance",
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
_1PASSWORD_HEADERS = ["Title", "Username", "Password", "Website", "Tags", "Notes"]

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


def _build_priority_tags(
    priority: AccountPriority,
    source_type: str,
    is_breached: bool,
    category: str | None,
) -> list[str]:
    tags = [
        "zima",
        "zima-review",
        f"priority:p{priority.tier}",
        f"priority:{priority.label.split(' ', maxsplit=1)[-1].lower()}",
        f"signal:{source_type.replace('_', '-')}",
    ]
    if category:
        tags.append(f"category:{category.lower()}")
    if is_breached:
        tags.append("breached")
    if priority.tier == 1:
        tags.append("fix-first")
    elif priority.tier == 2:
        tags.append("fix-next")
    elif priority.tier == 3:
        tags.append("review-after-import")
    else:
        tags.append("archive-or-delete")
    return tags


def _build_recommended_next_step(priority: AccountPriority, is_breached: bool) -> str:
    if is_breached:
        return (
            "Import this login into your password manager, verify the service links, "
            "then rotate the password and enable MFA."
        )
    if priority.tier <= 2:
        return (
            "Import this login into your password manager, verify the account is still "
            "active, and secure it before lower-priority services."
        )
    return (
        "Import this login into your password manager, decide whether you still need "
        "the account, then archive or delete it if it is dormant."
    )


def _build_verification_guidance(
    login_url: str | None,
    password_reset_url: str | None,
) -> str:
    parts = [
        "Verify the domain before opening any account link.",
        "Check the login or reset URL with VirusTotal first.",
        "Use manual review or an LLM-based second opinion only after the domain check"
        " passes.",
    ]
    if login_url:
        parts.append(f"Login URL: {login_url}")
    if password_reset_url:
        parts.append(f"Reset URL: {password_reset_url}")
    return " | ".join(parts)


def _build_notes(
    priority: AccountPriority,
    priority_tags: list[str],
    source_type: str,
    is_breached: bool,
    category: str | None,
    email_count: int,
    recommended_next_step: str,
    verification_guidance: str,
    password_reset_url: str | None,
) -> str:
    parts = [
        f"Priority: {priority.label}",
        priority.reason,
        f"Tags: {', '.join(priority_tags)}",
        f"Category: {category or 'unknown'}",
        f"Signal: {source_type}",
        f"Emails in inbox: {email_count}",
        f"Next step: {recommended_next_step}",
        verification_guidance,
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
    scored: list[tuple[AccountPriority, DiscoveredAccount, str | None]] = []
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

    for priority, a, category in scored:
        is_breached = a.email_used in breached_emails
        priority_tags = _build_priority_tags(
            priority=priority,
            source_type=a.source_type,
            is_breached=is_breached,
            category=category,
        )
        recommended_next_step = _build_recommended_next_step(priority, is_breached)
        verification_guidance = _build_verification_guidance(
            a.login_url,
            a.password_reset_url,
        )
        notes = _build_notes(
            priority,
            priority_tags,
            a.source_type,
            is_breached,
            category,
            a.email_count,
            recommended_next_step,
            verification_guidance,
            a.password_reset_url,
        )

        if export_format == "1password":
            writer.writerow(
                {
                    "Title": a.display_name,
                    "Username": a.email_used,
                    "Password": "",
                    "Website": a.login_url or "",
                    "Tags": ",".join(priority_tags),
                    "Notes": notes,
                }
            )
        elif export_format == "bitwarden":
            writer.writerow(
                {
                    "folder": (
                        f"Zima / {priority.label} / "
                        f"{'breached' if is_breached else 'review'}"
                    ),
                    "favorite": "1" if priority.tier == 1 else "0",
                    "type": "login",
                    "name": a.display_name,
                    "notes": notes,
                    "fields": "",
                    "reprompt": "0",
                    "login_uri": a.login_url or "",
                    "login_username": a.email_used,
                    "login_password": "",
                    "login_totp": "",
                }
            )
        else:
            writer.writerow(
                {
                    "priority_tier": priority.tier,
                    "priority_label": priority.label,
                    "priority_tags": ",".join(priority_tags),
                    "is_breached": str(is_breached).lower(),
                    "recommended_next_step": recommended_next_step,
                    "verification_guidance": verification_guidance,
                    "display_name": a.display_name,
                    "category": category or "unknown",
                    "email_used": a.email_used,
                    "source_type": a.source_type,
                    "login_url": a.login_url or "",
                    "password_reset_url": a.password_reset_url or "",
                    "email_count": a.email_count,
                    "first_seen": _fmt_dt(a.first_seen_at),
                    "last_seen": _fmt_dt(a.last_seen_at),
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


def _fmt_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _upload_to_dict(u: MboxUpload) -> dict[str, object]:
    return {
        "id": str(u.id),
        "filename": u.filename,
        "status": u.status,
        "accounts_discovered": u.accounts_discovered,
        "signals_created": u.signals_created,
        "error_detail": u.error_detail,
        "processed_at": _fmt_dt(u.processed_at),
        "created_at": _fmt_dt(u.created_at),
    }


def _normalise_account_name_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _root_domain_token(domain: str) -> str:
    labels = [label for label in domain.lower().strip().strip(".").split(".") if label]
    if not labels:
        return ""
    if len(labels) == 1:
        return _normalise_account_name_token(labels[0])

    suffix = ".".join(labels[-2:])
    if len(labels) >= 3 and suffix in _MULTIPART_PUBLIC_SUFFIXES:
        return _normalise_account_name_token(labels[-3])
    return _normalise_account_name_token(labels[-2])


def _should_prefer_registry_identity(
    account: DiscoveredAccount,
    registry_entry: ServiceRegistry,
) -> bool:
    if not account.service_name or not account.display_name:
        return True
    service_token = _normalise_account_name_token(account.service_name)
    display_token = _normalise_account_name_token(account.display_name)
    registry_service_token = _normalise_account_name_token(registry_entry.service_name)
    registry_display_token = _normalise_account_name_token(registry_entry.display_name)
    sender_root_token = _root_domain_token(account.sender_domain)

    # Very short labels (e.g. "ii") are ambiguous; prefer curated identity.
    if service_token and len(service_token) <= 2:
        return True
    if display_token and len(display_token) <= 2:
        return True

    # If name is just the root domain token but registry knows a richer brand,
    # prefer the curated identity.
    if sender_root_token and service_token == sender_root_token:
        if sender_root_token not in {registry_service_token, registry_display_token}:
            return True
    if sender_root_token and display_token == sender_root_token:
        if sender_root_token not in {registry_service_token, registry_display_token}:
            return True

    if account.service_name == account.sender_domain:
        return True
    if account.display_name == account.sender_domain:
        return True
    if service_token in _GENERIC_ACCOUNT_NAME_TOKENS:
        return True
    if display_token in _GENERIC_ACCOUNT_NAME_TOKENS:
        return True
    if not account.login_url and not account.password_reset_url:
        return True
    return False


def _account_to_dict(
    a: DiscoveredAccount,
    category: str | None = None,
    registry_entry: ServiceRegistry | None = None,
) -> dict[str, object]:
    effective_category = category
    service_name = a.service_name
    display_name = a.display_name
    login_url = a.login_url
    password_reset_url = a.password_reset_url

    if registry_entry is not None:
        effective_category = effective_category or registry_entry.category
        if not login_url and registry_entry.login_url:
            login_url = registry_entry.login_url
        if not password_reset_url and registry_entry.password_reset_url:
            password_reset_url = registry_entry.password_reset_url
        if _should_prefer_registry_identity(a, registry_entry):
            service_name = registry_entry.service_name
            display_name = registry_entry.display_name

    p = priority_score(effective_category, a.source_type, is_breached=False)
    return {
        "id": str(a.id),
        "service_name": service_name,
        "display_name": display_name,
        "email_used": a.email_used,
        "source_type": a.source_type,
        "sender_domain": a.sender_domain,
        "login_url": login_url,
        "password_reset_url": password_reset_url,
        "email_count": a.email_count,
        "first_seen_at": _fmt_dt(a.first_seen_at),
        "last_seen_at": _fmt_dt(a.last_seen_at),
        "is_reviewed": a.is_reviewed,
        "created_at": _fmt_dt(a.created_at),
        "category": effective_category,
        "priority_tier": p.tier,
        "priority_label": p.label,
        "confidence_score": a.confidence_score,
        "user_verdict": a.user_verdict,
    }
