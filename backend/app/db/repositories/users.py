# backend/app/db/repositories/users.py
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: str | uuid.UUID) -> User | None:
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        from backend.app.assets.models import Asset

        result = await self.session.execute(
            select(User)
            .join(Asset, Asset.user_id == User.id)
            .where(
                Asset.entity_type == "email",
                Asset.value == email,
                Asset.is_primary.is_(True),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_active_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.session.execute(
            select(User).where(
                User.id == user_id,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
