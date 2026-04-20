# backend/app/db/repositories/newsletter_subscriptions.py
import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.email_accounts import NewsletterSubscription

_MAX_SENDER_DOMAIN_LEN = 255
_MAX_SENDER_NAME_LEN = 255
_MAX_UNSUBSCRIBE_URL_LEN = 1024
_MAX_LIST_ID_LEN = 512
_MAX_CONFIDENCE_LEN = 20


def _sanitize_required(value: str, max_len: int, fallback: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        cleaned = fallback
    return cleaned[:max_len]


def _sanitize_optional(value: str | None, max_len: int) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned[:max_len]


def _sanitize_optional_url(value: str | None, max_len: int) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    # For untrusted URL-like fields, avoid storing truncated broken links.
    if len(cleaned) > max_len:
        return None
    return cleaned


class NewsletterSubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        user_id: uuid.UUID,
        upload_id: uuid.UUID,
        sender_domain: str,
        sender_name: str | None,
        message_count: int,
        first_seen_at: datetime | None,
        last_seen_at: datetime | None,
        unsubscribe_url: str | None,
        list_id: str | None,
        confidence: str,
        is_phishing: bool = False,
    ) -> NewsletterSubscription:
        """
        Insert or update a newsletter subscription record.
        On conflict (user_id, sender_domain): accumulates message_count,
        extends first/last_seen_at, updates unsubscribe_url and list_id.
        If is_phishing=True, latches the flag on (never reverts to False).
        """
        safe_sender_domain = _sanitize_required(
            sender_domain.lower(), _MAX_SENDER_DOMAIN_LEN, "unknown.local"
        )
        safe_sender_name = _sanitize_optional(sender_name, _MAX_SENDER_NAME_LEN)
        safe_unsubscribe_url = _sanitize_optional_url(
            unsubscribe_url, _MAX_UNSUBSCRIBE_URL_LEN
        )
        safe_list_id = _sanitize_optional(list_id, _MAX_LIST_ID_LEN)
        safe_confidence = _sanitize_required(confidence, _MAX_CONFIDENCE_LEN, "high")

        stmt = (
            insert(NewsletterSubscription)
            .values(
                user_id=user_id,
                upload_id=upload_id,
                sender_domain=safe_sender_domain,
                sender_name=safe_sender_name,
                message_count=message_count,
                first_seen_at=first_seen_at,
                last_seen_at=last_seen_at,
                unsubscribe_url=safe_unsubscribe_url,
                list_id=safe_list_id,
                confidence=safe_confidence,
                is_phishing=is_phishing,
            )
            .on_conflict_do_update(
                constraint="uq_newsletter_subscription",
                set_={
                    "message_count": NewsletterSubscription.message_count
                    + message_count,
                    "last_seen_at": last_seen_at,
                    "unsubscribe_url": safe_unsubscribe_url,
                    "list_id": safe_list_id,
                    "sender_name": safe_sender_name,
                    # Latch: once phishing, always phishing — never clear on re-upsert
                    "is_phishing": NewsletterSubscription.is_phishing | is_phishing,
                },
            )
            .returning(NewsletterSubscription)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one()
        return row

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        reviewed: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[NewsletterSubscription]:
        q = select(NewsletterSubscription).where(
            NewsletterSubscription.user_id == user_id
        )
        if reviewed is not None:
            q = q.where(NewsletterSubscription.is_reviewed == reviewed)
        q = (
            q.order_by(NewsletterSubscription.message_count.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def mark_reviewed(
        self, subscription_id: uuid.UUID, user_id: uuid.UUID
    ) -> NewsletterSubscription | None:
        record = await self.get_by_id(subscription_id, user_id)
        if record is None:
            return None
        record.is_reviewed = True
        await self.session.flush()
        return record

    async def get_by_id(
        self, subscription_id: uuid.UUID, user_id: uuid.UUID
    ) -> NewsletterSubscription | None:
        result = await self.session.execute(
            select(NewsletterSubscription).where(
                NewsletterSubscription.id == subscription_id,
                NewsletterSubscription.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(NewsletterSubscription).where(
                NewsletterSubscription.user_id == user_id
            )
        )
