# backend/app/db/repositories/user_integrations.py
import uuid

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.integrations import UserIntegration


class UserIntegrationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        user_id: uuid.UUID,
        provider: str,
        api_key_ciphertext: str,
    ) -> UserIntegration:
        stmt = (
            insert(UserIntegration)
            .values(
                user_id=user_id,
                provider=provider,
                api_key_ciphertext=api_key_ciphertext,
            )
            .on_conflict_do_update(
                constraint="uq_user_integration",
                set_={"api_key_ciphertext": api_key_ciphertext},
            )
            .returning(UserIntegration)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get(self, user_id: uuid.UUID, provider: str) -> UserIntegration | None:
        result = await self.session.execute(
            select(UserIntegration).where(
                UserIntegration.user_id == user_id,
                UserIntegration.provider == provider,
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, user_id: uuid.UUID, provider: str) -> None:
        await self.session.execute(
            delete(UserIntegration).where(
                UserIntegration.user_id == user_id,
                UserIntegration.provider == provider,
            )
        )

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(UserIntegration).where(UserIntegration.user_id == user_id)
        )
