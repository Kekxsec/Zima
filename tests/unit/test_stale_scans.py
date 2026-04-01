# tests/unit/test_stale_scans.py
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.enums import ScanStatus
from backend.app.db.repositories.scans import ScanRepository
from backend.app.jobs.models import Scan
from tests.factories import UserFactory


@pytest.mark.asyncio
async def test_mark_stale_scans_updates_old_running_scans(
    db_session: AsyncSession,
) -> None:
    user = UserFactory.build()
    db_session.add(user)
    await db_session.flush()

    stale_scan = Scan(
        user_id=user.id,
        tier="core",
        status=ScanStatus.RUNNING.value,
        started_at=datetime.now(UTC) - timedelta(minutes=15),
    )
    db_session.add(stale_scan)
    await db_session.commit()

    scan_repo = ScanRepository(db_session)
    count = await scan_repo.mark_stale_scans_failed(stale_after_minutes=10)
    await db_session.commit()

    assert count == 1
    await db_session.refresh(stale_scan)
    assert stale_scan.status == ScanStatus.FAILED.value
    assert stale_scan.completed_at is not None


@pytest.mark.asyncio
async def test_mark_stale_scans_ignores_recent_running_scans(
    db_session: AsyncSession,
) -> None:
    user = UserFactory.build()
    db_session.add(user)
    await db_session.flush()

    recent_scan = Scan(
        user_id=user.id,
        tier="core",
        status=ScanStatus.RUNNING.value,
        started_at=datetime.now(UTC) - timedelta(minutes=2),
    )
    db_session.add(recent_scan)
    await db_session.commit()

    scan_repo = ScanRepository(db_session)
    count = await scan_repo.mark_stale_scans_failed(stale_after_minutes=10)
    await db_session.commit()

    assert count == 0
    await db_session.refresh(recent_scan)
    assert recent_scan.status == ScanStatus.RUNNING.value


@pytest.mark.asyncio
async def test_mark_stale_scans_ignores_completed_scans(
    db_session: AsyncSession,
) -> None:
    user = UserFactory.build()
    db_session.add(user)
    await db_session.flush()

    completed_scan = Scan(
        user_id=user.id,
        tier="core",
        status=ScanStatus.COMPLETED.value,
        started_at=datetime.now(UTC) - timedelta(hours=2),
        completed_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(completed_scan)
    await db_session.commit()

    scan_repo = ScanRepository(db_session)
    count = await scan_repo.mark_stale_scans_failed(stale_after_minutes=10)

    assert count == 0
