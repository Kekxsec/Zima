# tests/unit/jobs/test_mbox_processor_vt.py
"""Unit tests for VirusTotal URL scanning in process_mbox_upload."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.email_accounts.newsletter import NewsletterDraft
from backend.app.jobs.mbox_processor import _scan_newsletter_url
from backend.app.providers.threat_intel.virustotal.client import UrlScanResult


def _make_newsletter_draft(
    unsubscribe_url: str | None = "https://news.example.com/unsub",
) -> NewsletterDraft:
    return NewsletterDraft(
        sender_domain="news.example.com",
        sender_name="Example News",
        message_count=5,
        first_seen_at=datetime(2024, 1, 1, tzinfo=UTC),
        last_seen_at=datetime(2024, 1, 5, tzinfo=UTC),
        unsubscribe_url=unsubscribe_url,
        list_id=None,
        confidence="high",
        confidence_score=80,
        is_phishing=False,
    )


def _clean_result(url: str) -> UrlScanResult:
    return UrlScanResult(
        url=url,
        is_malicious=False,
        malicious_count=0,
        suspicious_count=0,
        total_engines=70,
    )


def _malicious_result(url: str) -> UrlScanResult:
    return UrlScanResult(
        url=url,
        is_malicious=True,
        malicious_count=3,
        suspicious_count=1,
        total_engines=70,
    )


# ---------------------------------------------------------------------------
# _scan_newsletter_url
# ---------------------------------------------------------------------------


class TestScanNewsletterUrl:
    @pytest.mark.asyncio
    async def test_clean_url_leaves_is_phishing_false(self) -> None:
        draft = _make_newsletter_draft()

        with patch("backend.app.jobs.mbox_processor.VirusTotalProvider") as mock_cls:
            instance = mock_cls.return_value
            instance.scan_url = AsyncMock(
                return_value=_clean_result(draft.unsubscribe_url)  # type: ignore[arg-type]
            )
            result = await _scan_newsletter_url(draft, "test-key")

        assert result.is_phishing is False
        assert result.unsubscribe_url == draft.unsubscribe_url

    @pytest.mark.asyncio
    async def test_malicious_url_sets_is_phishing_true(self) -> None:
        draft = _make_newsletter_draft()

        with patch("backend.app.jobs.mbox_processor.VirusTotalProvider") as mock_cls:
            instance = mock_cls.return_value
            instance.scan_url = AsyncMock(
                return_value=_malicious_result(draft.unsubscribe_url)  # type: ignore[arg-type]
            )
            result = await _scan_newsletter_url(draft, "test-key")

        assert result.is_phishing is True
        assert result.unsubscribe_url == draft.unsubscribe_url

    @pytest.mark.asyncio
    async def test_no_url_skips_scan(self) -> None:
        draft = _make_newsletter_draft(unsubscribe_url=None)

        with patch("backend.app.jobs.mbox_processor.VirusTotalProvider") as mock_cls:
            result = await _scan_newsletter_url(draft, "test-key")

        mock_cls.assert_not_called()
        assert result.is_phishing is False

    @pytest.mark.asyncio
    async def test_vt_exception_fails_open(self) -> None:
        """Any VT error must leave is_phishing=False (fail-open)."""
        draft = _make_newsletter_draft()

        with patch("backend.app.jobs.mbox_processor.VirusTotalProvider") as mock_cls:
            instance = mock_cls.return_value
            instance.scan_url = AsyncMock(side_effect=RuntimeError("network error"))
            result = await _scan_newsletter_url(draft, "test-key")

        assert result.is_phishing is False
        assert result.unsubscribe_url == draft.unsubscribe_url
