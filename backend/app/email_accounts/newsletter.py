# backend/app/email_accounts/newsletter.py
"""
NewsletterDetectionService — pre-pass that strips inbox noise before account
classification.

Design rules:
- No HTTP calls.
- No direct DB access — takes parsed emails, returns aggregated NewsletterDraft
  objects plus the filtered non-newsletter email stream.
- Called by mbox_processor BEFORE AccountDiscoveryService.
- Uses explicit signals (List-ID, List-Unsubscribe, bulk headers, ESP domains,
  sender patterns, subject patterns) to produce a review queue, NOT automated
  actions.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from backend.app.providers.tools.mbox_parser.models import ParsedEmail

_HEADER_SCORE = 30
_SENDER_SCORE = 20
_SUBJECT_SCORE = 15
_UNSUBSCRIBE_SCORE = 25
_NEWSLETTER_THRESHOLD = 70

# ---------------------------------------------------------------------------
# Known ESP (Email Service Provider) sending domains — strong newsletter signal
# ---------------------------------------------------------------------------
_ESP_DOMAINS: frozenset[str] = frozenset(
    {
        # Mailchimp / Mandrill
        "list-manage.com",
        "mailchi.mp",
        "mc.com",
        # Constant Contact
        "constantcontact.com",
        "r.constantcontact.com",
        # Campaign Monitor
        "cmail1.com",
        "cmail2.com",
        "cmail19.com",
        "cmail20.com",
        # SendGrid
        "sendgrid.net",
        "em.example.com",
        # HubSpot
        "hubspotemail.net",
        "hs-email.com",
        # Klaviyo
        "klaviyoemail.com",
        "klaviyo.com",
        # Brevo (Sendinblue)
        "sendinblue.com",
        "brevo.com",
        # Drip
        "dripemails.com",
        # ConvertKit
        "convertkit.com",
        "ck.page",
        # Mailgun
        "mailgun.org",
        # Amazon SES (bulk senders)
        "amazonses.com",
        # Salesforce Marketing Cloud (ExactTarget)
        "exacttarget.com",
        "email.salesforce.com",
        # Litmus
        "litmus.com",
        # Substack
        "substack.com",
        # Beehiiv
        "beehiiv.com",
        # Ghost
        "ghost.org",
        # Revue (Twitter newsletters)
        "getrevue.co",
    }
)

# Subject-line patterns that indicate newsletter/marketing content
_NEWSLETTER_SUBJECT_RE = re.compile(
    r"(unsubscribe|newsletter|digest|weekly|monthly|update from|"
    r"issue #|\bvol\b|\bissue\b|this week in|roundup|recap|"
    r"sale|% off|discount|promo|exclusive offer|limited time|"
    r"you won't want to miss|don't miss|check it out)",
    re.IGNORECASE,
)

_SENDER_PATTERN_RE = re.compile(
    r"^(newsletter|news|updates|digest|hello|noreply|no-reply|mailer|list)\b",
    re.IGNORECASE,
)

_BULK_PRECEDENCE_RE = re.compile(r"\b(bulk|list|junk)\b", re.IGNORECASE)


def _is_esp_domain(domain: str | None) -> bool:
    if not domain:
        return False
    # Check both exact match and suffix match (e.g. em.clientdomain.sendgrid.net)
    if domain in _ESP_DOMAINS:
        return True
    for esp in _ESP_DOMAINS:
        if domain.endswith("." + esp):
            return True
    return False


def _sender_matches_newsletter_pattern(msg: ParsedEmail) -> bool:
    if msg.from_address and _SENDER_PATTERN_RE.search(msg.from_address):
        return True
    if msg.from_name and _SENDER_PATTERN_RE.search(msg.from_name):
        return True
    return _is_esp_domain(msg.sender_domain)


def _header_indicators(msg: ParsedEmail) -> bool:
    if msg.list_id:
        return True
    if msg.precedence and _BULK_PRECEDENCE_RE.search(msg.precedence):
        return True
    return False


def _subject_indicator(msg: ParsedEmail) -> bool:
    return bool(msg.subject and _NEWSLETTER_SUBJECT_RE.search(msg.subject))


def score_newsletter_email(msg: ParsedEmail) -> int:
    """
    Return a conservative 0-100 newsletter score for one parsed email.

    Threshold guidance:
    - >= 70: treat as newsletter noise and filter from account discovery
    - < 70: keep in the account-discovery stream to avoid destructive false
      positives
    """
    score = 0
    if _header_indicators(msg):
        score += _HEADER_SCORE
    if _sender_matches_newsletter_pattern(msg):
        score += _SENDER_SCORE
    if _subject_indicator(msg):
        score += _SUBJECT_SCORE
    if msg.list_unsubscribe:
        score += _UNSUBSCRIBE_SCORE
    return min(score, 100)


class NewsletterDraft(BaseModel):
    """
    Aggregated newsletter sender metadata for one (user, sender_domain) pair.
    Produced by NewsletterDetectionService; consumed by mbox_processor.
    """

    sender_domain: str
    sender_name: str | None
    message_count: int
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    unsubscribe_url: str | None
    list_id: str | None
    confidence: str  # "high" | "medium"
    confidence_score: int
    is_phishing: bool = False


class NewsletterDetectionService:
    """
    Stateless pre-pass classifier.
    Call detect() on a list of ParsedEmail before AccountDiscoveryService.
    Returns one NewsletterDraft per sender domain.
    """

    def partition(
        self, emails: list[ParsedEmail]
    ) -> tuple[list[NewsletterDraft], list[ParsedEmail]]:
        """
        Return detected newsletters and the remaining emails safe for
        account-discovery classification.
        """
        newsletter_emails: list[ParsedEmail] = []
        account_emails: list[ParsedEmail] = []

        for msg in emails:
            if score_newsletter_email(msg) >= _NEWSLETTER_THRESHOLD:
                newsletter_emails.append(msg)
            else:
                account_emails.append(msg)

        return self.detect(newsletter_emails), account_emails

    def detect(self, emails: list[ParsedEmail]) -> list[NewsletterDraft]:
        """
        Group newsletter emails by sender_domain and aggregate counts/metadata.
        """
        # domain → aggregated state
        buckets: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "sender_name": None,
                "message_count": 0,
                "first_seen_at": None,
                "last_seen_at": None,
                "unsubscribe_url": None,
                "list_id": None,
                "confidence": "medium",
                "confidence_score": 0,
            }
        )

        for msg in emails:
            confidence_score = score_newsletter_email(msg)
            if confidence_score < _NEWSLETTER_THRESHOLD:
                continue
            domain = msg.sender_domain
            if not domain:
                continue

            b = buckets[domain]
            b["message_count"] += 1

            # Escalate confidence: medium → high, never downgrade.
            b["confidence_score"] = max(int(b["confidence_score"]), confidence_score)
            if confidence_score >= 85:
                b["confidence"] = "high"

            # Update sender_name — prefer the first non-empty one
            if b["sender_name"] is None and msg.from_name:
                b["sender_name"] = msg.from_name

            # Update unsubscribe_url — prefer non-empty
            if b["unsubscribe_url"] is None and msg.list_unsubscribe:
                b["unsubscribe_url"] = msg.list_unsubscribe

            # Update list_id — prefer non-empty
            if b["list_id"] is None and msg.list_id:
                b["list_id"] = msg.list_id

            # Extend time window
            if msg.date:
                if b["first_seen_at"] is None or msg.date < b["first_seen_at"]:
                    b["first_seen_at"] = msg.date
                if b["last_seen_at"] is None or msg.date > b["last_seen_at"]:
                    b["last_seen_at"] = msg.date

        return [
            NewsletterDraft(
                sender_domain=domain,
                sender_name=state["sender_name"],
                message_count=state["message_count"],
                first_seen_at=state["first_seen_at"],
                last_seen_at=state["last_seen_at"],
                unsubscribe_url=state["unsubscribe_url"],
                list_id=state["list_id"],
                confidence=state["confidence"],
                confidence_score=int(state["confidence_score"]),
            )
            for domain, state in buckets.items()
        ]
