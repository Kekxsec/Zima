# Phase 1 — Database Models & Repositories

## Goal
Create the persistence layer for the email account identifier feature: three new tables, three repository classes, and an Alembic migration.

---

## Files to Create

### 1. `backend/app/db/models/email_accounts.py`

Three SQLAlchemy 2.0 ORM models. No `Column()` style — only `Mapped[]`.

```python
# backend/app/db/models/email_accounts.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class MboxUploadStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DiscoveredAccountSourceType:
    ACCOUNT_CONFIRMATION = "account_confirmation"
    PASSWORD_RESET = "password_reset"
    RECEIPT = "receipt"
    NEWSLETTER = "newsletter"
    SECURITY_ALERT = "security_alert"
    OTHER = "other"


class ServiceRegistry(Base):
    """
    Curated catalog of known services with their login and password reset URLs.
    Seeded via scripts/seed_service_registry.py. Never auto-generated.
    """
    __tablename__ = "service_registry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)  # e.g. "github"
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)               # e.g. "GitHub"
    category: Mapped[str] = mapped_column(String(50), nullable=False)                    # e.g. "code", "email", "payment"
    common_domains: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)  # e.g. ["github.com"]
    login_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    password_reset_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_service_registry_name", "service_name"),
        Index("ix_service_registry_active", "is_active"),
    )


class MboxUpload(Base):
    """
    Tracks the lifecycle of a user-submitted mbox file.
    file_hash (SHA-256) + user_id = idempotency key.
    Raw file content is NEVER stored here.
    """
    __tablename__ = "mbox_uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)   # SHA-256 hex
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=MboxUploadStatus.PENDING)
    accounts_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    signals_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_detail: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "file_hash", name="uq_mbox_upload_user_hash"),
        Index("ix_mbox_upload_user_status", "user_id", "status"),
    )


class DiscoveredAccount(Base):
    """
    A service/account the user has interacted with, discovered by scanning mbox emails.
    (user_id, service_name, email_used) is the natural unique key.
    Raw email bodies are NEVER stored here — only metadata.
    """
    __tablename__ = "discovered_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    service_name: Mapped[str] = mapped_column(String(100), nullable=False)   # normalised, e.g. "github"
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)   # human-readable, e.g. "GitHub"
    email_used: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)     # DiscoveredAccountSourceType value
    login_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    password_reset_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sender_domain: Mapped[str] = mapped_column(String(255), nullable=False)  # raw domain from mbox sender
    email_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_reviewed: Mapped[bool] = mapped_column(nullable=False, default=False)  # user has reviewed this entry
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "service_name", "email_used", name="uq_discovered_account"),
        Index("ix_discovered_account_user", "user_id"),
        Index("ix_discovered_account_user_service", "user_id", "service_name"),
        Index("ix_discovered_account_reviewed", "user_id", "is_reviewed"),
    )
```

**Notes:**
- `upload_id` links back to `MboxUpload` but no FK defined (avoid cascading deletes; uploads are deleted independently)
- `is_reviewed` not `is_verified` — the rule that `is_verified` only goes on `Asset` rows set by `AssetService.register_verified_email()` (Rule 5)
- No raw email body fields anywhere

---

### 2. `backend/app/db/repositories/mbox_uploads.py`

```python
# backend/app/db/repositories/mbox_uploads.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
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
        upload = MboxUpload(user_id=user_id, filename=filename, file_hash=file_hash)
        self.session.add(upload)
        await self.session.flush()
        return upload

    async def get_by_id(self, upload_id: uuid.UUID, user_id: uuid.UUID) -> MboxUpload | None:
        result = await self.session.execute(
            select(MboxUpload).where(
                MboxUpload.id == upload_id,
                MboxUpload.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, user_id: uuid.UUID, file_hash: str) -> MboxUpload | None:
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
                processed_at=datetime.now(timezone.utc),
            )
        )

    async def set_failed(self, upload_id: uuid.UUID, error_detail: str) -> None:
        await self.session.execute(
            update(MboxUpload)
            .where(MboxUpload.id == upload_id)
            .values(
                status=MboxUploadStatus.FAILED,
                error_detail=error_detail[:1024],
                processed_at=datetime.now(timezone.utc),
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
```

---

### 3. `backend/app/db/repositories/discovered_accounts.py`

```python
# backend/app/db/repositories/discovered_accounts.py
import uuid
from datetime import datetime

from sqlalchemy import func, select, update
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
    ) -> DiscoveredAccount:
        """
        Insert or update by (user_id, service_name, email_used).
        On conflict: increment email_count, extend date range, update URLs if now known.
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
                    "email_count": DiscoveredAccount.email_count + email_count,
                    "last_seen_at": func.greatest(DiscoveredAccount.last_seen_at, last_seen_at),
                    "first_seen_at": func.least(DiscoveredAccount.first_seen_at, first_seen_at),
                    "login_url": func.coalesce(login_url, DiscoveredAccount.login_url),
                    "password_reset_url": func.coalesce(password_reset_url, DiscoveredAccount.password_reset_url),
                    "updated_at": func.now(),
                },
            )
            .returning(DiscoveredAccount)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_by_id(self, account_id: uuid.UUID, user_id: uuid.UUID) -> DiscoveredAccount | None:
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
        if service_name:
            q = q.where(DiscoveredAccount.service_name == service_name)
        if source_type:
            q = q.where(DiscoveredAccount.source_type == source_type)
        if is_reviewed is not None:
            q = q.where(DiscoveredAccount.is_reviewed == is_reviewed)
        q = q.order_by(DiscoveredAccount.service_name).limit(limit).offset(offset)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(DiscoveredAccount).where(DiscoveredAccount.user_id == user_id)
        )
        return result.scalar_one()

    async def mark_reviewed(self, account_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            update(DiscoveredAccount)
            .where(DiscoveredAccount.id == account_id, DiscoveredAccount.user_id == user_id)
            .values(is_reviewed=True)
            .returning(DiscoveredAccount.id)
        )
        return result.scalar_one_or_none() is not None

    async def get_all_for_user_export(self, user_id: uuid.UUID) -> list[DiscoveredAccount]:
        """Returns full list for CSV export — no pagination."""
        result = await self.session.execute(
            select(DiscoveredAccount)
            .where(DiscoveredAccount.user_id == user_id)
            .order_by(DiscoveredAccount.service_name)
        )
        return list(result.scalars().all())

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        """GDPR erasure."""
        from sqlalchemy import delete
        await self.session.execute(
            delete(DiscoveredAccount).where(DiscoveredAccount.user_id == user_id)
        )
```

---

### 4. `backend/app/db/repositories/service_registry.py`

```python
# backend/app/db/repositories/service_registry.py
from sqlalchemy import select
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
        from sqlalchemy import cast
        from sqlalchemy.dialects.postgresql import ARRAY
        from sqlalchemy import String as SAString
        result = await self.session.execute(
            select(ServiceRegistry).where(
                ServiceRegistry.common_domains.contains(cast([domain], ARRAY(SAString))),
                ServiceRegistry.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()
```

---

### 5. Migration: `backend/app/db/migrations/versions/XXXX_email_account_identifier_tables.py`

```python
# backend/app/db/migrations/versions/XXXX_email_account_identifier_tables.py
"""email account identifier tables

Revision ID: <generated>
Revises: <previous>
Create Date: <generated>
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, UUID

revision = "<generated>"
down_revision = "<previous>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # service_registry
    op.create_table(
        "service_registry",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("service_name", sa.String(100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("common_domains", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("login_url", sa.String(512), nullable=True),
        sa.Column("password_reset_url", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_service_registry_name", "service_registry", ["service_name"])
    op.create_index("ix_service_registry_active", "service_registry", ["is_active"])

    # mbox_uploads
    op.create_table(
        "mbox_uploads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("accounts_discovered", sa.Integer, nullable=False, server_default="0"),
        sa.Column("signals_created", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_detail", sa.String(1024), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_mbox_upload_user_hash", "mbox_uploads", ["user_id", "file_hash"])
    op.create_index("ix_mbox_upload_user_status", "mbox_uploads", ["user_id", "status"])

    # discovered_accounts
    op.create_table(
        "discovered_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("upload_id", UUID(as_uuid=True), nullable=False),
        sa.Column("service_name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("email_used", sa.String(512), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("login_url", sa.String(512), nullable=True),
        sa.Column("password_reset_url", sa.String(512), nullable=True),
        sa.Column("sender_domain", sa.String(255), nullable=False),
        sa.Column("email_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_reviewed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_discovered_account", "discovered_accounts", ["user_id", "service_name", "email_used"])
    op.create_index("ix_discovered_account_user", "discovered_accounts", ["user_id"])
    op.create_index("ix_discovered_account_user_service", "discovered_accounts", ["user_id", "service_name"])
    op.create_index("ix_discovered_account_reviewed", "discovered_accounts", ["user_id", "is_reviewed"])


def downgrade() -> None:
    op.drop_table("discovered_accounts")
    op.drop_table("mbox_uploads")
    op.drop_table("service_registry")
```

---

## Checklist
- [ ] `backend/app/db/models/email_accounts.py` — 3 ORM models + status/source-type constants
- [ ] `backend/app/db/repositories/mbox_uploads.py` — create, get_by_id, get_by_hash, set_processing, set_completed, set_failed, list_for_user
- [ ] `backend/app/db/repositories/discovered_accounts.py` — upsert, get_by_id, list_for_user, count_for_user, mark_reviewed, get_all_for_user_export, delete_all_for_user
- [ ] `backend/app/db/repositories/service_registry.py` — get_by_name, get_all_active, find_by_domain
- [ ] Migration file with all three tables, unique constraints, and indexes
- [ ] Import `ServiceRegistry`, `MboxUpload`, `DiscoveredAccount` in `backend/app/db/base.py` (or wherever Alembic autogenerates from) so they appear in `alembic revision --autogenerate`

## Dependencies
None — pure data layer, no imports from providers, modules, or API.

## Validation
- `alembic upgrade head` applies cleanly
- `alembic downgrade -1` reverses cleanly
- All three repository classes pass mypy
