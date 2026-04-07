# backend/app/db/repositories/vault_imports.py
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.email_accounts import VaultImport, VaultImportStatus


class VaultImportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: uuid.UUID,
        filename: str,
        file_hash: str,
        import_type: str,
    ) -> VaultImport:
        record = VaultImport(
            user_id=user_id,
            filename=filename,
            file_hash=file_hash,
            import_type=import_type,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_by_id(
        self, import_id: uuid.UUID, user_id: uuid.UUID
    ) -> VaultImport | None:
        result = await self.session.execute(
            select(VaultImport).where(
                VaultImport.id == import_id,
                VaultImport.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_hash(
        self, user_id: uuid.UUID, file_hash: str
    ) -> VaultImport | None:
        result = await self.session.execute(
            select(VaultImport).where(
                VaultImport.user_id == user_id,
                VaultImport.file_hash == file_hash,
            )
        )
        return result.scalar_one_or_none()

    async def set_processing(self, import_id: uuid.UUID) -> None:
        await self.session.execute(
            update(VaultImport)
            .where(VaultImport.id == import_id)
            .values(status=VaultImportStatus.PROCESSING)
        )

    async def set_completed(
        self,
        import_id: uuid.UUID,
        accounts_discovered: int,
    ) -> None:
        await self.session.execute(
            update(VaultImport)
            .where(VaultImport.id == import_id)
            .values(
                status=VaultImportStatus.COMPLETED,
                accounts_discovered=accounts_discovered,
                processed_at=datetime.now(UTC),
            )
        )

    async def set_failed(self, import_id: uuid.UUID, error_detail: str) -> None:
        await self.session.execute(
            update(VaultImport)
            .where(VaultImport.id == import_id)
            .values(
                status=VaultImportStatus.FAILED,
                error_detail=error_detail[:1024],
                processed_at=datetime.now(UTC),
            )
        )

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[VaultImport]:
        result = await self.session.execute(
            select(VaultImport)
            .where(VaultImport.user_id == user_id)
            .order_by(VaultImport.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(VaultImport).where(VaultImport.user_id == user_id)
        )
