# backend/app/db/repositories/discovered_accounts.py
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.email_accounts import (
    DiscoveredAccount,
    DiscoveredAccountSourceType,
)

if TYPE_CHECKING:
    from backend.app.db.repositories.service_registry import ServiceRegistryRepository

_MAX_SERVICE_NAME_LEN = 100
_MAX_DISPLAY_NAME_LEN = 200
_MAX_EMAIL_USED_LEN = 512
_MAX_SOURCE_TYPE_LEN = 50
_MAX_SENDER_DOMAIN_LEN = 255
_MAX_LOGIN_URL_LEN = 512
_MAX_PASSWORD_RESET_URL_LEN = 512
_MAX_UNSUBSCRIBE_URL_LEN = 1024


def _sanitize_required(value: str, max_len: int, fallback: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        cleaned = fallback
    return cleaned[:max_len]


def _sanitize_optional_url(value: str | None, max_len: int) -> str | None:
    """
    Guard DB writes against oversized URL payloads from untrusted headers.

    Legacy schemas may still use VARCHAR(512/1024) for URL columns.
    For overlong URL-like values, prefer dropping to NULL over storing a
    truncated, potentially invalid link.
    """
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > max_len:
        return None
    return cleaned


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
        unsubscribe_url: str | None = None,
        first_seen_at: datetime | None = None,
        last_seen_at: datetime | None = None,
        email_count: int = 1,
        confidence_score: int = 0,
        increment_email_count: bool = True,
    ) -> DiscoveredAccount:
        """
        Insert or update by (user_id, service_name, email_used).
        On conflict: increment email_count, extend date range, and fill in
        URLs if now known.
        """
        safe_service_name = _sanitize_required(
            service_name, _MAX_SERVICE_NAME_LEN, "unknown"
        )
        safe_display_name = _sanitize_required(
            display_name, _MAX_DISPLAY_NAME_LEN, safe_service_name
        )
        safe_email_used = _sanitize_required(
            email_used.lower(), _MAX_EMAIL_USED_LEN, "unknown@local"
        )
        safe_source_type = _sanitize_required(
            source_type, _MAX_SOURCE_TYPE_LEN, "other"
        )
        safe_sender_domain = _sanitize_required(
            sender_domain.lower(), _MAX_SENDER_DOMAIN_LEN, "unknown.local"
        )
        safe_login_url = _sanitize_optional_url(login_url, _MAX_LOGIN_URL_LEN)
        safe_password_reset_url = _sanitize_optional_url(
            password_reset_url, _MAX_PASSWORD_RESET_URL_LEN
        )
        safe_unsubscribe_url = _sanitize_optional_url(
            unsubscribe_url, _MAX_UNSUBSCRIBE_URL_LEN
        )

        stmt = (
            pg_insert(DiscoveredAccount)
            .values(
                user_id=user_id,
                upload_id=upload_id,
                service_name=safe_service_name,
                display_name=safe_display_name,
                email_used=safe_email_used,
                source_type=safe_source_type,
                sender_domain=safe_sender_domain,
                login_url=safe_login_url,
                password_reset_url=safe_password_reset_url,
                unsubscribe_url=safe_unsubscribe_url,
                first_seen_at=first_seen_at,
                last_seen_at=last_seen_at,
                email_count=email_count,
                confidence_score=confidence_score,
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
                    "login_url": func.coalesce(
                        safe_login_url, DiscoveredAccount.login_url
                    ),
                    "password_reset_url": func.coalesce(
                        safe_password_reset_url, DiscoveredAccount.password_reset_url
                    ),
                    "unsubscribe_url": func.coalesce(
                        safe_unsubscribe_url, DiscoveredAccount.unsubscribe_url
                    ),
                    # Never downgrade confidence on re-upsert
                    "confidence_score": func.greatest(
                        DiscoveredAccount.confidence_score, confidence_score
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

    async def list_all_for_user(
        self,
        user_id: uuid.UUID,
    ) -> list[DiscoveredAccount]:
        """
        Full list of discovered accounts for a user (no pagination).
        """
        result = await self.session.execute(
            select(DiscoveredAccount)
            .where(DiscoveredAccount.user_id == user_id)
            .order_by(DiscoveredAccount.service_name)
        )
        return list(result.scalars().all())

    async def list_for_upload(
        self,
        user_id: uuid.UUID,
        upload_id: uuid.UUID,
    ) -> list[DiscoveredAccount]:
        """
        List discovered accounts created from one mailbox upload.
        """
        result = await self.session.execute(
            select(DiscoveredAccount)
            .where(
                DiscoveredAccount.user_id == user_id,
                DiscoveredAccount.upload_id == upload_id,
            )
            .order_by(DiscoveredAccount.service_name)
        )
        return list(result.scalars().all())

    async def list_for_user_with_category(
        self,
        user_id: uuid.UUID,
        source_type: str | None = None,
        is_reviewed: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[tuple[DiscoveredAccount, str | None]]:
        """List accounts with their service_registry category (LEFT JOIN)."""
        from backend.app.db.models.email_accounts import ServiceRegistry

        q = (
            select(DiscoveredAccount, ServiceRegistry.category)
            .outerjoin(
                ServiceRegistry,
                DiscoveredAccount.service_name == ServiceRegistry.service_name,
            )
            .where(DiscoveredAccount.user_id == user_id)
        )
        if source_type is not None:
            q = q.where(DiscoveredAccount.source_type == source_type)
        if is_reviewed is not None:
            q = q.where(DiscoveredAccount.is_reviewed == is_reviewed)
        q = q.order_by(DiscoveredAccount.service_name).limit(limit).offset(offset)
        result = await self.session.execute(q)
        return [(row[0], row[1]) for row in result.all()]

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

    async def set_verdict(
        self,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
        verdict: str,
    ) -> bool:
        """
        Set user_verdict on a discovered account.
        Accepted values: confirmed, dismissed, newsletter, receipt.
        Returns True if the row was found and updated.
        """
        result = await self.session.execute(
            update(DiscoveredAccount)
            .where(
                DiscoveredAccount.id == account_id,
                DiscoveredAccount.user_id == user_id,
            )
            .values(user_verdict=verdict, is_reviewed=True)
            .returning(DiscoveredAccount.id)
        )
        return result.scalar_one_or_none() is not None

    async def update_identity_fields(
        self,
        *,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
        service_name: str,
        display_name: str,
    ) -> DiscoveredAccount | None:
        """
        Update service/display identity for one discovered account.

        Safety rule:
        - If changing service_name would collide with another row's natural key
          (user_id, service_name, email_used), keep the existing service_name and
          still apply display_name.
        """
        current = await self.get_by_id(account_id=account_id, user_id=user_id)
        if current is None:
            return None

        next_service = service_name.strip().lower() or current.service_name
        next_display = display_name.strip() or current.display_name

        if next_service != current.service_name:
            conflict_stmt = select(DiscoveredAccount.id).where(
                DiscoveredAccount.user_id == user_id,
                DiscoveredAccount.email_used == current.email_used,
                DiscoveredAccount.service_name == next_service,
                DiscoveredAccount.id != account_id,
            )
            conflict = await self.session.execute(conflict_stmt)
            if conflict.scalar_one_or_none() is not None:
                next_service = current.service_name

        if (
            next_service == current.service_name
            and next_display == current.display_name
        ):
            return current

        result = await self.session.execute(
            update(DiscoveredAccount)
            .where(
                DiscoveredAccount.id == account_id,
                DiscoveredAccount.user_id == user_id,
            )
            .values(
                service_name=next_service,
                display_name=next_display,
                updated_at=func.now(),
            )
            .returning(DiscoveredAccount)
        )
        return result.scalar_one_or_none()

    async def list_by_confidence(
        self,
        user_id: uuid.UUID,
        min_score: int,
        max_score: int,
        include_dismissed: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DiscoveredAccount]:
        """
        List accounts within a confidence score band.
        Ordered by confidence_score desc, then email_count desc.
        """
        q = select(DiscoveredAccount).where(
            DiscoveredAccount.user_id == user_id,
            DiscoveredAccount.confidence_score >= min_score,
            DiscoveredAccount.confidence_score <= max_score,
        )
        if not include_dismissed:
            q = q.where(DiscoveredAccount.user_verdict != "dismissed")
        q = (
            q.order_by(
                DiscoveredAccount.confidence_score.desc(),
                DiscoveredAccount.email_count.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        """Hard-deletes all discovered accounts for a user. Used by GDPR erasure."""
        await self.session.execute(
            delete(DiscoveredAccount).where(DiscoveredAccount.user_id == user_id)
        )

    async def merge_duplicates_by_domain(self, user_id: uuid.UUID) -> int:
        """
        Merge accounts sharing (sender_domain, email_used) that differ in service_name.
        After Ollama renames an account the pre-rename row may persist beside it.
        Keeps the winner (highest confidence_score then email_count), sums email_counts,
        takes the best available URLs, and hard-deletes the losers.
        Returns the number of rows deleted.
        """
        accounts = await self.list_all_for_user(user_id)
        groups: dict[tuple[str, str], list[DiscoveredAccount]] = defaultdict(list)
        for account in accounts:
            groups[(account.sender_domain, account.email_used)].append(account)

        deleted = 0
        for group in groups.values():
            if len(group) <= 1:
                continue
            winner = max(group, key=lambda a: (a.confidence_score, a.email_count))
            losers = [a for a in group if a.id != winner.id]

            total_count = sum(a.email_count for a in group)
            best_login = next((a.login_url for a in group if a.login_url), None)
            best_reset = next(
                (a.password_reset_url for a in group if a.password_reset_url), None
            )
            best_unsub = next(
                (a.unsubscribe_url for a in group if a.unsubscribe_url), None
            )
            first_times = [
                a.first_seen_at for a in group if a.first_seen_at is not None
            ]
            earliest = min(first_times) if first_times else winner.first_seen_at
            last_times = [a.last_seen_at for a in group if a.last_seen_at is not None]
            latest = max(last_times) if last_times else winner.last_seen_at

            await self.session.execute(
                update(DiscoveredAccount)
                .where(DiscoveredAccount.id == winner.id)
                .values(
                    email_count=total_count,
                    login_url=best_login,
                    password_reset_url=best_reset,
                    unsubscribe_url=best_unsub,
                    first_seen_at=earliest,
                    last_seen_at=latest,
                    updated_at=func.now(),
                )
            )
            await self.session.execute(
                delete(DiscoveredAccount).where(
                    DiscoveredAccount.id.in_([a.id for a in losers])
                )
            )
            deleted += len(losers)

        return deleted

    async def backfill_urls_from_registry(
        self,
        user_id: uuid.UUID,
        registry_repo: ServiceRegistryRepository,
    ) -> int:
        """
        For accounts with a known service_name but missing login_url, look up
        service_registry and copy login_url / password_reset_url.
        Returns number of rows updated.
        """
        accounts = await self.list_all_for_user(user_id)
        updated = 0
        for account in accounts:
            if account.login_url:
                continue
            if not account.service_name or account.service_name == "unknown":
                continue
            registry = await registry_repo.get_by_name(account.service_name)
            if registry is None:
                continue
            if not registry.login_url and not registry.password_reset_url:
                continue
            await self.session.execute(
                update(DiscoveredAccount)
                .where(DiscoveredAccount.id == account.id)
                .values(
                    login_url=registry.login_url or account.login_url,
                    password_reset_url=(
                        registry.password_reset_url or account.password_reset_url
                    ),
                    updated_at=func.now(),
                )
            )
            updated += 1
        return updated

    async def classify_accounts(
        self,
        user_id: uuid.UUID,
        registry_repo: ServiceRegistryRepository | None = None,
    ) -> int:
        """
        Set account_category on all accounts for the user based on source_type,
        unsubscribe_url presence, and optionally service_registry category.
        Returns number of rows updated.
        """
        _newsletter_sources = {DiscoveredAccountSourceType.NEWSLETTER}
        _account_sources = {
            DiscoveredAccountSourceType.ACCOUNT_CONFIRMATION,
            DiscoveredAccountSourceType.PASSWORD_RESET,
            DiscoveredAccountSourceType.SECURITY_ALERT,
            DiscoveredAccountSourceType.EPIEOS,
            DiscoveredAccountSourceType.HOLEHE,
            DiscoveredAccountSourceType.MAIGRET,
            DiscoveredAccountSourceType.PASSWORD_MANAGER,
        }

        accounts = await self.list_all_for_user(user_id)
        updated = 0
        for account in accounts:
            if account.source_type in _newsletter_sources:
                category = "newsletter"
            elif account.source_type == DiscoveredAccountSourceType.RECEIPT:
                category = "receipt"
            elif account.unsubscribe_url:
                category = "newsletter"
            elif account.source_type in _account_sources:
                category = "account"
            elif registry_repo is not None and account.service_name not in (
                None,
                "unknown",
            ):
                reg = await registry_repo.get_by_name(account.service_name)
                if reg and reg.category in ("newsletter", "receipt", "notification"):
                    category = reg.category
                else:
                    category = "account"
            else:
                category = "account"

            if account.account_category == category:
                continue

            await self.session.execute(
                update(DiscoveredAccount)
                .where(DiscoveredAccount.id == account.id)
                .values(account_category=category, updated_at=func.now())
            )
            updated += 1

        return updated
