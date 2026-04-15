# tests/integration/test_repositories.py
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.enums import Confidence, EntityType, Severity, SignalStatus
from backend.app.db.repositories.signals import SignalRepository
from backend.app.signals.schemas import SignalCreate
from tests.factories import AssetFactory, UserFactory


def _make_signal_create(
    user_id: uuid.UUID, asset_id: uuid.UUID, signal_type: str = "email_breached"
) -> SignalCreate:
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
async def test_upsert_same_signal_does_not_create_duplicate(
    db_session: AsyncSession,
) -> None:
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
async def test_score_get_latest_returns_most_recent_per_domain(
    db_session: AsyncSession,
) -> None:
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
