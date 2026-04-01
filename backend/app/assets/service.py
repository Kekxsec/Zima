# backend/app/assets/service.py
import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
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
        try:
            await self.session.commit()
        except IntegrityError:
            # Two concurrent verify_otp calls for the same email raced to insert.
            # The constraint uq_asset_user_type_value caught the duplicate.
            # Roll back and return the row the winning request created.
            await self.session.rollback()
            winner = await self.asset_repo.get_by_value(
                user_id=user_id,
                entity_type="email",
                value=email,
            )
            if winner is None:
                # Should be unreachable: IntegrityError means the row exists.
                raise
            logger.info("asset.email_register_race_resolved", user_id=str(user_id))
            return winner

        logger.info("asset.email_registered", user_id=str(user_id))
        return asset

    async def register_declared_asset(
        self,
        user_id: uuid.UUID,
        entity_type: str,
        value: str,
    ) -> Asset:
        """Register a user-declared non-email asset as verified.

        Unlike register_verified_email, this does not require OTP. The user is
        asserting ownership, so is_verified=True is set as the verification
        event for scan-eligible assets.
        """
        existing = await self.asset_repo.get_by_value(
            user_id=user_id,
            entity_type=entity_type,
            value=value,
        )
        if existing:
            return existing

        asset = Asset(
            user_id=user_id,
            entity_type=entity_type,
            value=value,
            is_primary=False,
            is_verified=True,
            verified_at=datetime.now(UTC),
        )
        self.session.add(asset)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            winner = await self.asset_repo.get_by_value(
                user_id=user_id,
                entity_type=entity_type,
                value=value,
            )
            if winner is None:
                raise
            return winner

        logger.info(
            "asset.declared_registered",
            user_id=str(user_id),
            entity_type=entity_type,
        )
        return asset
