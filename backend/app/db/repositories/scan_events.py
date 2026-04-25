# backend/app/db/repositories/scan_events.py
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.jobs.models import Scan, ScanEvent


class ScanEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _assert_scan_owned_by_user(
        self, scan_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Reject writes whose user_id does not match the scan's owner."""
        result = await self.session.execute(
            select(Scan.user_id).where(Scan.id == scan_id)
        )
        owner_id = result.scalar_one_or_none()
        if owner_id is None:
            raise ValueError(f"Scan {scan_id} not found.")
        if owner_id != user_id:
            raise PermissionError(
                f"Scan {scan_id} not owned by user {user_id}; refusing event write."
            )

    async def record(
        self,
        scan_id: uuid.UUID,
        user_id: uuid.UUID,
        event_type: str,
        data: dict[str, Any] | None = None,
        ts: datetime | None = None,
    ) -> ScanEvent:
        """Append a single event to the scan history."""
        await self._assert_scan_owned_by_user(scan_id, user_id)
        event = ScanEvent(
            scan_id=scan_id,
            user_id=user_id,
            event_type=event_type,
            ts=ts or datetime.now(UTC),
            data=data or {},
        )
        self.session.add(event)
        return event

    async def bulk_record(
        self,
        scan_id: uuid.UUID,
        user_id: uuid.UUID,
        events: list[dict[str, Any]],
    ) -> None:
        """
        Flush a batch of events drained from ScanExecutionContext.

        Each dict must have keys: event_type, ts (ISO string), plus any
        extra fields which are stored in data.
        """
        if not events:
            return
        await self._assert_scan_owned_by_user(scan_id, user_id)
        for raw in events:
            event_type = raw["event_type"]
            ts_raw = raw.get("ts")
            ts = (
                datetime.fromisoformat(ts_raw)
                if isinstance(ts_raw, str)
                else datetime.now(UTC)
            )
            data = {k: v for k, v in raw.items() if k not in ("event_type", "ts")}
            event = ScanEvent(
                scan_id=scan_id,
                user_id=user_id,
                event_type=event_type,
                ts=ts,
                data=data,
            )
            self.session.add(event)

    async def get_for_scan(
        self,
        scan_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[ScanEvent]:
        """Return all events for a scan, ordered oldest-first."""
        result = await self.session.execute(
            select(ScanEvent)
            .where(
                ScanEvent.scan_id == scan_id,
                ScanEvent.user_id == user_id,
            )
            .order_by(ScanEvent.ts.asc())
        )
        return list(result.scalars().all())

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        """Hard-deletes all scan events for a user. Used by GDPR erasure."""
        await self.session.execute(
            delete(ScanEvent).where(ScanEvent.user_id == user_id)
        )
