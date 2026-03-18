# Stage 3 — Signal Pipeline

**Exit condition:** Signals can be created, stored, deduplicated via atomic upsert, and lifecycle-transitioned. Scores are versioned and historical records are preserved. FindingRepository is fully defined with a proper upsert. All tests pass including negative cases.

---

## 3.1 Asset Model

```python
# assets/models.py
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base, TimestampMixin
from backend.app.core.enums import EntityType

class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[str] = mapped_column(String(512), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Verified = user has proven ownership (via OTP sign-in or explicit verification flow)
    # Scans MUST NOT run against assets where is_verified=False
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("user_id", "entity_type", "value", name="uq_asset_user_type_value"),
        Index("ix_asset_user_verified", "user_id", "is_verified"),
    )
```

---

## 3.2 Signal Model

```python
# signals/models.py
import uuid
from sqlalchemy import String, JSON, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base, TimestampMixin

class Signal(Base, TimestampMixin):
    __tablename__ = "signals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Deterministic ID — same user + signal_type + entity always produces the same value
    # This is the deduplication key used by the upsert
    signal_id: Mapped[str] = mapped_column(String(32), nullable=False)

    signal_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False
    )
    entity_value: Mapped[str] = mapped_column(String(512), nullable=False)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)

    source: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)

    summary: Mapped[str] = mapped_column(String(512), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(String(512), nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)

    __table_args__ = (
        # signal_id is the deduplication key — one row per unique combination
        UniqueConstraint("signal_id", name="uq_signal_id"),
        Index("ix_signal_user_status", "user_id", "status"),
        Index("ix_signal_user_type", "user_id", "signal_type"),
    )
```

---

## 3.3 Signal Deduplication

```python
# signals/dedup.py
import hashlib
import uuid

def compute_signal_id(
    user_id: uuid.UUID,
    signal_type: str,
    entity_id: uuid.UUID,
) -> str:
    """
    Deterministic signal ID. Same three inputs always produce the same ID.
    This means the same real-world condition detected on consecutive scans
    produces one row (upserted), not duplicate rows.
    """
    key = f"{user_id}:{signal_type}:{entity_id}"
    return "sig_" + hashlib.sha256(key.encode()).hexdigest()[:24]
```

---

## 3.4 Signal Repository

```python
# db/repositories/signals.py
import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from backend.app.signals.models import Signal
from backend.app.signals.schemas import SignalCreate
from backend.app.signals.dedup import compute_signal_id
from backend.app.core.enums import SignalStatus

class SignalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, data: SignalCreate) -> Signal:
        """
        Atomic insert-or-update. If a signal with the same signal_id
        already exists, it is updated to open status with fresh evidence.
        This prevents duplicate rows on repeated scan runs.
        """
        signal_id = compute_signal_id(data.user_id, data.signal_type, data.entity_id)

        stmt = (
            pg_insert(Signal)
            .values(
                signal_id=signal_id,
                signal_type=data.signal_type,
                category=data.category,
                entity_type=data.entity_type.value,
                entity_id=data.entity_id,
                entity_value=data.entity_value,
                user_id=data.user_id,
                severity=data.severity.value,
                confidence=data.confidence.value,
                source=data.source,
                provider=data.provider,
                summary=data.summary,
                details=data.details,
                evidence=data.evidence,
                tags=data.tags,
                recommended_action=data.recommended_action,
                status=SignalStatus.OPEN,
            )
            .on_conflict_do_update(
                constraint="uq_signal_id",
                set_={
                    "status": SignalStatus.OPEN,
                    "severity": data.severity.value,
                    "evidence": data.evidence,
                    "updated_at": func.now(),
                },
            )
            .returning(Signal)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_open_for_user(
        self,
        user_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Signal]:
        result = await self.session.execute(
            select(Signal)
            .where(Signal.user_id == user_id, Signal.status == SignalStatus.OPEN)
            .order_by(Signal.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_open_for_user(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Signal)
            .where(Signal.user_id == user_id, Signal.status == SignalStatus.OPEN)
        )
        return result.scalar_one()
```

---

## 3.5 Finding Model and Repository

Both are defined here together. The finding repository uses the same upsert pattern as signals — deterministic IDs prevent duplicate findings on repeated correlation runs.

```python
# correlation/models.py
import uuid
from sqlalchemy import String, JSON, ForeignKey, Text, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base, TimestampMixin

class Finding(Base, TimestampMixin):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Deterministic ID — same rule + same contributing signals = same finding_id
    finding_id: Mapped[str] = mapped_column(String(32), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    contributing_signal_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    affected_entity_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)

    __table_args__ = (
        UniqueConstraint("finding_id", name="uq_finding_id"),
        Index("ix_finding_user_status", "user_id", "status"),
    )
```

```python
# db/repositories/findings.py
import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from backend.app.correlation.models import Finding

class FindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, finding: Finding) -> Finding:
        """
        Inserts or updates a finding by finding_id.
        Repeated correlation runs on the same signal set produce one finding row.
        """
        stmt = (
            pg_insert(Finding)
            .values(
                finding_id=finding.finding_id,
                finding_type=finding.finding_type,
                user_id=finding.user_id,
                severity=finding.severity,
                confidence=finding.confidence,
                title=finding.title,
                explanation=finding.explanation,
                contributing_signal_ids=finding.contributing_signal_ids,
                affected_entity_ids=finding.affected_entity_ids,
                rule_name=finding.rule_name,
                status="open",
            )
            .on_conflict_do_update(
                constraint="uq_finding_id",
                set_={
                    "status": "open",
                    "explanation": finding.explanation,
                    "contributing_signal_ids": finding.contributing_signal_ids,
                    "updated_at": func.now(),
                },
            )
            .returning(Finding)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_open_for_user(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Finding]:
        result = await self.session.execute(
            select(Finding)
            .where(Finding.user_id == user_id, Finding.status == "open")
            .order_by(Finding.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
```

---

## 3.6 Score Model with Versioning

Scores are **never overwritten**. Each scan cycle appends a new score record. This preserves the full score history for trend visualisation and means you can always explain any historical score.

```python
# scoring/models.py
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base

class Score(Base):
    """
    Append-only score record. One row per scan cycle per domain per user.
    Never update — always insert. Query for the latest with ORDER BY calculated_at DESC.
    """
    __tablename__ = "scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    # Version identifies which scoring model produced this score.
    # Increment when weights or calculator logic changes so historical
    # scores remain explainable and comparable within a version.
    scorer_version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    signal_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Link to the scan that produced this score
    scan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id"), nullable=True
    )

    __table_args__ = (
        Index("ix_score_user_domain_time", "user_id", "domain", "calculated_at"),
    )
```

```python
# db/repositories/scores.py
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.scoring.models import Score

class ScoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert(
        self,
        user_id: uuid.UUID,
        domain: str,
        score: int,
        signal_count: int,
        scan_id: uuid.UUID | None = None,
        scorer_version: str = "1.0",
    ) -> Score:
        """Always insert — never update. Historical scores are immutable."""
        record = Score(
            user_id=user_id,
            domain=domain,
            score=score,
            signal_count=signal_count,
            scorer_version=scorer_version,
            scan_id=scan_id,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_latest_for_user(self, user_id: uuid.UUID) -> list[Score]:
        """Returns the most recent score per domain for a user."""
        # Subquery for max calculated_at per domain
        from sqlalchemy import func
        subq = (
            select(Score.domain, func.max(Score.calculated_at).label("max_ts"))
            .where(Score.user_id == user_id)
            .group_by(Score.domain)
            .subquery()
        )
        result = await self.session.execute(
            select(Score)
            .join(subq, (Score.domain == subq.c.domain) & (Score.calculated_at == subq.c.max_ts))
            .where(Score.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_history_for_domain(
        self,
        user_id: uuid.UUID,
        domain: str,
        limit: int = 30,
    ) -> list[Score]:
        """Returns score history for trend charts."""
        result = await self.session.execute(
            select(Score)
            .where(Score.user_id == user_id, Score.domain == domain)
            .order_by(Score.calculated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
```

---

## 3.7 Stage 3 Tests

```python
# tests/unit/signals/test_dedup.py
import uuid
from backend.app.signals.dedup import compute_signal_id


def test_same_inputs_always_produce_same_signal_id() -> None:
    uid = uuid.uuid4()
    eid = uuid.uuid4()
    assert compute_signal_id(uid, "email_breached", eid) == compute_signal_id(uid, "email_breached", eid)


def test_different_entity_produces_different_signal_id() -> None:
    uid = uuid.uuid4()
    assert compute_signal_id(uid, "email_breached", uuid.uuid4()) != compute_signal_id(uid, "email_breached", uuid.uuid4())


def test_different_signal_type_produces_different_signal_id() -> None:
    uid = uuid.uuid4()
    eid = uuid.uuid4()
    assert compute_signal_id(uid, "email_breached", eid) != compute_signal_id(uid, "mfa_missing", eid)


def test_signal_id_has_expected_prefix() -> None:
    result = compute_signal_id(uuid.uuid4(), "email_breached", uuid.uuid4())
    assert result.startswith("sig_")
```

```python
# tests/unit/signals/test_repositories.py
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.repositories.signals import SignalRepository
from backend.app.signals.schemas import SignalCreate
from backend.app.core.enums import Severity, Confidence, EntityType, SignalStatus
from tests.factories import UserFactory, AssetFactory


def _make_signal_create(user_id: uuid.UUID, asset_id: uuid.UUID, signal_type: str = "email_breached") -> SignalCreate:
    return SignalCreate(
        signal_type=signal_type,
        category="identity_security",
        entity_type=EntityType.EMAIL,
        entity_id=asset_id,
        entity_value="test@example.com",
        user_id=user_id,
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        source="breach_monitor",
        provider="hibp",
        summary="Found in breach",
        evidence={"breach_name": "Test"},
        tags=["identity"],
    )


@pytest.mark.asyncio
async def test_upsert_creates_new_signal(db_session: AsyncSession) -> None:
    user = UserFactory.build()
    db_session.add(user)
    asset = AssetFactory.build(user_id=user.id)
    db_session.add(asset)
    await db_session.flush()

    repo = SignalRepository(db_session)
    signal = await repo.upsert(_make_signal_create(user.id, asset.id))
    await db_session.commit()

    assert signal.id is not None
    assert signal.status == SignalStatus.OPEN


@pytest.mark.asyncio
async def test_upsert_same_signal_does_not_create_duplicate(db_session: AsyncSession) -> None:
    user = UserFactory.build()
    db_session.add(user)
    asset = AssetFactory.build(user_id=user.id)
    db_session.add(asset)
    await db_session.flush()

    repo = SignalRepository(db_session)
    data = _make_signal_create(user.id, asset.id)
    s1 = await repo.upsert(data)
    await db_session.commit()
    s2 = await repo.upsert(data)
    await db_session.commit()

    assert s1.id == s2.id  # Same row, not two rows
    signals = await repo.get_open_for_user(user.id)
    assert len(signals) == 1


@pytest.mark.asyncio
async def test_get_open_for_user_excludes_resolved(db_session: AsyncSession) -> None:
    user = UserFactory.build()
    db_session.add(user)
    asset = AssetFactory.build(user_id=user.id)
    db_session.add(asset)
    await db_session.flush()

    repo = SignalRepository(db_session)
    signal = await repo.upsert(_make_signal_create(user.id, asset.id))
    await db_session.commit()

    from sqlalchemy import update
    from backend.app.signals.models import Signal
    await db_session.execute(
        update(Signal).where(Signal.id == signal.id).values(status="resolved")
    )
    await db_session.commit()

    signals = await repo.get_open_for_user(user.id)
    assert len(signals) == 0


@pytest.mark.asyncio
async def test_score_insert_appends_not_overwrites(db_session: AsyncSession) -> None:
    user = UserFactory.build()
    db_session.add(user)
    await db_session.flush()

    from backend.app.db.repositories.scores import ScoreRepository
    repo = ScoreRepository(db_session)

    await repo.insert(user_id=user.id, domain="identity", score=90, signal_count=1)
    await db_session.commit()
    await repo.insert(user_id=user.id, domain="identity", score=70, signal_count=3)
    await db_session.commit()

    history = await repo.get_history_for_domain(user.id, "identity", limit=10)
    assert len(history) == 2
    # Most recent first
    assert history[0].score == 70
    assert history[1].score == 90


@pytest.mark.asyncio
async def test_score_get_latest_returns_most_recent_per_domain(db_session: AsyncSession) -> None:
    user = UserFactory.build()
    db_session.add(user)
    await db_session.flush()

    from backend.app.db.repositories.scores import ScoreRepository
    repo = ScoreRepository(db_session)

    await repo.insert(user_id=user.id, domain="identity", score=80, signal_count=2)
    await db_session.commit()
    await repo.insert(user_id=user.id, domain="identity", score=60, signal_count=4)
    await db_session.commit()

    latest = await repo.get_latest_for_user(user.id)
    assert len(latest) == 1
    assert latest[0].score == 60  # Most recent
```

**Stage 3 Verification:**
```bash
uv run pytest tests/unit/signals/ -v
uv run python scripts/check_imports.py
```
