# backend/app/db/repositories/service_registry.py
from sqlalchemy import String as SAString
from sqlalchemy import cast, select
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.email_accounts import ServiceRegistry


class ServiceRegistryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_name(self, service_name: str) -> ServiceRegistry | None:
        result = await self.session.execute(
            select(ServiceRegistry).where(
                ServiceRegistry.service_name == service_name,
                ServiceRegistry.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_all_active(self) -> list[ServiceRegistry]:
        result = await self.session.execute(
            select(ServiceRegistry).where(ServiceRegistry.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def find_by_domain(self, domain: str) -> ServiceRegistry | None:
        """
        Finds a registry entry where `domain` appears in common_domains.
        Uses PostgreSQL ARRAY contains operator.
        """
        result = await self.session.execute(
            select(ServiceRegistry).where(
                ServiceRegistry.common_domains.contains(
                    cast([domain], ARRAY(SAString))
                ),
                ServiceRegistry.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()
