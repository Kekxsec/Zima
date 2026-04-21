import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.email_accounts import ServiceRegistry
from backend.app.db.repositories.service_registry import ServiceRegistryRepository


def _service(
    *,
    service_name: str,
    common_domains: list[str],
    display_name: str | None = None,
) -> ServiceRegistry:
    return ServiceRegistry(
        id=uuid.uuid4(),
        service_name=service_name,
        display_name=display_name or service_name.title(),
        category="finance",
        common_domains=common_domains,
        login_url="https://example.com/login",
        password_reset_url=None,
        is_active=True,
    )


@pytest.mark.asyncio
async def test_find_by_domain_matches_subdomain_suffix(
    db_session: AsyncSession,
) -> None:
    db_session.add(
        _service(service_name="trading212", common_domains=["trading212.com"])
    )
    await db_session.commit()

    repo = ServiceRegistryRepository(db_session)
    found = await repo.find_by_domain("alerts.eu.mail.trading212.com")

    assert found is not None
    assert found.service_name == "trading212"


@pytest.mark.asyncio
async def test_find_by_domain_matches_service_name_candidate(
    db_session: AsyncSession,
) -> None:
    db_session.add(
        _service(service_name="librarything", common_domains=["librarything.com"])
    )
    await db_session.commit()

    repo = ServiceRegistryRepository(db_session)
    found = await repo.find_by_domain("login.librarything.xyz")

    assert found is not None
    assert found.service_name == "librarything"


@pytest.mark.asyncio
async def test_find_by_domain_matches_bare_service_label(
    db_session: AsyncSession,
) -> None:
    db_session.add(_service(service_name="netflix", common_domains=["netflix.com"]))
    await db_session.commit()

    repo = ServiceRegistryRepository(db_session)
    found = await repo.find_by_domain("netflix")

    assert found is not None
    assert found.service_name == "netflix"
