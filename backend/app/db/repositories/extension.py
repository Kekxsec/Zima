# backend/app/db/repositories/extension.py
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.extension import (
    ExtensionSession,
    ExtensionSnapshot,
    GuidanceEvent,
)


class ExtensionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_session(
        self,
        user_id: uuid.UUID,
        browser: str,
        version: str,
        jti: str,
    ) -> ExtensionSession:
        """
        INSERT a new ExtensionSession, or UPDATE the existing one for this user.
        One session per user (enforced by unique constraint on user_id).
        """
        now = datetime.now(UTC)
        stmt = (
            pg_insert(ExtensionSession)
            .values(
                id=uuid.uuid4(),
                user_id=user_id,
                browser=browser,
                extension_version=version,
                extension_jti=jti,
                last_seen_at=now,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_extension_sessions_user_id",
                set_={
                    "browser": browser,
                    "extension_version": version,
                    "extension_jti": jti,
                    "last_seen_at": now,
                    "updated_at": now,
                },
            )
            .returning(ExtensionSession)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_session_by_user(self, user_id: uuid.UUID) -> ExtensionSession | None:
        result = await self.session.execute(
            select(ExtensionSession).where(ExtensionSession.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_last_seen(self, session_id: uuid.UUID) -> None:
        result = await self.session.execute(
            select(ExtensionSession).where(ExtensionSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session is not None:
            session.last_seen_at = datetime.now(UTC)

    async def rotate_session_jti(self, session_id: uuid.UUID, jti: str) -> None:
        result = await self.session.execute(
            select(ExtensionSession).where(ExtensionSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session is not None:
            now = datetime.now(UTC)
            session.extension_jti = jti
            session.last_seen_at = now
            session.updated_at = now

    async def insert_snapshot(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        raw: dict[str, object],
    ) -> ExtensionSnapshot:
        snapshot = ExtensionSnapshot(
            id=uuid.uuid4(),
            user_id=user_id,
            extension_session_id=session_id,
            raw_snapshot=raw,
        )
        self.session.add(snapshot)
        return snapshot

    async def get_latest_snapshot(self, user_id: uuid.UUID) -> ExtensionSnapshot | None:
        result = await self.session.execute(
            select(ExtensionSnapshot)
            .where(ExtensionSnapshot.user_id == user_id)
            .order_by(ExtensionSnapshot.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def insert_guidance_event(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        provider: str,
        step: str,
    ) -> GuidanceEvent:
        event = GuidanceEvent(
            id=uuid.uuid4(),
            user_id=user_id,
            extension_session_id=session_id,
            provider=provider,
            step=step,
        )
        self.session.add(event)
        return event

    async def get_guide_completion(self, user_id: uuid.UUID, provider: str) -> bool:
        """Returns True if the user has recorded a 'mbox_downloaded' event for this provider."""
        result = await self.session.execute(
            select(GuidanceEvent).where(
                GuidanceEvent.user_id == user_id,
                GuidanceEvent.provider == provider,
                GuidanceEvent.step == "mbox_downloaded",
            )
        )
        return result.scalar_one_or_none() is not None

    async def list_recent_guidance_events(
        self, user_id: uuid.UUID, limit: int = 50
    ) -> list[GuidanceEvent]:
        result = await self.session.execute(
            select(GuidanceEvent)
            .where(GuidanceEvent.user_id == user_id)
            .order_by(GuidanceEvent.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
