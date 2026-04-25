# backend/app/db/repositories/service_registry.py
from sqlalchemy import String as SAString
from sqlalchemy import cast, select
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.email_accounts import ServiceRegistry

_GENERIC_SUBDOMAIN_LABELS: frozenset[str] = frozenset(
    {
        "www",
        "m",
        "mail",
        "email",
        "mailer",
        "noreply",
        "no-reply",
        "notify",
        "notifications",
        "news",
        "support",
        "help",
        "account",
        "accounts",
        "login",
        "secure",
        "auth",
        "id",
        "info",
        "updates",
        "billing",
        "receipt",
        "receipts",
        "orders",
    }
)

_MULTIPART_PUBLIC_SUFFIXES: frozenset[str] = frozenset(
    {
        "co.uk",
        "org.uk",
        "gov.uk",
        "ac.uk",
        "com.au",
        "net.au",
        "org.au",
        "co.nz",
        "co.jp",
        "com.br",
        "com.mx",
        "co.za",
    }
)


def _normalise_domain(value: str) -> str:
    return value.lower().strip().strip(".")


def _normalise_service_token(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _service_name_candidates_from_domain(domain: str) -> list[str]:
    labels = [p for p in _normalise_domain(domain).split(".") if p]
    if not labels:
        return []

    if len(labels) == 1:
        token = _normalise_service_token(labels[0])
        return [token] if token else []

    suffix = ".".join(labels[-2:])
    if len(labels) >= 3 and suffix in _MULTIPART_PUBLIC_SUFFIXES:
        root_label = labels[-3]
        subdomain_labels = labels[:-3]
    else:
        root_label = labels[-2]
        subdomain_labels = labels[:-2]

    ordered_raw: list[str] = [root_label]
    for label in reversed(subdomain_labels):
        if label not in _GENERIC_SUBDOMAIN_LABELS:
            ordered_raw.append(label)

    out: list[str] = []
    seen: set[str] = set()
    for raw in ordered_raw:
        token = _normalise_service_token(raw)
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return out


class ServiceRegistryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._active_cache: list[ServiceRegistry] | None = None

    async def get_by_name(self, service_name: str) -> ServiceRegistry | None:
        result = await self.session.execute(
            select(ServiceRegistry).where(
                ServiceRegistry.service_name == service_name,
                ServiceRegistry.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_all_active(self) -> list[ServiceRegistry]:
        if self._active_cache is not None:
            return self._active_cache
        result = await self.session.execute(
            select(ServiceRegistry).where(ServiceRegistry.is_active.is_(True))
        )
        rows = list(result.scalars().all())
        self._active_cache = rows
        return rows

    async def find_by_domain(self, domain: str) -> ServiceRegistry | None:
        """
        Find a registry service by sender domain using layered matching:
        1) exact domain in common_domains (fast SQL path),
        2) subdomain suffix match in memory (e.g. mail.foo.com -> foo.com),
        3) service_name token match from domain labels (e.g. secure.foo.com -> foo).
        """
        domain = _normalise_domain(domain)
        if not domain:
            return None

        # Fast exact-match path
        result = await self.session.execute(
            select(ServiceRegistry).where(
                ServiceRegistry.common_domains.contains(
                    cast([domain], ARRAY(SAString))
                ),
                ServiceRegistry.is_active.is_(True),
            )
        )
        exact = result.scalars().first()
        if exact is not None:
            return exact

        services = await self.get_all_active()

        # Best suffix match wins (longest matching common domain)
        best_suffix_match: ServiceRegistry | None = None
        best_suffix_len = -1
        for entry in services:
            for common_domain in entry.common_domains:
                candidate = _normalise_domain(common_domain)
                if not candidate:
                    continue
                if domain == candidate or domain.endswith(f".{candidate}"):
                    if len(candidate) > best_suffix_len:
                        best_suffix_match = entry
                        best_suffix_len = len(candidate)
        if best_suffix_match is not None:
            return best_suffix_match

        # Domain-token fallback for partially-obscured sender domains
        service_map = {s.service_name: s for s in services}
        for candidate_name in _service_name_candidates_from_domain(domain):
            token_match = service_map.get(candidate_name)
            if token_match is not None:
                return token_match

        return None
