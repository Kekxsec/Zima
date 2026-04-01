# Phase 3 — Service Discovery Service + Seed Data

## Goal
Two deliverables:
1. `AccountDiscoveryService` — classifies emails, matches services, resolves URLs, deduplicates into `DiscoveredAccountDraft` objects ready for persistence
2. `scripts/seed_service_registry.py` — populates the `service_registry` table with ~60 common services

---

## Files to Create

### 1. `backend/app/email_accounts/__init__.py`
Empty.

### 2. `backend/app/email_accounts/schemas.py`

Internal transfer objects (not API schemas).

```python
# backend/app/email_accounts/schemas.py
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class DiscoveredAccountDraft(BaseModel):
    """
    Intermediate object produced by AccountDiscoveryService.
    Passed to the module/repository layer for persistence and signal emission.
    Not stored in DB directly.
    """
    service_name: str          # normalised key, e.g. "github"
    display_name: str          # human-readable, e.g. "GitHub"
    email_used: str
    source_type: str           # DiscoveredAccountSourceType value
    sender_domain: str
    login_url: str | None
    password_reset_url: str | None
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    email_count: int
```

### 3. `backend/app/email_accounts/service.py`

```python
# backend/app/email_accounts/service.py
from __future__ import annotations

import re
from collections import defaultdict

from backend.app.core.logging import get_logger
from backend.app.db.models.email_accounts import (
    DiscoveredAccountSourceType,
    ServiceRegistry,
)
from backend.app.email_accounts.schemas import DiscoveredAccountDraft
from backend.app.providers.tools.mbox_parser.models import ParsedEmail

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Subject-line classification patterns
# Order matters — more specific patterns first
# ---------------------------------------------------------------------------
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        DiscoveredAccountSourceType.ACCOUNT_CONFIRMATION,
        re.compile(
            r"(confirm|verify|activate|welcome|account created|registration|"
            r"you've (successfully )?signed up|thank you for (joining|registering|creating))",
            re.IGNORECASE,
        ),
    ),
    (
        DiscoveredAccountSourceType.PASSWORD_RESET,
        re.compile(
            r"(password reset|reset your password|forgot password|change your password|"
            r"password change request)",
            re.IGNORECASE,
        ),
    ),
    (
        DiscoveredAccountSourceType.RECEIPT,
        re.compile(
            r"(receipt|invoice|order confirmation|payment|your (order|purchase|subscription)|"
            r"billing statement|charge)",
            re.IGNORECASE,
        ),
    ),
    (
        DiscoveredAccountSourceType.SECURITY_ALERT,
        re.compile(
            r"(security alert|unusual (sign-?in|activity|login)|new (device|location|login)|"
            r"suspicious activity|we noticed a (sign-?in|login))",
            re.IGNORECASE,
        ),
    ),
    (
        DiscoveredAccountSourceType.NEWSLETTER,
        re.compile(
            r"(newsletter|unsubscribe|digest|weekly|monthly|update from|latest from)",
            re.IGNORECASE,
        ),
    ),
]

# Domains to always skip — system mail, internal routing, anti-spam
_SKIP_DOMAINS: frozenset[str] = frozenset(
    {
        "localhost",
        "example.com",
        "mailer-daemon.example",
        "noreply.invalid",
        "bounce.invalid",
        "postmaster.example",
    }
)

# Sender local-parts that indicate automated/transactional mail (not user accounts)
_SKIP_LOCAL_PARTS: frozenset[str] = frozenset(
    {
        "mailer-daemon",
        "postmaster",
        "abuse",
        "noc",
        "daemon",
        "root",
        "MAILER-DAEMON",
    }
)


def _classify_source_type(subject: str) -> str:
    """Return the most likely DiscoveredAccountSourceType for a given subject line."""
    for source_type, pattern in _PATTERNS:
        if pattern.search(subject):
            return source_type
    return DiscoveredAccountSourceType.OTHER


def _local_part(address: str) -> str:
    """Returns the part before @ in lower case."""
    at = address.find("@")
    if at == -1:
        return address.lower()
    return address[:at].lower()


def _should_skip(email: ParsedEmail) -> bool:
    """Return True for addresses that are clearly not service accounts."""
    if email.sender_domain in _SKIP_DOMAINS:
        return True
    if _local_part(email.sender_address) in _SKIP_LOCAL_PARTS:
        return True
    return False


class AccountDiscoveryService:
    """
    Pure business logic layer — no DB access, no HTTP.

    Takes a list of ParsedEmail (from MboxParserProvider) and a ServiceRegistry
    lookup table (loaded once by the caller), and returns deduplicated
    DiscoveredAccountDraft objects.

    Dependency: receives registry as a parameter — no DB session here.
    """

    def __init__(self, registry: list[ServiceRegistry]) -> None:
        # Build domain → registry lookup once
        self._domain_map: dict[str, ServiceRegistry] = {}
        for entry in registry:
            for domain in entry.common_domains:
                self._domain_map[domain.lower()] = entry

    def process(
        self,
        emails: list[ParsedEmail],
        recipient_email: str,
    ) -> list[DiscoveredAccountDraft]:
        """
        Main entry point.

        Args:
            emails: parsed emails from MboxParserProvider
            recipient_email: the email address the mbox belongs to (the user's own address)

        Returns:
            Deduplicated list of DiscoveredAccountDraft, one per (service_name, email_used).
        """
        # Group emails by (service_name, email_used)
        # Key: (service_name, email_used)
        groups: dict[tuple[str, str], list[ParsedEmail]] = defaultdict(list)

        for em in emails:
            if _should_skip(em):
                continue

            # Only process emails received by the user (sender ≠ user)
            if em.sender_address == recipient_email.lower():
                continue

            registry_entry = self._domain_map.get(em.sender_domain)
            if registry_entry:
                service_name = registry_entry.service_name
            else:
                # Unknown service — use domain as service_name, normalised
                service_name = em.sender_domain.replace(".", "_").replace("-", "_")

            groups[(service_name, recipient_email.lower())].append(em)

        drafts: list[DiscoveredAccountDraft] = []
        for (service_name, email_used), group in groups.items():
            drafts.append(self._build_draft(service_name, email_used, group))

        logger.info(
            "account_discovery.processed",
            input_emails=len(emails),
            unique_services=len(drafts),
        )
        return drafts

    def _build_draft(
        self,
        service_name: str,
        email_used: str,
        emails: list[ParsedEmail],
    ) -> DiscoveredAccountDraft:
        registry_entry = self._get_registry_entry(service_name)

        # Pick the most informative source_type from all subjects in the group
        source_type = self._dominant_source_type(emails)

        # Date range
        dates = [e.date for e in emails if e.date is not None]
        first_seen = min(dates) if dates else None
        last_seen = max(dates) if dates else None

        # Representative domain
        sender_domain = emails[0].sender_domain

        return DiscoveredAccountDraft(
            service_name=service_name,
            display_name=registry_entry.display_name if registry_entry else _make_display_name(sender_domain),
            email_used=email_used,
            source_type=source_type,
            sender_domain=sender_domain,
            login_url=registry_entry.login_url if registry_entry else None,
            password_reset_url=registry_entry.password_reset_url if registry_entry else None,
            first_seen_at=first_seen,
            last_seen_at=last_seen,
            email_count=len(emails),
        )

    def _get_registry_entry(self, service_name: str) -> ServiceRegistry | None:
        # Registry entries are keyed by service_name
        for entry in self._domain_map.values():
            if entry.service_name == service_name:
                return entry
        return None

    @staticmethod
    def _dominant_source_type(emails: list[ParsedEmail]) -> str:
        """
        Priority order: account_confirmation > password_reset > security_alert > receipt > newsletter > other.
        Returns the highest-priority source_type found in the group.
        """
        priority = [
            DiscoveredAccountSourceType.ACCOUNT_CONFIRMATION,
            DiscoveredAccountSourceType.PASSWORD_RESET,
            DiscoveredAccountSourceType.SECURITY_ALERT,
            DiscoveredAccountSourceType.RECEIPT,
            DiscoveredAccountSourceType.NEWSLETTER,
            DiscoveredAccountSourceType.OTHER,
        ]
        found: set[str] = {_classify_source_type(e.subject) for e in emails}
        for p in priority:
            if p in found:
                return p
        return DiscoveredAccountSourceType.OTHER


def _make_display_name(domain: str) -> str:
    """Convert a domain like 'mail.example.co.uk' into 'Example'."""
    # Strip common prefixes
    for prefix in ("mail.", "email.", "noreply.", "no-reply.", "notifications.", "info."):
        if domain.startswith(prefix):
            domain = domain[len(prefix):]
    # Take SLD
    parts = domain.split(".")
    return parts[0].replace("-", " ").replace("_", " ").title()
```

---

### 4. `scripts/seed_service_registry.py`

This is a standalone script — run once to populate the `service_registry` table. It uses sync SQLAlchemy (migration/seed context, not async).

```python
# scripts/seed_service_registry.py
"""
Seed the service_registry table with common services.
Run: python scripts/seed_service_registry.py
Requires DATABASE_URL_SYNC to be set in .env
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from backend.app.db.models.email_accounts import ServiceRegistry

SERVICES: list[dict] = [
    # --- Dev & Code ---
    {"service_name": "github", "display_name": "GitHub", "category": "code",
     "common_domains": ["github.com"], "login_url": "https://github.com/login", "password_reset_url": "https://github.com/password_reset"},
    {"service_name": "gitlab", "display_name": "GitLab", "category": "code",
     "common_domains": ["gitlab.com"], "login_url": "https://gitlab.com/users/sign_in", "password_reset_url": "https://gitlab.com/users/password/new"},
    {"service_name": "bitbucket", "display_name": "Bitbucket", "category": "code",
     "common_domains": ["bitbucket.org"], "login_url": "https://bitbucket.org/account/signin/", "password_reset_url": "https://bitbucket.org/account/password/reset/"},
    {"service_name": "npm", "display_name": "npm", "category": "code",
     "common_domains": ["npmjs.com"], "login_url": "https://www.npmjs.com/login", "password_reset_url": "https://www.npmjs.com/forgot"},
    {"service_name": "vercel", "display_name": "Vercel", "category": "code",
     "common_domains": ["vercel.com"], "login_url": "https://vercel.com/login", "password_reset_url": "https://vercel.com/account/login?next=/login"},

    # --- Cloud ---
    {"service_name": "aws", "display_name": "Amazon Web Services", "category": "cloud",
     "common_domains": ["aws.amazon.com", "amazon.com"], "login_url": "https://signin.aws.amazon.com/", "password_reset_url": "https://www.amazon.com/ap/forgotpassword"},
    {"service_name": "gcp", "display_name": "Google Cloud", "category": "cloud",
     "common_domains": ["google.com", "accounts.google.com"], "login_url": "https://console.cloud.google.com/", "password_reset_url": "https://accounts.google.com/signin/recovery"},
    {"service_name": "azure", "display_name": "Microsoft Azure", "category": "cloud",
     "common_domains": ["microsoft.com", "azure.com"], "login_url": "https://portal.azure.com/", "password_reset_url": "https://account.live.com/password/reset"},
    {"service_name": "digitalocean", "display_name": "DigitalOcean", "category": "cloud",
     "common_domains": ["digitalocean.com"], "login_url": "https://cloud.digitalocean.com/login", "password_reset_url": "https://cloud.digitalocean.com/forgot_password"},
    {"service_name": "railway", "display_name": "Railway", "category": "cloud",
     "common_domains": ["railway.app"], "login_url": "https://railway.app/login", "password_reset_url": "https://railway.app/login"},

    # --- Email ---
    {"service_name": "gmail", "display_name": "Gmail", "category": "email",
     "common_domains": ["gmail.com", "googlemail.com"], "login_url": "https://mail.google.com/", "password_reset_url": "https://accounts.google.com/signin/recovery"},
    {"service_name": "outlook", "display_name": "Outlook / Hotmail", "category": "email",
     "common_domains": ["outlook.com", "hotmail.com", "live.com"], "login_url": "https://outlook.live.com/", "password_reset_url": "https://account.live.com/password/reset"},
    {"service_name": "protonmail", "display_name": "Proton Mail", "category": "email",
     "common_domains": ["proton.me", "protonmail.com"], "login_url": "https://account.proton.me/login", "password_reset_url": "https://account.proton.me/reset-password"},
    {"service_name": "fastmail", "display_name": "Fastmail", "category": "email",
     "common_domains": ["fastmail.com", "fastmail.fm"], "login_url": "https://www.fastmail.com/", "password_reset_url": "https://www.fastmail.com/reset/"},

    # --- Social ---
    {"service_name": "twitter", "display_name": "X / Twitter", "category": "social",
     "common_domains": ["twitter.com", "x.com"], "login_url": "https://x.com/login", "password_reset_url": "https://x.com/account/begin_password_reset"},
    {"service_name": "linkedin", "display_name": "LinkedIn", "category": "social",
     "common_domains": ["linkedin.com"], "login_url": "https://www.linkedin.com/login", "password_reset_url": "https://www.linkedin.com/uas/request-password-reset"},
    {"service_name": "facebook", "display_name": "Facebook", "category": "social",
     "common_domains": ["facebook.com", "facebookmail.com"], "login_url": "https://www.facebook.com/", "password_reset_url": "https://www.facebook.com/login/identify"},
    {"service_name": "instagram", "display_name": "Instagram", "category": "social",
     "common_domains": ["instagram.com"], "login_url": "https://www.instagram.com/accounts/login/", "password_reset_url": "https://www.instagram.com/accounts/password/reset/"},
    {"service_name": "reddit", "display_name": "Reddit", "category": "social",
     "common_domains": ["reddit.com"], "login_url": "https://www.reddit.com/login/", "password_reset_url": "https://www.reddit.com/password"},
    {"service_name": "discord", "display_name": "Discord", "category": "social",
     "common_domains": ["discord.com"], "login_url": "https://discord.com/login", "password_reset_url": "https://discord.com/reset"},

    # --- Payments ---
    {"service_name": "stripe", "display_name": "Stripe", "category": "payment",
     "common_domains": ["stripe.com"], "login_url": "https://dashboard.stripe.com/login", "password_reset_url": "https://dashboard.stripe.com/login"},
    {"service_name": "paypal", "display_name": "PayPal", "category": "payment",
     "common_domains": ["paypal.com"], "login_url": "https://www.paypal.com/signin", "password_reset_url": "https://www.paypal.com/authflow/password-recovery"},
    {"service_name": "wise", "display_name": "Wise", "category": "payment",
     "common_domains": ["wise.com", "transferwise.com"], "login_url": "https://wise.com/login", "password_reset_url": "https://wise.com/lost-password"},

    # --- Shopping / E-commerce ---
    {"service_name": "amazon", "display_name": "Amazon", "category": "shopping",
     "common_domains": ["amazon.co.uk", "amazon.de", "amazon.fr"], "login_url": "https://www.amazon.com/ap/signin", "password_reset_url": "https://www.amazon.com/ap/forgotpassword"},
    {"service_name": "ebay", "display_name": "eBay", "category": "shopping",
     "common_domains": ["ebay.com", "ebay.co.uk"], "login_url": "https://signin.ebay.com/", "password_reset_url": "https://signin.ebay.com/ws/eBayISAPI.dll?ForgotPassword"},
    {"service_name": "shopify", "display_name": "Shopify", "category": "shopping",
     "common_domains": ["shopify.com"], "login_url": "https://accounts.shopify.com/lookup", "password_reset_url": "https://accounts.shopify.com/lookup"},

    # --- SaaS / Productivity ---
    {"service_name": "slack", "display_name": "Slack", "category": "productivity",
     "common_domains": ["slack.com"], "login_url": "https://slack.com/signin", "password_reset_url": "https://slack.com/forgot-password"},
    {"service_name": "notion", "display_name": "Notion", "category": "productivity",
     "common_domains": ["notion.so"], "login_url": "https://www.notion.so/login", "password_reset_url": "https://www.notion.so/login"},
    {"service_name": "atlassian", "display_name": "Atlassian (Jira/Confluence)", "category": "productivity",
     "common_domains": ["atlassian.com", "atlassian.net"], "login_url": "https://id.atlassian.com/login", "password_reset_url": "https://id.atlassian.com/forgot-password"},
    {"service_name": "dropbox", "display_name": "Dropbox", "category": "productivity",
     "common_domains": ["dropbox.com"], "login_url": "https://www.dropbox.com/login", "password_reset_url": "https://www.dropbox.com/forgot"},
    {"service_name": "zoom", "display_name": "Zoom", "category": "productivity",
     "common_domains": ["zoom.us"], "login_url": "https://zoom.us/signin", "password_reset_url": "https://zoom.us/forgot_password"},
    {"service_name": "hubspot", "display_name": "HubSpot", "category": "productivity",
     "common_domains": ["hubspot.com"], "login_url": "https://app.hubspot.com/login", "password_reset_url": "https://app.hubspot.com/login"},
    {"service_name": "mailchimp", "display_name": "Mailchimp", "category": "marketing",
     "common_domains": ["mailchimp.com"], "login_url": "https://login.mailchimp.com/", "password_reset_url": "https://login.mailchimp.com/forgot/"},
    {"service_name": "twilio", "display_name": "Twilio", "category": "developer",
     "common_domains": ["twilio.com"], "login_url": "https://console.twilio.com/", "password_reset_url": "https://www.twilio.com/login#forgot-password"},

    # --- Security / Identity ---
    {"service_name": "1password", "display_name": "1Password", "category": "security",
     "common_domains": ["1password.com"], "login_url": "https://my.1password.com/", "password_reset_url": "https://my.1password.com/"},
    {"service_name": "lastpass", "display_name": "LastPass", "category": "security",
     "common_domains": ["lastpass.com"], "login_url": "https://lastpass.com/", "password_reset_url": "https://lastpass.com/recover.php"},
    {"service_name": "bitwarden", "display_name": "Bitwarden", "category": "security",
     "common_domains": ["bitwarden.com"], "login_url": "https://vault.bitwarden.com/", "password_reset_url": "https://vault.bitwarden.com/#/recover-2fa"},
    {"service_name": "okta", "display_name": "Okta", "category": "security",
     "common_domains": ["okta.com"], "login_url": "https://login.okta.com/", "password_reset_url": "https://login.okta.com/"},

    # --- Finance ---
    {"service_name": "revolut", "display_name": "Revolut", "category": "finance",
     "common_domains": ["revolut.com"], "login_url": "https://app.revolut.com/start", "password_reset_url": "https://app.revolut.com/start"},
    {"service_name": "monzo", "display_name": "Monzo", "category": "finance",
     "common_domains": ["monzo.com"], "login_url": "https://monzo.com/i/login/", "password_reset_url": "https://monzo.com/help/"},
    {"service_name": "coinbase", "display_name": "Coinbase", "category": "finance",
     "common_domains": ["coinbase.com"], "login_url": "https://www.coinbase.com/signin", "password_reset_url": "https://www.coinbase.com/forgot-password"},

    # --- Streaming / Entertainment ---
    {"service_name": "netflix", "display_name": "Netflix", "category": "entertainment",
     "common_domains": ["netflix.com"], "login_url": "https://www.netflix.com/login", "password_reset_url": "https://www.netflix.com/LoginHelp"},
    {"service_name": "spotify", "display_name": "Spotify", "category": "entertainment",
     "common_domains": ["spotify.com"], "login_url": "https://accounts.spotify.com/login", "password_reset_url": "https://accounts.spotify.com/en/password-reset"},
    {"service_name": "apple", "display_name": "Apple", "category": "entertainment",
     "common_domains": ["apple.com", "icloud.com"], "login_url": "https://appleid.apple.com/", "password_reset_url": "https://iforgot.apple.com/"},

    # --- AI / Developer Tools ---
    {"service_name": "openai", "display_name": "OpenAI", "category": "ai",
     "common_domains": ["openai.com"], "login_url": "https://auth.openai.com/", "password_reset_url": "https://auth.openai.com/"},
    {"service_name": "anthropic", "display_name": "Anthropic / Claude", "category": "ai",
     "common_domains": ["anthropic.com", "claude.ai"], "login_url": "https://claude.ai/login", "password_reset_url": "https://claude.ai/login"},
]


def main() -> None:
    db_url = os.environ.get("DATABASE_URL_SYNC")
    if not db_url:
        print("ERROR: DATABASE_URL_SYNC not set")
        sys.exit(1)

    engine = create_engine(db_url)
    with Session(engine) as session:
        inserted = 0
        skipped = 0
        for svc in SERVICES:
            existing = session.execute(
                text("SELECT id FROM service_registry WHERE service_name = :name"),
                {"name": svc["service_name"]},
            ).fetchone()
            if existing:
                skipped += 1
                continue

            session.add(
                ServiceRegistry(
                    id=uuid.uuid4(),
                    **svc,
                )
            )
            inserted += 1

        session.commit()
        print(f"Done. Inserted: {inserted}, Skipped (already exist): {skipped}")


if __name__ == "__main__":
    main()
```

---

## Checklist
- [ ] `backend/app/email_accounts/__init__.py`
- [ ] `backend/app/email_accounts/schemas.py` — `DiscoveredAccountDraft`
- [ ] `backend/app/email_accounts/service.py` — `AccountDiscoveryService` with `process()`
- [ ] `scripts/seed_service_registry.py` — ~50 services seeded
- [ ] No DB session access in `AccountDiscoveryService` (registry passed in as param)
- [ ] No HTTP calls in `AccountDiscoveryService`
- [ ] Passes mypy

## Dependencies
- Phase 1 (for `ServiceRegistry` model import in type hints)
- Phase 2 (for `ParsedEmail` import)

## Validation
```python
registry = [...]  # list of ServiceRegistry from DB
service = AccountDiscoveryService(registry=registry)
drafts = service.process(emails=parsed_emails, recipient_email="user@example.com")
assert all(isinstance(d, DiscoveredAccountDraft) for d in drafts)
```
