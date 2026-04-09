# backend/app/db/repositories/scans.py
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.enums import ScanStatus, Tier
from backend.app.jobs.models import Scan


class ScanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: uuid.UUID,
        tier: Tier,
        target_emails: list[str] | None = None,
    ) -> Scan:
        scan = Scan(
            user_id=user_id,
            tier=tier.value,
            status=ScanStatus.PENDING,
            target_emails=target_emails or [],
        )
        self.session.add(scan)
        await self.session.flush()
        return scan

    async def get_by_id_for_user(
        self, scan_id: uuid.UUID, user_id: uuid.UUID
    ) -> Scan | None:
        result = await self.session.execute(
            select(Scan).where(
                Scan.id == scan_id,
                Scan.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        scan_id: uuid.UUID,
        status: ScanStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        signals_created: int | None = None,
        findings_created: int | None = None,
        domains_run: list[str] | None = None,
        error_detail: str | None = None,
    ) -> None:
        values: dict[str, object] = {"status": status.value}
        if started_at is not None:
            values["started_at"] = started_at
        if completed_at is not None:
            values["completed_at"] = completed_at
        if signals_created is not None:
            values["signals_created"] = signals_created
        if findings_created is not None:
            values["findings_created"] = findings_created
        if domains_run is not None:
            values["domains_run"] = domains_run
        if error_detail is not None:
            values["error_detail"] = error_detail
        await self.session.execute(
            update(Scan).where(Scan.id == scan_id).values(**values)
        )

    async def mark_stale_if_running(
        self,
        scan_id: uuid.UUID,
        stale_after_minutes: int = 30,
    ) -> bool:
        """
        Conditionally marks a single scan FAILED only if it is still RUNNING
        and its started_at exceeds the stale threshold.

        The WHERE clause is evaluated atomically by PostgreSQL, so this is
        race-free: a concurrent COMPLETED update will cause this to match zero
        rows and return False rather than overwriting the final status.
        """
        stale_threshold = datetime.now(UTC) - timedelta(minutes=stale_after_minutes)
        result = await self.session.execute(
            update(Scan)
            .where(
                and_(
                    Scan.id == scan_id,
                    Scan.status == ScanStatus.RUNNING.value,
                    Scan.started_at < stale_threshold,
                )
            )
            .values(
                status=ScanStatus.FAILED.value,
                completed_at=datetime.now(UTC),
                error_detail="Scan timed out — marked failed by stale scan detector",
            )
        )
        return result.rowcount > 0

    async def mark_stale_scans_failed(self, stale_after_minutes: int = 30) -> int:
        """
        Marks any scan in RUNNING status for longer than stale_after_minutes as FAILED.
        Called at startup and when the scan status endpoint detects a stale scan.
        Returns count of scans updated.
        """
        stale_threshold = datetime.now(UTC) - timedelta(minutes=stale_after_minutes)
        result = await self.session.execute(
            update(Scan)
            .where(
                and_(
                    Scan.status == ScanStatus.RUNNING.value,
                    Scan.started_at < stale_threshold,
                )
            )
            .values(
                status=ScanStatus.FAILED.value,
                completed_at=datetime.now(UTC),
                error_detail="Scan timed out — marked failed by stale scan detector",
            )
        )
        count: int = result.rowcount
        return count

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        """Hard-deletes all scans for a user. Used by GDPR erasure."""
        await self.session.execute(delete(Scan).where(Scan.user_id == user_id))

    async def get_history_for_user(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Scan]:
        result = await self.session.execute(
            select(Scan)
            .where(Scan.user_id == user_id)
            .order_by(Scan.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
