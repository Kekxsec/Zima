# backend/app/db/repositories/assets.py
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.assets.models import Asset


class AssetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_value(
        self,
        user_id: uuid.UUID,
        entity_type: str,
        value: str,
    ) -> Asset | None:
        result = await self.session.execute(
            select(Asset).where(
                Asset.user_id == user_id,
                Asset.entity_type == entity_type,
                Asset.value == value,
            )
        )
        return result.scalar_one_or_none()

    async def get_verified_for_user(
        self,
        user_id: uuid.UUID,
        entity_type: str,
    ) -> list[Asset]:
        result = await self.session.execute(
            select(Asset).where(
                Asset.user_id == user_id,
                Asset.entity_type == entity_type,
                Asset.is_verified.is_(True),
            )
        )
        return list(result.scalars().all())

    async def get_all_for_user(self, user_id: uuid.UUID) -> list[Asset]:
        result = await self.session.execute(
            select(Asset).where(Asset.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_primary_email(self, user_id: uuid.UUID) -> Asset | None:
        result = await self.session.execute(
            select(Asset).where(
                Asset.user_id == user_id,
                Asset.entity_type == "email",
                Asset.is_primary.is_(True),
            )
        )
        return result.scalar_one_or_none()
