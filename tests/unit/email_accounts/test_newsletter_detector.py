# tests/unit/email_accounts/test_newsletter_detector.py
from datetime import UTC, datetime

from backend.app.email_accounts.newsletter import (
    NewsletterDetectionService,
    score_newsletter_email,
)
from backend.app.providers.tools.mbox_parser.models import ParsedEmail


def _make_email(
    *,
    from_address: str,
    subject: str,
    list_id: str | None = None,
    list_unsubscribe: str | None = None,
    precedence: str | None = None,
) -> ParsedEmail:
    return ParsedEmail(
        message_id="<message@example.com>",
        subject=subject,
        from_address=from_address,
        from_name="Sender",
        sender_domain=from_address.split("@", 1)[1],
        to_address="user@example.com",
        to_addresses=["user@example.com"],
        date=datetime(2024, 1, 1, tzinfo=UTC),
        list_id=list_id,
        list_unsubscribe=list_unsubscribe,
        precedence=precedence,
    )


def test_score_newsletter_email_requires_multiple_signals() -> None:
    email_obj = _make_email(
        from_address="newsletter@medium.com",
        subject="Weekly product digest",
        list_unsubscribe="<https://example.com/unsub>",
    )

    assert score_newsletter_email(email_obj) == 60


def test_score_newsletter_email_crosses_threshold_with_bulk_header() -> None:
    email_obj = _make_email(
        from_address="newsletter@medium.com",
        subject="Weekly product digest",
        list_unsubscribe="<https://example.com/unsub>",
        precedence="bulk",
    )

    assert score_newsletter_email(email_obj) == 90


def test_partition_filters_only_high_confidence_newsletters() -> None:
    detector = NewsletterDetectionService()
    newsletter_email = _make_email(
        from_address="updates@substack.com",
        subject="This week in security",
        list_unsubscribe="<https://substack.com/unsub>",
        precedence="bulk",
    )
    account_email = _make_email(
        from_address="security@github.com",
        subject="Verify your email address",
    )

    drafts, account_emails = detector.partition([newsletter_email, account_email])

    assert len(drafts) == 1
    assert drafts[0].sender_domain == "substack.com"
    assert drafts[0].confidence == "high"
    assert drafts[0].confidence_score == 90
    assert account_emails == [account_email]


def test_detect_aggregates_newsletter_metadata_by_domain() -> None:
    detector = NewsletterDetectionService()
    emails = [
        _make_email(
            from_address="updates@substack.com",
            subject="Issue #41",
            list_id="security.substack.com",
            list_unsubscribe="<https://substack.com/unsub>",
        ),
        _make_email(
            from_address="digest@substack.com",
            subject="Issue #42",
            precedence="list",
            list_unsubscribe="<https://substack.com/unsub2>",
        ),
    ]

    drafts = detector.detect(emails)

    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.sender_domain == "substack.com"
    assert draft.message_count == 2
    assert draft.list_id == "security.substack.com"
    assert draft.unsubscribe_url == "<https://substack.com/unsub>"
    assert draft.confidence_score >= 70
