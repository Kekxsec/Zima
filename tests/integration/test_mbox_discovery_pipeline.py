# tests/integration/test_mbox_discovery_pipeline.py
"""
Integration test: process_mbox_upload — full pipeline from bytes → DB.

process_mbox_upload creates its own AsyncSession (Rule 3), so test data must be
committed to the DB before calling it. The test DB is shared across calls via
AsyncSessionLocal which uses the same settings.database_url as the test engine.
"""

import inspect
import json
import uuid
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.email_accounts import MboxUploadStatus
from backend.app.db.repositories.discovered_accounts import DiscoveredAccountRepository
from backend.app.db.repositories.mbox_uploads import MboxUploadRepository
from backend.app.db.repositories.signals import SignalRepository
from backend.app.jobs.mbox_processor import process_mbox_upload
from tests.factories import AssetFactory, UserFactory


def _make_mbox(*messages: tuple[str, str, str]) -> bytes:
    """Build minimal mbox bytes from (from_addr, subject, date_str) tuples."""
    lines: list[bytes] = []
    for from_addr, subject, date_str in messages:
        lines.append(f"From {from_addr} {date_str}\n".encode())
        lines.append(f"From: {from_addr}\n".encode())
        lines.append(f"Subject: {subject}\n".encode())
        lines.append(f"Date: {date_str}\n".encode())
        lines.append(f"Message-ID: <{uuid.uuid4()}@test>\n".encode())
        lines.append(b"\n")
        lines.append(b"Body.\n\n")
    return b"".join(lines)


def _write_upload(tmp_path: Path, filename: str, data: bytes) -> str:
    upload_path = tmp_path / filename
    upload_path.write_bytes(data)
    return str(upload_path)


def _write_proton_export_dir(
    root: Path,
    *messages: tuple[str, str, str],
) -> str:
    export_dir = root / "Export" / "Inbox"
    export_dir.mkdir(parents=True, exist_ok=True)

    for index, (from_addr, subject, date_str) in enumerate(messages):
        eml_path = export_dir / f"message-{index}.eml"
        eml_path.write_bytes(
            (
                f"From: {from_addr}\n"
                "To: inbox@example.com\n"
                f"Subject: {subject}\n"
                f"Date: {date_str}\n"
                f"Message-ID: <dir-{index}@example.com>\n"
                "\n"
                "Body line.\n"
            ).encode()
        )
        eml_path.with_suffix(".json").write_text(
            json.dumps({"metadata": {"index": index}})
        )

    return str(root / "Export")


@pytest.mark.asyncio
async def test_process_mbox_upload_does_not_accept_session_param() -> None:
    """Rule 3: background task must create its own session, not accept one."""
    sig = inspect.signature(process_mbox_upload)
    assert "session" not in sig.parameters


@pytest.mark.asyncio
async def test_process_mbox_upload_creates_accounts_and_marks_completed(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    """Full pipeline: mbox bytes → parse → classify → upsert → completed."""
    # --- arrange ---
    user = UserFactory.build()
    db_session.add(user)
    asset = AssetFactory.build(
        user_id=user.id,
        entity_type="email",
        value="inbox@example.com",
        is_verified=True,
        is_primary=True,
    )
    db_session.add(asset)
    await db_session.flush()

    upload_repo = MboxUploadRepository(db_session)
    upload = await upload_repo.create(
        user_id=user.id,
        filename="test.mbox",
        file_hash="deadbeef01",
    )
    await db_session.commit()  # process_mbox_upload uses its own session — must commit
    user_id = user.id
    asset_id = asset.id
    upload_id = upload.id

    # One account-confirmation email from a non-skip domain
    mbox_data = _make_mbox(
        ("noreply@github.com", "Welcome to GitHub!", "Mon, 01 Jan 2024 10:00:00 +0000"),
    )
    mbox_path = _write_upload(tmp_path, "test.mbox", mbox_data)

    # --- act ---
    await process_mbox_upload(
        user_id=user_id,
        upload_id=upload_id,
        asset_id=asset_id,
        recipient_email="inbox@example.com",
        mbox_path=mbox_path,
    )

    # --- assert: upload marked completed ---
    # Use a fresh read from DB (process_mbox_upload committed in its own session)
    db_session.expire_all()
    fresh_upload = await upload_repo.get_by_id(upload_id=upload_id, user_id=user_id)
    assert fresh_upload is not None
    assert fresh_upload.status == MboxUploadStatus.COMPLETED
    assert fresh_upload.accounts_discovered >= 1
    assert fresh_upload.signals_created >= 1


@pytest.mark.asyncio
async def test_process_mbox_upload_creates_discovered_account_row(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    """Verified: a DiscoveredAccount row is inserted for each unique service."""
    user = UserFactory.build()
    db_session.add(user)
    asset = AssetFactory.build(
        user_id=user.id,
        entity_type="email",
        value="inbox2@example.com",
        is_verified=True,
        is_primary=True,
    )
    db_session.add(asset)
    await db_session.flush()

    upload_repo = MboxUploadRepository(db_session)
    upload = await upload_repo.create(
        user_id=user.id,
        filename="test2.mbox",
        file_hash="deadbeef02",
    )
    await db_session.commit()
    user_id = user.id
    asset_id = asset.id
    upload_id = upload.id

    mbox_data = _make_mbox(
        (
            "noreply@dropbox.com",
            "Confirm your Dropbox account",
            "Mon, 01 Jan 2024 10:00:00 +0000",
        ),
        (
            "security@netflix.com",
            "Welcome to Netflix",
            "Tue, 02 Jan 2024 10:00:00 +0000",
        ),
    )
    mbox_path = _write_upload(tmp_path, "test2.mbox", mbox_data)

    await process_mbox_upload(
        user_id=user_id,
        upload_id=upload_id,
        asset_id=asset_id,
        recipient_email="inbox2@example.com",
        mbox_path=mbox_path,
    )

    db_session.expire_all()
    account_repo = DiscoveredAccountRepository(db_session)
    accounts = await account_repo.list_for_user(user_id=user_id, limit=20, offset=0)
    assert len(accounts) >= 2
    domains = {a.sender_domain for a in accounts}
    assert "dropbox.com" in domains
    assert "netflix.com" in domains


@pytest.mark.asyncio
async def test_process_mbox_upload_creates_signals(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    """A Signal row is emitted for each discovered account."""
    user = UserFactory.build()
    db_session.add(user)
    asset = AssetFactory.build(
        user_id=user.id,
        entity_type="email",
        value="inbox3@example.com",
        is_verified=True,
        is_primary=True,
    )
    db_session.add(asset)
    await db_session.flush()

    upload_repo = MboxUploadRepository(db_session)
    upload = await upload_repo.create(
        user_id=user.id,
        filename="test3.mbox",
        file_hash="deadbeef03",
    )
    await db_session.commit()
    user_id = user.id
    asset_id = asset.id
    upload_id = upload.id

    mbox_data = _make_mbox(
        (
            "confirm@stripe.com",
            "Receipt for your Stripe subscription",
            "Mon, 01 Jan 2024 10:00:00 +0000",
        ),
    )
    mbox_path = _write_upload(tmp_path, "test3.mbox", mbox_data)

    await process_mbox_upload(
        user_id=user_id,
        upload_id=upload_id,
        asset_id=asset_id,
        recipient_email="inbox3@example.com",
        mbox_path=mbox_path,
    )

    db_session.expire_all()
    signal_repo = SignalRepository(db_session)
    count = await signal_repo.count_open_for_user(user_id)
    assert count >= 1


@pytest.mark.asyncio
async def test_process_mbox_upload_marks_failed_on_bad_upload_id(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    """
    If upload_id doesn't exist in the DB, process_mbox_upload will fail
    (set_processing raises) and re-raise. The failure handler uses its own
    session; this test verifies the exception propagates to the caller.
    """
    bad_upload_id = uuid.uuid4()
    bad_user_id = uuid.uuid4()
    bad_asset_id = uuid.uuid4()
    bad_path = _write_upload(tmp_path, "bad.mbox", b"From nobody\nSubject: hi\n\n")

    with pytest.raises(Exception):  # noqa: B017
        await process_mbox_upload(
            user_id=bad_user_id,
            upload_id=bad_upload_id,
            asset_id=bad_asset_id,
            recipient_email="nobody@example.com",
            mbox_path=bad_path,
        )


@pytest.mark.asyncio
async def test_process_mbox_upload_empty_mbox_completes_with_zero_counts(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    """Empty mbox → zero accounts discovered, upload still marked COMPLETED."""
    user = UserFactory.build()
    db_session.add(user)
    asset = AssetFactory.build(
        user_id=user.id,
        entity_type="email",
        value="inbox4@example.com",
        is_verified=True,
        is_primary=True,
    )
    db_session.add(asset)
    await db_session.flush()

    upload_repo = MboxUploadRepository(db_session)
    upload = await upload_repo.create(
        user_id=user.id,
        filename="empty.mbox",
        file_hash="deadbeef04",
    )
    await db_session.commit()
    user_id = user.id
    asset_id = asset.id
    upload_id = upload.id

    empty_path = _write_upload(tmp_path, "empty.mbox", b"")

    await process_mbox_upload(
        user_id=user_id,
        upload_id=upload_id,
        asset_id=asset_id,
        recipient_email="inbox4@example.com",
        mbox_path=empty_path,
    )

    db_session.expire_all()
    fresh_upload = await upload_repo.get_by_id(upload_id=upload_id, user_id=user_id)
    assert fresh_upload is not None
    assert fresh_upload.status == MboxUploadStatus.COMPLETED
    assert fresh_upload.accounts_discovered == 0
    assert fresh_upload.signals_created == 0


@pytest.mark.asyncio
async def test_process_mbox_upload_supports_proton_export_directory(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    user = UserFactory.build()
    db_session.add(user)
    asset = AssetFactory.build(
        user_id=user.id,
        entity_type="email",
        value="inbox5@example.com",
        is_verified=True,
        is_primary=True,
    )
    db_session.add(asset)
    await db_session.flush()

    upload_repo = MboxUploadRepository(db_session)
    upload = await upload_repo.create(
        user_id=user.id,
        filename="Export",
        file_hash="deadbeef05",
    )
    await db_session.commit()
    user_id = user.id
    asset_id = asset.id
    upload_id = upload.id

    export_path = _write_proton_export_dir(
        tmp_path,
        ("noreply@github.com", "Welcome to GitHub!", "Mon, 01 Jan 2024 10:00:00 +0000"),
        (
            "security@dropbox.com",
            "Confirm your Dropbox account",
            "Tue, 02 Jan 2024 10:00:00 +0000",
        ),
    )

    await process_mbox_upload(
        user_id=user_id,
        upload_id=upload_id,
        asset_id=asset_id,
        recipient_email="inbox5@example.com",
        mbox_path=export_path,
    )

    db_session.expire_all()
    account_repo = DiscoveredAccountRepository(db_session)
    accounts = await account_repo.list_for_user(user_id=user_id, limit=20, offset=0)
    domains = {a.sender_domain for a in accounts}
    assert "github.com" in domains
    assert "dropbox.com" in domains
