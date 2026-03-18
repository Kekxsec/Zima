# backend/app/assets/service.py
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.assets.models import Asset
from backend.app.core.logging import get_logger
from backend.app.db.repositories.assets import AssetRepository

logger = get_logger(__name__)


class AssetService:
    def __init__(self, session: AsyncSession, asset_repo: AssetRepository) -> None:
        self.session = session
        self.asset_repo = asset_repo

    async def register_verified_email(self, user_id: uuid.UUID, email: str) -> Asset:
        existing = await self.asset_repo.get_by_value(
            user_id=user_id,
            entity_type="email",
            value=email,
        )

        if existing:
            if not existing.is_verified:
                existing.is_verified = True
                existing.verified_at = datetime.now(UTC)
                await self.session.commit()
                logger.info("asset.email_reverified", user_id=str(user_id))
            return existing

        primary_exists = await self.asset_repo.get_primary_email(user_id)

        asset = Asset(
            user_id=user_id,
            entity_type="email",
            value=email,
            is_primary=(primary_exists is None),
            is_verified=True,
            verified_at=datetime.now(UTC),
        )
        self.session.add(asset)
        await self.session.commit()
        logger.info("asset.email_registered", user_id=str(user_id))
        return asset
