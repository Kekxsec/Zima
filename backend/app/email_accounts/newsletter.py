# backend/app/email_accounts/newsletter.py
"""
NewsletterDetectionService — pre-pass that strips inbox noise before account
classification.

Design rules:
- No HTTP calls.
- No direct DB access — takes parsed emails, returns aggregated NewsletterDraft objects.
- Called by mbox_processor BEFORE AccountDiscoveryService.
- Uses explicit signals (List-ID, List-Unsubscribe, ESP domains, subject patterns)
  to produce a review queue, NOT automated actions.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime

from pydantic import BaseModel

from backend.app.providers.tools.mbox_parser.models import ParsedEmail

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


def _detect_confidence(msg: ParsedEmail) -> str | None:
    """
    Returns 'high', 'medium', or None (not a newsletter).

    High: has List-ID or List-Unsubscribe header (RFC 2919 / RFC 2369).
    Medium: sender domain is a known ESP, or subject matches newsletter pattern.
    """
    has_list_id = bool(msg.list_id)
    has_list_unsub = bool(msg.list_unsubscribe)

    if has_list_id or has_list_unsub:
        return "high"

    if _is_esp_domain(msg.sender_domain):
        return "medium"

    if msg.subject and _NEWSLETTER_SUBJECT_RE.search(msg.subject):
        return "medium"

    return None


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
    is_phishing: bool = False


class NewsletterDetectionService:
    """
    Stateless pre-pass classifier.
    Call detect() on a list of ParsedEmail before AccountDiscoveryService.
    Returns one NewsletterDraft per sender domain.
    """

    def detect(self, emails: list[ParsedEmail]) -> list[NewsletterDraft]:
        """
        Group newsletter emails by sender_domain and aggregate counts/metadata.

        Returns only senders where confidence is 'high' or 'medium'.
        """
        # domain → aggregated state
        buckets: dict[str, dict] = defaultdict(
            lambda: {
                "sender_name": None,
                "message_count": 0,
                "first_seen_at": None,
                "last_seen_at": None,
                "unsubscribe_url": None,
                "list_id": None,
                "confidence": "medium",
            }
        )

        for msg in emails:
            confidence = _detect_confidence(msg)
            if confidence is None:
                continue
            domain = msg.sender_domain
            if not domain:
                continue

            b = buckets[domain]
            b["message_count"] += 1

            # Escalate confidence: medium → high, never downgrade
            if confidence == "high":
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
            )
            for domain, state in buckets.items()
        ]
