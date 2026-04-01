# backend/app/db/repositories/discovered_accounts.py
import uuid
from datetime import datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.email_accounts import DiscoveredAccount


class DiscoveredAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        user_id: uuid.UUID,
        upload_id: uuid.UUID,
        service_name: str,
        display_name: str,
        email_used: str,
        source_type: str,
        sender_domain: str,
        login_url: str | None,
        password_reset_url: str | None,
        first_seen_at: datetime | None,
        last_seen_at: datetime | None,
        email_count: int,
        increment_email_count: bool = True,
    ) -> DiscoveredAccount:
        """
        Insert or update by (user_id, service_name, email_used).
        On conflict: increment email_count, extend date range, and fill in
        URLs if now known.
        """
        stmt = (
            pg_insert(DiscoveredAccount)
            .values(
                user_id=user_id,
                upload_id=upload_id,
                service_name=service_name,
                display_name=display_name,
                email_used=email_used,
                source_type=source_type,
                sender_domain=sender_domain,
                login_url=login_url,
                password_reset_url=password_reset_url,
                first_seen_at=first_seen_at,
                last_seen_at=last_seen_at,
                email_count=email_count,
            )
            .on_conflict_do_update(
                constraint="uq_discovered_account",
                set_={
                    "email_count": (
                        DiscoveredAccount.email_count + email_count
                        if increment_email_count
                        else func.greatest(DiscoveredAccount.email_count, email_count)
                    ),
                    # COALESCE guards against the existing row having a NULL date:
                    # GREATEST/LEAST(NULL, value) returns NULL in PostgreSQL.
                    "last_seen_at": func.greatest(
                        func.coalesce(DiscoveredAccount.last_seen_at, last_seen_at),
                        last_seen_at,
                    ),
                    "first_seen_at": func.least(
                        func.coalesce(DiscoveredAccount.first_seen_at, first_seen_at),
                        first_seen_at,
                    ),
                    "login_url": func.coalesce(login_url, DiscoveredAccount.login_url),
                    "password_reset_url": func.coalesce(
                        password_reset_url, DiscoveredAccount.password_reset_url
                    ),
                    "updated_at": func.now(),
                },
            )
            .returning(DiscoveredAccount)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_by_id(
        self, account_id: uuid.UUID, user_id: uuid.UUID
    ) -> DiscoveredAccount | None:
        result = await self.session.execute(
            select(DiscoveredAccount).where(
                DiscoveredAccount.id == account_id,
                DiscoveredAccount.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        service_name: str | None = None,
        source_type: str | None = None,
        is_reviewed: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DiscoveredAccount]:
        q = select(DiscoveredAccount).where(DiscoveredAccount.user_id == user_id)
        if service_name is not None:
            q = q.where(DiscoveredAccount.service_name == service_name)
        if source_type is not None:
            q = q.where(DiscoveredAccount.source_type == source_type)
        if is_reviewed is not None:
            q = q.where(DiscoveredAccount.is_reviewed == is_reviewed)
        q = q.order_by(DiscoveredAccount.service_name).limit(limit).offset(offset)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(DiscoveredAccount)
            .where(DiscoveredAccount.user_id == user_id)
        )
        return result.scalar_one()

    async def mark_reviewed(self, account_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            update(DiscoveredAccount)
            .where(
                DiscoveredAccount.id == account_id,
                DiscoveredAccount.user_id == user_id,
            )
            .values(is_reviewed=True)
            .returning(DiscoveredAccount.id)
        )
        return result.scalar_one_or_none() is not None

    async def get_all_for_user_export(
        self, user_id: uuid.UUID
    ) -> list[DiscoveredAccount]:
        """Full list for CSV export — no pagination."""
        result = await self.session.execute(
            select(DiscoveredAccount)
            .where(DiscoveredAccount.user_id == user_id)
            .order_by(DiscoveredAccount.service_name)
        )
        return list(result.scalars().all())

    async def get_all_for_user_export_with_category(
        self, user_id: uuid.UUID
    ) -> list[tuple[DiscoveredAccount, str | None]]:
        """
        Full list for priority-aware export.
        LEFT JOINs with service_registry to fetch the service category so that
        financial/payment accounts can be escalated to P1/P2 in priority scoring.
        """
        from backend.app.db.models.email_accounts import ServiceRegistry

        result = await self.session.execute(
            select(DiscoveredAccount, ServiceRegistry.category)
            .outerjoin(
                ServiceRegistry,
                DiscoveredAccount.service_name == ServiceRegistry.service_name,
            )
            .where(DiscoveredAccount.user_id == user_id)
            .order_by(DiscoveredAccount.service_name)
        )
        return [(row[0], row[1]) for row in result.all()]

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        """Hard-deletes all discovered accounts for a user. Used by GDPR erasure."""
        await self.session.execute(
            delete(DiscoveredAccount).where(DiscoveredAccount.user_id == user_id)
        )
