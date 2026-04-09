# backend/app/db/repositories/companion.py
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.companion import BrowserSnapshot, CompanionSession


class CompanionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_session(
        self,
        user_id: uuid.UUID,
        machine_id_encrypted: str,
        platform: str,
        version: str,
        jti: str,
    ) -> CompanionSession:
        """
        INSERT a new CompanionSession, or UPDATE the existing one for this user.
        One session per user (enforced by unique constraint on user_id).
        Returns the current session row after upsert.
        """
        now = datetime.now(UTC)
        stmt = (
            pg_insert(CompanionSession)
            .values(
                id=uuid.uuid4(),
                user_id=user_id,
                machine_id=machine_id_encrypted,
                platform=platform,
                companion_version=version,
                companion_jti=jti,
                last_seen_at=now,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_companion_sessions_user_id",
                set_={
                    "machine_id": machine_id_encrypted,
                    "platform": platform,
                    "companion_version": version,
                    "companion_jti": jti,
                    "last_seen_at": now,
                    "updated_at": now,
                },
            )
            .returning(CompanionSession)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one()
        return row

    async def get_session_by_user(self, user_id: uuid.UUID) -> CompanionSession | None:
        result = await self.session.execute(
            select(CompanionSession).where(CompanionSession.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_last_seen(self, session_id: uuid.UUID) -> None:
        """Update last_seen_at on an existing session. Caller must commit."""
        result = await self.session.execute(
            select(CompanionSession).where(CompanionSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session is not None:
            session.last_seen_at = datetime.now(UTC)

    async def insert_snapshot(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        raw: dict,
    ) -> BrowserSnapshot:
        """Append a new snapshot. Caller must commit."""
        snapshot = BrowserSnapshot(
            id=uuid.uuid4(),
            user_id=user_id,
            companion_session_id=session_id,
            raw_snapshot=raw,
        )
        self.session.add(snapshot)
        return snapshot

    async def get_latest_snapshot(self, user_id: uuid.UUID) -> BrowserSnapshot | None:
        result = await self.session.execute(
            select(BrowserSnapshot)
            .where(BrowserSnapshot.user_id == user_id)
            .order_by(BrowserSnapshot.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
