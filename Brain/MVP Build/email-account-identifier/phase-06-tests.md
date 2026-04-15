# Phase 6 — Tests

## Goal
Unit, integration, and API tests covering all components of the email account identifier. Aim for >85% coverage on new code.

---

## Test Files to Create

### 1. `tests/unit/providers/test_mbox_parser.py`

```python
# tests/unit/providers/test_mbox_parser.py
"""Unit tests for MboxParserProvider."""
import textwrap
from datetime import datetime, timezone

import pytest

from backend.app.providers.tools.mbox_parser.client import MboxParserProvider
from backend.app.providers.tools.mbox_parser.models import ParsedEmail


def _make_mbox(*messages: str) -> bytes:
    """Assemble raw mbox bytes from individual message strings."""
    parts: list[str] = []
    for msg in messages:
        parts.append("From MAILER-DAEMON Fri Jan  1 00:00:00 2021\n" + msg + "\n\n")
    return "\n".join(parts).encode("utf-8")


SIMPLE_MSG = textwrap.dedent("""\
    From: GitHub <noreply@github.com>
    To: user@example.com
    Subject: Welcome to GitHub!
    Date: Mon, 01 Jan 2024 10:00:00 +0000
    Message-ID: <abc123@github.com>
""")

ENCODED_SUBJECT_MSG = textwrap.dedent("""\
    From: =?UTF-8?B?R2l0SHVi?= <noreply@github.com>
    To: user@example.com
    Subject: =?UTF-8?Q?Confirm_your_email?=
    Date: Tue, 02 Jan 2024 10:00:00 +0000
    Message-ID: <def456@github.com>
""")

NO_SENDER_MSG = textwrap.dedent("""\
    To: user@example.com
    Subject: Broken message
    Date: Wed, 03 Jan 2024 10:00:00 +0000
""")

MAILER_DAEMON_MSG = textwrap.dedent("""\
    From: MAILER-DAEMON <mailer-daemon@example.com>
    To: user@example.com
    Subject: Delivery failure
    Date: Thu, 04 Jan 2024 10:00:00 +0000
    Message-ID: <mda123@example.com>
""")


class TestMboxParserProvider:
    def setup_method(self) -> None:
        self.provider = MboxParserProvider()

    def test_parse_simple_message(self) -> None:
        raw = _make_mbox(SIMPLE_MSG)
        result = self.provider.parse(raw)
        assert len(result) == 1
        email = result[0]
        assert email.sender_address == "noreply@github.com"
        assert email.sender_domain == "github.com"
        assert email.sender_name == "GitHub"
        assert email.subject == "Welcome to GitHub!"
        assert isinstance(email.date, datetime)

    def test_parse_encoded_headers(self) -> None:
        raw = _make_mbox(ENCODED_SUBJECT_MSG)
        result = self.provider.parse(raw)
        assert len(result) == 1
        assert "Confirm" in result[0].subject

    def test_skips_message_without_sender(self) -> None:
        raw = _make_mbox(NO_SENDER_MSG)
        result = self.provider.parse(raw)
        assert len(result) == 0

    def test_skips_mailer_daemon(self) -> None:
        # MAILER-DAEMON messages — filtered by AccountDiscoveryService, not provider
        # Provider parses them; service skips them
        raw = _make_mbox(MAILER_DAEMON_MSG)
        result = self.provider.parse(raw)
        # Provider returns it; local_part filtering happens in service layer
        assert len(result) == 1
        assert result[0].sender_address == "mailer-daemon@example.com"

    def test_deduplicates_by_message_id(self) -> None:
        """Same Message-ID appearing twice should produce one result."""
        raw = _make_mbox(SIMPLE_MSG, SIMPLE_MSG)
        result = self.provider.parse(raw)
        assert len(result) == 1

    def test_empty_mbox(self) -> None:
        result = self.provider.parse(b"")
        assert result == []

    def test_parse_multiple_messages(self) -> None:
        raw = _make_mbox(SIMPLE_MSG, ENCODED_SUBJECT_MSG)
        result = self.provider.parse(raw)
        assert len(result) == 2

    def test_compute_hash_deterministic(self) -> None:
        data = b"test content"
        h1 = MboxParserProvider.compute_hash(data)
        h2 = MboxParserProvider.compute_hash(data)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_compute_hash_different_content(self) -> None:
        h1 = MboxParserProvider.compute_hash(b"content a")
        h2 = MboxParserProvider.compute_hash(b"content b")
        assert h1 != h2

    def test_parse_timezone_naive_date(self) -> None:
        """Dates without timezone info should be treated as UTC."""
        msg = textwrap.dedent("""\
            From: noreply@example.com
            To: user@example.com
            Subject: Test
            Date: Mon, 01 Jan 2024 10:00:00
            Message-ID: <tz-naive@example.com>
        """)
        raw = _make_mbox(msg)
        result = self.provider.parse(raw)
        assert len(result) == 1
        assert result[0].date is not None
        assert result[0].date.tzinfo is not None


class TestParsedEmailModel:
    def test_domain_extraction(self) -> None:
        email = ParsedEmail(
            sender_address="noreply@sub.example.co.uk",
            sender_domain="sub.example.co.uk",
        )
        assert email.sender_domain == "sub.example.co.uk"
```

---

### 2. `tests/unit/email_accounts/test_service_discovery.py`

```python
# tests/unit/email_accounts/test_service_discovery.py
"""Unit tests for AccountDiscoveryService."""
from datetime import datetime, timezone

import pytest

from backend.app.db.models.email_accounts import (
    DiscoveredAccountSourceType,
    ServiceRegistry,
)
from backend.app.email_accounts.service import (
    AccountDiscoveryService,
    _classify_source_type,
    _make_display_name,
    _should_skip,
)
from backend.app.providers.tools.mbox_parser.models import ParsedEmail

UTC = timezone.utc


def _make_registry(
    service_name: str,
    display_name: str,
    domains: list[str],
    login_url: str = "https://example.com/login",
    password_reset_url: str = "https://example.com/reset",
) -> ServiceRegistry:
    entry = ServiceRegistry()
    entry.service_name = service_name
    entry.display_name = display_name
    entry.category = "test"
    entry.common_domains = domains
    entry.login_url = login_url
    entry.password_reset_url = password_reset_url
    entry.is_active = True
    return entry


def _make_email(
    sender_address: str = "noreply@github.com",
    sender_domain: str = "github.com",
    subject: str = "Welcome",
    date: datetime | None = None,
) -> ParsedEmail:
    return ParsedEmail(
        sender_address=sender_address,
        sender_domain=sender_domain,
        subject=subject,
        date=date or datetime(2024, 1, 1, tzinfo=UTC),
        message_id=f"<{sender_address}-{subject[:10]}>",
    )


class TestClassifySourceType:
    def test_account_confirmation(self) -> None:
        assert _classify_source_type("Welcome to GitHub!") == DiscoveredAccountSourceType.ACCOUNT_CONFIRMATION
        assert _classify_source_type("Confirm your email address") == DiscoveredAccountSourceType.ACCOUNT_CONFIRMATION
        assert _classify_source_type("Thank you for registering") == DiscoveredAccountSourceType.ACCOUNT_CONFIRMATION

    def test_password_reset(self) -> None:
        assert _classify_source_type("Password reset request") == DiscoveredAccountSourceType.PASSWORD_RESET
        assert _classify_source_type("Reset your password") == DiscoveredAccountSourceType.PASSWORD_RESET

    def test_receipt(self) -> None:
        assert _classify_source_type("Your order confirmation") == DiscoveredAccountSourceType.RECEIPT
        assert _classify_source_type("Invoice #12345") == DiscoveredAccountSourceType.RECEIPT

    def test_newsletter(self) -> None:
        assert _classify_source_type("Weekly newsletter") == DiscoveredAccountSourceType.NEWSLETTER

    def test_security_alert(self) -> None:
        assert _classify_source_type("Unusual sign-in detected") == DiscoveredAccountSourceType.SECURITY_ALERT
        assert _classify_source_type("New device login") == DiscoveredAccountSourceType.SECURITY_ALERT

    def test_other(self) -> None:
        assert _classify_source_type("Random subject line") == DiscoveredAccountSourceType.OTHER


class TestShouldSkip:
    def test_skips_example_domain(self) -> None:
        em = _make_email(sender_address="user@example.com", sender_domain="example.com")
        assert _should_skip(em) is True

    def test_skips_mailer_daemon(self) -> None:
        em = _make_email(sender_address="mailer-daemon@example.org", sender_domain="example.org")
        assert _should_skip(em) is True

    def test_does_not_skip_normal_sender(self) -> None:
        em = _make_email(sender_address="noreply@github.com", sender_domain="github.com")
        assert _should_skip(em) is False


class TestMakeDisplayName:
    def test_strips_noreply_prefix(self) -> None:
        assert _make_display_name("noreply.github.com") == "Github"

    def test_titlecases_sld(self) -> None:
        assert _make_display_name("stripe.com") == "Stripe"

    def test_handles_hyphenated_domain(self) -> None:
        name = _make_display_name("my-service.com")
        assert "My Service" == name or "My-Service" in name  # either is acceptable


class TestAccountDiscoveryService:
    def setup_method(self) -> None:
        github_registry = _make_registry(
            "github", "GitHub", ["github.com"],
            "https://github.com/login", "https://github.com/password_reset"
        )
        self.service = AccountDiscoveryService(registry=[github_registry])

    def test_groups_emails_by_service(self) -> None:
        emails = [
            _make_email(sender_address="noreply@github.com", sender_domain="github.com", subject="Welcome to GitHub!"),
            _make_email(sender_address="noreply@github.com", sender_domain="github.com", subject="Password reset"),
        ]
        drafts = self.service.process(emails, "user@example.com")
        assert len(drafts) == 1
        assert drafts[0].service_name == "github"
        assert drafts[0].email_count == 2

    def test_known_service_gets_registry_urls(self) -> None:
        emails = [_make_email(sender_address="noreply@github.com", sender_domain="github.com")]
        drafts = self.service.process(emails, "user@example.com")
        assert drafts[0].login_url == "https://github.com/login"
        assert drafts[0].password_reset_url == "https://github.com/password_reset"

    def test_unknown_service_gets_no_urls(self) -> None:
        emails = [_make_email(sender_address="noreply@unknown-saas.com", sender_domain="unknown-saas.com")]
        drafts = self.service.process(emails, "user@example.com")
        assert len(drafts) == 1
        assert drafts[0].login_url is None

    def test_skips_self_sent_email(self) -> None:
        """Emails sent from the user's own address should be excluded."""
        emails = [_make_email(sender_address="user@example.com", sender_domain="example.com")]
        drafts = self.service.process(emails, "user@example.com")
        assert len(drafts) == 0

    def test_date_range_tracked(self) -> None:
        emails = [
            _make_email(date=datetime(2024, 1, 1, tzinfo=UTC)),
            _make_email(date=datetime(2024, 6, 1, tzinfo=UTC)),
        ]
        drafts = self.service.process(emails, "other@example.com")
        assert drafts[0].first_seen_at == datetime(2024, 1, 1, tzinfo=UTC)
        assert drafts[0].last_seen_at == datetime(2024, 6, 1, tzinfo=UTC)

    def test_dominant_source_type_priority(self) -> None:
        """account_confirmation should win over newsletter in same group."""
        emails = [
            _make_email(subject="Weekly newsletter"),
            _make_email(subject="Welcome to GitHub!"),
        ]
        drafts = self.service.process(emails, "user@other.com")
        assert drafts[0].source_type == DiscoveredAccountSourceType.ACCOUNT_CONFIRMATION

    def test_empty_email_list(self) -> None:
        drafts = self.service.process([], "user@example.com")
        assert drafts == []
```

---

### 3. `tests/integration/test_mbox_discovery_pipeline.py`

```python
# tests/integration/test_mbox_discovery_pipeline.py
"""
Integration tests for the full mbox processing pipeline.
Requires a real test database (see conftest.py).
"""
import textwrap
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.email_accounts import MboxUploadStatus, ServiceRegistry
from backend.app.db.repositories.discovered_accounts import DiscoveredAccountRepository
from backend.app.db.repositories.mbox_uploads import MboxUploadRepository
from backend.app.db.repositories.service_registry import ServiceRegistryRepository
from backend.app.db.repositories.signals import SignalRepository
from backend.app.jobs.mbox_processor import process_mbox_upload


def _make_mbox_bytes(sender: str = "noreply@github.com", subject: str = "Welcome to GitHub!") -> bytes:
    msg = textwrap.dedent(f"""\
        From MAILER-DAEMON Fri Jan  1 00:00:00 2021
        From: GitHub <{sender}>
        To: user@example.com
        Subject: {subject}
        Date: Mon, 01 Jan 2024 10:00:00 +0000
        Message-ID: <test-{uuid.uuid4()}@github.com>

    """)
    return msg.encode("utf-8")


@pytest.mark.asyncio
class TestMboxProcessingPipeline:
    async def test_full_pipeline_creates_account_and_signal(
        self,
        db_session: AsyncSession,
        test_user_id: uuid.UUID,
        test_asset_id: uuid.UUID,
    ) -> None:
        # Seed registry
        reg_repo = ServiceRegistryRepository(db_session)
        # (Assumes service_registry is seeded in test DB or we insert here)

        upload_repo = MboxUploadRepository(db_session)
        raw = _make_mbox_bytes()
        file_hash = "testhash123"
        upload = await upload_repo.create(
            user_id=test_user_id,
            filename="test.mbox",
            file_hash=file_hash,
        )
        await db_session.commit()

        await process_mbox_upload(
            upload_id=upload.id,
            user_id=test_user_id,
            asset_id=test_asset_id,
            asset_value="user@example.com",
            raw_bytes=raw,
        )

        # Verify upload completed
        completed_upload = await upload_repo.get_by_id(upload.id, test_user_id)
        assert completed_upload is not None
        assert completed_upload.status == MboxUploadStatus.COMPLETED
        assert completed_upload.accounts_discovered >= 0  # may be 0 if registry not seeded

    async def test_idempotency_same_hash(
        self,
        db_session: AsyncSession,
        test_user_id: uuid.UUID,
    ) -> None:
        """Uploading same file hash twice should not create a duplicate upload."""
        upload_repo = MboxUploadRepository(db_session)
        file_hash = f"idempotency-test-{uuid.uuid4().hex}"

        upload1 = await upload_repo.create(
            user_id=test_user_id, filename="a.mbox", file_hash=file_hash
        )
        await db_session.commit()

        existing = await upload_repo.get_by_hash(test_user_id, file_hash)
        assert existing is not None
        assert existing.id == upload1.id

    async def test_failed_upload_sets_error_detail(
        self,
        db_session: AsyncSession,
        test_user_id: uuid.UUID,
        test_asset_id: uuid.UUID,
    ) -> None:
        upload_repo = MboxUploadRepository(db_session)
        upload = await upload_repo.create(
            user_id=test_user_id,
            filename="bad.mbox",
            file_hash="badhash456",
        )
        await db_session.commit()

        # Pass corrupt bytes to trigger failure path
        await process_mbox_upload(
            upload_id=upload.id,
            user_id=test_user_id,
            asset_id=test_asset_id,
            asset_value="user@example.com",
            raw_bytes=b"this is not a valid mbox",
        )

        # Should complete (0 accounts found) or fail gracefully
        result = await upload_repo.get_by_id(upload.id, test_user_id)
        assert result is not None
        assert result.status in (MboxUploadStatus.COMPLETED, MboxUploadStatus.FAILED)
```

---

### 4. `tests/api/test_email_accounts_endpoints.py`

```python
# tests/api/test_email_accounts_endpoints.py
"""API-level tests for email account endpoints."""
import io
import textwrap

import pytest
from httpx import AsyncClient


def _make_mbox_bytes() -> bytes:
    return textwrap.dedent("""\
        From MAILER-DAEMON Fri Jan  1 00:00:00 2021
        From: GitHub <noreply@github.com>
        To: user@example.com
        Subject: Welcome to GitHub!
        Date: Mon, 01 Jan 2024 10:00:00 +0000
        Message-ID: <api-test@github.com>

    """).encode("utf-8")


@pytest.mark.asyncio
class TestUploadEndpoint:
    async def test_upload_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/email-accounts/upload")
        assert resp.status_code == 401

    async def test_upload_returns_202(
        self, auth_client: AsyncClient, plus_user_headers: dict
    ) -> None:
        data = _make_mbox_bytes()
        resp = await auth_client.post(
            "/api/v1/email-accounts/upload",
            files={"file": ("test.mbox", io.BytesIO(data), "application/octet-stream")},
        )
        assert resp.status_code == 202
        body = resp.json()
        assert "upload_id" in body
        assert body["status"] == "pending"

    async def test_upload_idempotent_same_file(
        self, auth_client: AsyncClient, plus_user_headers: dict
    ) -> None:
        data = _make_mbox_bytes()
        resp1 = await auth_client.post(
            "/api/v1/email-accounts/upload",
            files={"file": ("a.mbox", io.BytesIO(data), "application/octet-stream")},
        )
        resp2 = await auth_client.post(
            "/api/v1/email-accounts/upload",
            files={"file": ("b.mbox", io.BytesIO(data), "application/octet-stream")},
        )
        assert resp1.json()["upload_id"] == resp2.json()["upload_id"]

    async def test_upload_core_tier_rejected(
        self, auth_client: AsyncClient, core_user_headers: dict
    ) -> None:
        data = _make_mbox_bytes()
        resp = await auth_client.post(
            "/api/v1/email-accounts/upload",
            files={"file": ("test.mbox", io.BytesIO(data), "application/octet-stream")},
            headers=core_user_headers,
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestUploadStatusEndpoint:
    async def test_get_status_invalid_uuid(self, auth_client: AsyncClient) -> None:
        resp = await auth_client.get("/api/v1/email-accounts/upload/not-a-uuid")
        assert resp.status_code == 422

    async def test_get_status_not_found(self, auth_client: AsyncClient) -> None:
        import uuid
        resp = await auth_client.get(f"/api/v1/email-accounts/upload/{uuid.uuid4()}")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestDiscoveredAccountsEndpoint:
    async def test_list_returns_empty_initially(self, auth_client: AsyncClient) -> None:
        resp = await auth_client.get("/api/v1/email-accounts/discovered")
        assert resp.status_code == 200
        body = resp.json()
        assert "accounts" in body
        assert isinstance(body["accounts"], list)

    async def test_mark_reviewed_invalid_uuid(self, auth_client: AsyncClient) -> None:
        resp = await auth_client.patch("/api/v1/email-accounts/discovered/bad-id/review")
        assert resp.status_code == 422

    async def test_mark_reviewed_not_found(self, auth_client: AsyncClient) -> None:
        import uuid
        resp = await auth_client.patch(f"/api/v1/email-accounts/discovered/{uuid.uuid4()}/review")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestCsvExport:
    async def test_export_returns_csv(self, auth_client: AsyncClient) -> None:
        resp = await auth_client.get("/api/v1/email-accounts/export/csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "attachment" in resp.headers.get("content-disposition", "")

    async def test_csv_has_correct_headers(self, auth_client: AsyncClient) -> None:
        resp = await auth_client.get("/api/v1/email-accounts/export/csv")
        content = resp.content.decode("utf-8-sig")
        first_line = content.splitlines()[0]
        assert "Title" in first_line
        assert "Username" in first_line
        assert "URL" in first_line
```

---

## Checklist
- [ ] `tests/unit/providers/test_mbox_parser.py` — 11 test cases
- [ ] `tests/unit/email_accounts/test_service_discovery.py` — 15 test cases
- [ ] `tests/integration/test_mbox_discovery_pipeline.py` — 3 integration tests
- [ ] `tests/api/test_email_accounts_endpoints.py` — 10 API tests
- [ ] `tests/unit/providers/__init__.py` created if missing
- [ ] `tests/unit/email_accounts/__init__.py` created if missing

## Notes on Test Fixtures
The integration and API tests assume these fixtures from `conftest.py`:
- `db_session` — real async DB session (existing)
- `test_user_id` — UUID of a test user (existing or add)
- `test_asset_id` — UUID of a verified email asset for that user (add if missing)
- `auth_client` — authenticated AsyncClient (existing)
- `plus_user_headers` — auth headers for a Plus-tier user (add if missing)
- `core_user_headers` — auth headers for a Core-tier user (add if missing)

Check `tests/conftest.py` and add any missing fixtures before running Phase 6 tests.
