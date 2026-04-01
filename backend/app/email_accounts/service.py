# backend/app/email_accounts/service.py
"""
AccountDiscoveryService — classifies parsed emails into DiscoveredAccountDraft objects.

Design rules:
- No HTTP calls (provider boundary).
- No direct DB access (uses ServiceRegistryRepository via injected session).
- Classifies by subject-line regex AND sender-domain lookup against ServiceRegistry.
- Unknown domains produce an "other" entry so nothing is silently dropped.
"""

import re

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.email_accounts import DiscoveredAccountSourceType
from backend.app.db.repositories.service_registry import ServiceRegistryRepository
from backend.app.email_accounts.schemas import DiscoveredAccountDraft
from backend.app.providers.tools.mbox_parser.models import ParsedEmail

# ---------------------------------------------------------------------------
# Subject-line classification patterns (order matters — first match wins)
# ---------------------------------------------------------------------------
_SUBJECT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"(verify|confirm|activate|complete|validate).{0,30}(account|email|sign.?up|registr)",
            re.IGNORECASE,
        ),
        DiscoveredAccountSourceType.ACCOUNT_CONFIRMATION,
    ),
    (
        re.compile(
            r"(welcome to|thanks for (joining|signing up|creating|registering))",
            re.IGNORECASE,
        ),
        DiscoveredAccountSourceType.ACCOUNT_CONFIRMATION,
    ),
    (
        re.compile(
            r"(reset|change|forgot|recover).{0,20}password",
            re.IGNORECASE,
        ),
        DiscoveredAccountSourceType.PASSWORD_RESET,
    ),
    (
        re.compile(
            r"(receipt|order confirm|invoice|your (purchase|order)|payment "
            r"(confirm|receipt))",
            re.IGNORECASE,
        ),
        DiscoveredAccountSourceType.RECEIPT,
    ),
    (
        re.compile(
            r"(security (alert|notice|warning)|unusual (sign.?in|activity|access)|"
            r"new (device|login|sign.?in)|suspicious)",
            re.IGNORECASE,
        ),
        DiscoveredAccountSourceType.SECURITY_ALERT,
    ),
    (
        re.compile(
            r"(unsubscribe|newsletter|digest|weekly|monthly|update from)",
            re.IGNORECASE,
        ),
        DiscoveredAccountSourceType.NEWSLETTER,
    ),
]

# Domains that are generic email providers or system senders — skip these
_SKIP_DOMAINS: frozenset[str] = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "yahoo.com",
        "yahoo.co.uk",
        "outlook.com",
        "hotmail.com",
        "live.com",
        "msn.com",
        "icloud.com",
        "me.com",
        "mac.com",
        "protonmail.com",
        "proton.me",
        "fastmail.com",
        "hey.com",
        "tutanota.com",
        "zoho.com",
        "aol.com",
        # Transactional / ESP domains — not services themselves
        "sendgrid.net",
        "mailgun.org",
        "amazonses.com",
        "bounce.com",
        "noreply.com",
        "mailer.com",
    }
)


def _classify_subject(subject: str | None) -> str:
    if not subject:
        return DiscoveredAccountSourceType.OTHER
    for pattern, source_type in _SUBJECT_PATTERNS:
        if pattern.search(subject):
            return source_type
    return DiscoveredAccountSourceType.OTHER


class AccountDiscoveryService:
    """
    Stateless classification layer between the parser provider and the DB.
    Must be instantiated with an AsyncSession so it can query ServiceRegistry.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._registry = ServiceRegistryRepository(session)

    async def classify_emails(
        self,
        emails: list[ParsedEmail],
        recipient_email: str,
    ) -> list[DiscoveredAccountDraft]:
        """
        Turn a list of ParsedEmail into DiscoveredAccountDraft objects.

        - Skips generic email-provider domains.
        - Looks up sender domain in ServiceRegistry for curated display name + URLs.
        - Falls back to a domain-derived name when no registry entry exists.
        - Only emits drafts for messages that look account-related.
        """
        drafts: list[DiscoveredAccountDraft] = []

        for msg in emails:
            domain = msg.sender_domain
            if not domain or domain in _SKIP_DOMAINS:
                continue

            source_type = _classify_subject(msg.subject)

            # Only carry forward messages that look account-related
            if source_type == DiscoveredAccountSourceType.OTHER:
                if source_type == DiscoveredAccountSourceType.NEWSLETTER:
                    # Newsletters are not account evidence — skip
                    continue
                # Generic "other" — keep only if we have a registry match
                registry_entry = await self._registry.find_by_domain(domain)
                if registry_entry is None:
                    continue
            else:
                registry_entry = await self._registry.find_by_domain(domain)

            if registry_entry is not None:
                service_name = registry_entry.service_name
                display_name = registry_entry.display_name
                login_url = registry_entry.login_url
                password_reset_url = registry_entry.password_reset_url
            else:
                # Derive a service name from the domain, for example
                # "example.com" -> "example.com".
                service_name = domain
                display_name = domain
                login_url = None
                password_reset_url = None

            drafts.append(
                DiscoveredAccountDraft(
                    service_name=service_name,
                    display_name=display_name,
                    email_used=recipient_email,
                    source_type=source_type,
                    sender_domain=domain,
                    login_url=login_url,
                    password_reset_url=password_reset_url,
                    first_seen_at=msg.date,
                    last_seen_at=msg.date,
                    email_count=1,
                )
            )

        return drafts
