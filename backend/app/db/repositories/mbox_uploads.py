# backend/app/db/repositories/mbox_uploads.py
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.email_accounts import MboxUpload, MboxUploadStatus


class MboxUploadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: uuid.UUID,
        filename: str,
        file_hash: str,
    ) -> MboxUpload:
        upload = MboxUpload(
            user_id=user_id,
            filename=filename,
            file_hash=file_hash,
        )
        self.session.add(upload)
        await self.session.flush()
        return upload

    async def get_by_id(
        self, upload_id: uuid.UUID, user_id: uuid.UUID
    ) -> MboxUpload | None:
        result = await self.session.execute(
            select(MboxUpload).where(
                MboxUpload.id == upload_id,
                MboxUpload.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_hash(
        self, user_id: uuid.UUID, file_hash: str
    ) -> MboxUpload | None:
        """Idempotency check — has this exact file been uploaded before?"""
        result = await self.session.execute(
            select(MboxUpload).where(
                MboxUpload.user_id == user_id,
                MboxUpload.file_hash == file_hash,
            )
        )
        return result.scalar_one_or_none()

    async def set_processing(self, upload_id: uuid.UUID) -> None:
        await self.session.execute(
            update(MboxUpload)
            .where(MboxUpload.id == upload_id)
            .values(status=MboxUploadStatus.PROCESSING)
        )

    async def set_completed(
        self,
        upload_id: uuid.UUID,
        accounts_discovered: int,
        signals_created: int,
    ) -> None:
        await self.session.execute(
            update(MboxUpload)
            .where(MboxUpload.id == upload_id)
            .values(
                status=MboxUploadStatus.COMPLETED,
                accounts_discovered=accounts_discovered,
                signals_created=signals_created,
                processed_at=datetime.now(UTC),
            )
        )

    async def set_failed(self, upload_id: uuid.UUID, error_detail: str) -> None:
        await self.session.execute(
            update(MboxUpload)
            .where(MboxUpload.id == upload_id)
            .values(
                status=MboxUploadStatus.FAILED,
                error_detail=error_detail[:1024],
                processed_at=datetime.now(UTC),
            )
        )

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[MboxUpload]:
        result = await self.session.execute(
            select(MboxUpload)
            .where(MboxUpload.user_id == user_id)
            .order_by(MboxUpload.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        """Hard-deletes all mbox upload records for a user. Used by GDPR erasure."""
        await self.session.execute(
            delete(MboxUpload).where(MboxUpload.user_id == user_id)
        )
