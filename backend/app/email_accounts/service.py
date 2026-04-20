# backend/app/email_accounts/service.py
"""
AccountDiscoveryService — classifies parsed emails into DiscoveredAccountDraft objects.

Design rules:
- No HTTP calls (provider boundary).
- No direct DB access (uses ServiceRegistryRepository via injected session).
- Pre-aggregates by sender_domain before classifying — one draft per domain.
- Confidence score is derived from message count, best source type seen, and
  ServiceRegistry presence. Low-signal domains (single RECEIPT, single OTHER)
  are capped or skipped entirely to reduce noise.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.email_accounts import DiscoveredAccountSourceType
from backend.app.db.repositories.service_registry import ServiceRegistryRepository
from backend.app.email_accounts.schemas import DiscoveredAccountDraft
from backend.app.providers.tools.mbox_parser.models import ParsedEmail

# ---------------------------------------------------------------------------
# Known email alias / forwarding service domains.
# When sender_domain matches one of these (or is a subdomain of one),
# the real service identity is recovered from forwarding headers or subject.
# ---------------------------------------------------------------------------
_ALIAS_SERVICE_DOMAINS: frozenset[str] = frozenset(
    {
        "passmail.net",
        "passmail.com",
        "simplelogin.co",
        "simplelogin.com",
        "anonaddy.com",
        "anonaddy.me",
        "relay.firefox.com",
        "mozmail.com",
        "duckduckgo.com",  # DuckDuckGo email protection
        "duck.com",
        "addy.io",
        "forwardemail.net",
        "improvmx.com",
        "33mail.com",
        "spamgourmet.com",
    }
)

# ---------------------------------------------------------------------------
# Subject-line service-name extraction.
# Captures the service name from common transactional subject patterns.
# Returns None when no confident match is found.
# ---------------------------------------------------------------------------
_SUBJECT_SERVICE_PATTERNS: list[re.Pattern[str]] = [
    # "Welcome to Netflix" / "Welcome to the Netflix family"
    re.compile(
        r"welcome to (?:the )?([A-Za-z0-9][\w\s&'.,-]{1,40}?)(?:\s+family|\s+community|[!,.]|$)",
        re.IGNORECASE,
    ),
    # "Your Netflix account" / "Your account at Netflix"
    re.compile(
        r"your (?:account (?:at|with|on) |account (?:has been )?)?([A-Za-z0-9][\w\s&'.,-]{1,40}?) account",
        re.IGNORECASE,
    ),
    # "Verify your Spotify account" / "Confirm your Dropbox email"
    re.compile(
        r"(?:verify|confirm|activate|validate) (?:your )?([A-Za-z0-9][\w\s&'.,-]{1,40}?) (?:account|email|address)",
        re.IGNORECASE,
    ),
    # "Thanks for joining GitHub" / "Thanks for signing up for Figma"
    re.compile(
        r"thanks for (?:joining|signing up (?:for|to|with)) ([A-Za-z0-9][\w\s&'.,-]{1,40})(?:[!,.]|$)",
        re.IGNORECASE,
    ),
    # "Order from Amazon" / "Receipt from Etsy"
    re.compile(
        r"(?:order|receipt|invoice) from ([A-Za-z0-9][\w\s&'.,-]{1,40})(?:[!,.]|$)",
        re.IGNORECASE,
    ),
    # "Your Amazon order" / "Your Stripe invoice"
    re.compile(
        r"your ([A-Za-z0-9][\w\s&'.,-]{1,30}) (?:order|invoice|receipt|subscription|purchase)",
        re.IGNORECASE,
    ),
]

# Words that indicate the capture is a generic phrase, not a service name
_SUBJECT_EXTRACTION_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "your",
        "my",
        "our",
        "email",
        "password",
        "account",
        "service",
        "subscription",
        "order",
        "invoice",
        "receipt",
        "payment",
        "new",
        "recent",
        "security",
        "login",
        "sign",
        "access",
        "request",
        "update",
        "change",
        "alert",
        "notice",
        "notification",
        "message",
        "team",
        "support",
        "help",
    }
)

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


def _is_alias_domain(domain: str) -> bool:
    """Return True when domain is a known alias/forwarding service (including subdomains)."""
    if domain in _ALIAS_SERVICE_DOMAINS:
        return True
    for alias_root in _ALIAS_SERVICE_DOMAINS:
        if domain.endswith(f".{alias_root}"):
            return True
    return False


def _resolve_alias_domain(msg: ParsedEmail) -> str | None:
    """
    Given a ParsedEmail whose sender_domain belongs to an alias service,
    return the best-guess real sender domain, or None if unresolvable.

    Resolution order:
    1. x_original_from — explicit header set by most alias providers
    2. reply_to — alias providers often set Reply-To to the original sender
    3. Subdomain local-part — e.g. netflix.passmail.net → "netflix" (not a domain,
       but used downstream to drive subject-based name extraction)
    """
    # 1. x_original_from header
    if msg.x_original_from and "@" in msg.x_original_from:
        domain = msg.x_original_from.split("@", 1)[1].lower().strip()
        if domain and not _is_alias_domain(domain):
            return domain

    # 2. reply_to address
    if msg.reply_to and "@" in msg.reply_to:
        domain = msg.reply_to.split("@", 1)[1].lower().strip()
        if domain and not _is_alias_domain(domain) and domain not in _SKIP_DOMAINS:
            return domain

    # 3. Subdomain hint: e.g. netflix.passmail.net → "netflix" returned as bare label
    if msg.sender_domain:
        parts = msg.sender_domain.split(".")
        for alias_root in _ALIAS_SERVICE_DOMAINS:
            root_parts = alias_root.split(".")
            if len(parts) > len(root_parts):
                # subdomain prefix before the alias root
                prefix = ".".join(parts[: len(parts) - len(root_parts)])
                if prefix and "." not in prefix:
                    return prefix  # bare label, not a real domain

    return None


def _extract_service_name_from_subject(subject: str) -> str | None:
    """
    Try to extract a human-readable service name from a subject line.
    Returns None when no confident match is found.
    """
    for pattern in _SUBJECT_SERVICE_PATTERNS:
        m = pattern.search(subject)
        if not m:
            continue
        candidate = m.group(1).strip().rstrip(".,!;:")
        words = candidate.lower().split()
        if not words:
            continue
        # Reject single stopword captures
        if len(words) == 1 and words[0] in _SUBJECT_EXTRACTION_STOPWORDS:
            continue
        # Reject generic phrases like "your account" or "security update"
        if all(word in _SUBJECT_EXTRACTION_STOPWORDS for word in words):
            continue
        # Reject implausibly long matches (probably a sentence fragment)
        if len(candidate) > 40:
            continue
        return candidate.title()
    return None


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

# Source-type weights used in confidence scoring — higher = stronger account signal
_SOURCE_TYPE_WEIGHT: dict[str, int] = {
    DiscoveredAccountSourceType.ACCOUNT_CONFIRMATION: 60,
    DiscoveredAccountSourceType.SECURITY_ALERT: 50,
    DiscoveredAccountSourceType.PASSWORD_RESET: 45,
    DiscoveredAccountSourceType.RECEIPT: 30,
    DiscoveredAccountSourceType.OTHER: 10,
    DiscoveredAccountSourceType.NEWSLETTER: 0,
}


def _classify_subject(subject: str | None) -> str:
    if not subject:
        return DiscoveredAccountSourceType.OTHER
    for pattern, source_type in _SUBJECT_PATTERNS:
        if pattern.search(subject):
            return source_type
    return DiscoveredAccountSourceType.OTHER


def _compute_confidence(
    best_source_type: str,
    message_count: int,
    in_registry: bool,
) -> int:
    base = _SOURCE_TYPE_WEIGHT.get(best_source_type, 10)
    frequency_bonus = min(message_count * 5, 25)
    registry_bonus = 15 if in_registry else 0
    return min(base + frequency_bonus + registry_bonus, 100)


class AccountDiscoveryService:
    """
    Stateless classification layer between the parser provider and the DB.
    Must be instantiated with an AsyncSession so it can query ServiceRegistry.

    classify_emails() pre-aggregates by sender_domain before classifying so
    that confidence scoring can account for message frequency. One
    DiscoveredAccountDraft is emitted per domain.
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
        - Groups messages by sender_domain first so frequency informs confidence.
        - Skips domains where the only evidence is a single RECEIPT or OTHER email.
        - Looks up sender domain in ServiceRegistry for curated display name + URLs.
        - Falls back to domain-derived name when no registry entry exists.
        """
        # --- Group by effective sender domain ---
        # For alias-service emails, resolve the real sender before grouping so
        # that e.g. all Netflix emails forwarded via passmail collapse into one
        # "netflix.com" group rather than appearing as a "passmail.net" account.
        domain_groups: dict[str, list[ParsedEmail]] = defaultdict(list)
        for msg in emails:
            domain = msg.sender_domain
            if not domain:
                continue
            if _is_alias_domain(domain):
                resolved = _resolve_alias_domain(msg)
                if not resolved:
                    # Can't identify real sender — skip rather than create noise
                    continue
                domain = resolved
            if domain in _SKIP_DOMAINS:
                continue
            domain_groups[domain].append(msg)

        drafts: list[DiscoveredAccountDraft] = []

        for domain, messages in domain_groups.items():
            # Classify every message and pick the best (highest-weight) source type
            source_types_seen: list[str] = []
            for msg in messages:
                st = _classify_subject(msg.subject)
                # Newsletters are filtered by the pre-pass — drop any that slip through
                if st == DiscoveredAccountSourceType.NEWSLETTER:
                    continue
                source_types_seen.append(st)

            if not source_types_seen:
                continue

            best_source_type = max(
                source_types_seen,
                key=lambda st: _SOURCE_TYPE_WEIGHT.get(st, 0),
            )

            message_count = len(messages)

            # domain may be a bare subdomain label (e.g. "netflix") when we could
            # only recover a prefix from the alias address, not a real domain.
            is_bare_label = "." not in domain

            # find_by_domain() includes exact, suffix, and token heuristics.
            registry_entry = await self._registry.find_by_domain(domain)
            in_registry = registry_entry is not None

            # Skip weak single-message domains with no strong account signal,
            # but always keep curated registry entries regardless of message count.
            if (
                not in_registry
                and message_count == 1
                and best_source_type
                in (
                    DiscoveredAccountSourceType.OTHER,
                    DiscoveredAccountSourceType.RECEIPT,
                )
            ):
                continue

            if in_registry and registry_entry is not None:
                service_name = registry_entry.service_name
                display_name = registry_entry.display_name
                login_url = registry_entry.login_url
                password_reset_url = registry_entry.password_reset_url
            else:
                # Try to extract a human-readable name from subject lines
                subject_name: str | None = None
                for msg in messages:
                    if msg.subject:
                        subject_name = _extract_service_name_from_subject(msg.subject)
                        if subject_name:
                            break

                if subject_name:
                    service_name = subject_name
                    display_name = subject_name
                elif is_bare_label:
                    service_name = domain.capitalize()
                    display_name = domain.capitalize()
                else:
                    service_name = domain
                    display_name = domain
                login_url = None
                password_reset_url = None

            confidence_score = _compute_confidence(
                best_source_type, message_count, in_registry
            )

            # Aggregate timestamps and unsubscribe URL (keep first non-null)
            dates: list[datetime] = [m.date for m in messages if m.date is not None]
            first_seen_at = min(dates) if dates else None
            last_seen_at = max(dates) if dates else None
            unsubscribe_url: str | None = next(
                (m.list_unsubscribe for m in messages if m.list_unsubscribe), None
            )

            # Prefer the actual To: address so alias-based accounts show the
            # correct email rather than the upload's primary address.
            representative = messages[0]
            email_used = (
                representative.to_address
                if representative.to_address and "@" in representative.to_address
                else recipient_email
            )

            drafts.append(
                DiscoveredAccountDraft(
                    service_name=service_name,
                    display_name=display_name,
                    email_used=email_used,
                    source_type=best_source_type,
                    sender_domain=domain,
                    login_url=login_url,
                    password_reset_url=password_reset_url,
                    unsubscribe_url=unsubscribe_url,
                    first_seen_at=first_seen_at,
                    last_seen_at=last_seen_at,
                    email_count=message_count,
                    confidence_score=confidence_score,
                )
            )

        return drafts
