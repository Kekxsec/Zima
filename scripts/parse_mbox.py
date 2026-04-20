# scripts/parse_mbox.py
"""
Offline mailbox export parser — no database or running server required.

Parses an `.mbox` file or Proton Mail export directory and prints discovered
accounts to stdout.

Usage:
    python -m scripts.parse_mbox tests/fixtures/sample.mbox
    python -m scripts.parse_mbox /path/to/your/export.mbox
    python -m scripts.parse_mbox /path/to/export.mbox --format csv
    python -m scripts.parse_mbox /path/to/export.mbox --format json
    python -m scripts.parse_mbox /path/to/proton-export
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from backend.app.db.models.email_accounts import DiscoveredAccountSourceType
from backend.app.email_accounts.priority import score as priority_score
from backend.app.providers.tools.mbox_parser.client import MboxParserProvider
from backend.app.providers.tools.mbox_parser.models import ParsedEmail

# ---------------------------------------------------------------------------
# Re-use the same subject patterns and skip list from service.py
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
        re.compile(r"(reset|change|forgot|recover).{0,20}password", re.IGNORECASE),
        DiscoveredAccountSourceType.PASSWORD_RESET,
    ),
    (
        re.compile(
            r"(receipt|order confirm|invoice|your (purchase|order)|payment (confirm|receipt))",
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
        # Bulk / infra senders
        "sendgrid.net",
        "mailchimp.com",
        "mandrillapp.com",
        "amazonses.com",
        "mailgun.org",
        "sparkpostmail.com",
        "bounce.com",
        "bounces.com",
    }
)

# ---------------------------------------------------------------------------
# Inline domain → service registry (mirrors scripts/seed_service_registry.py)
# Only used to produce a friendly display_name and category; everything else
# still works without it.
# ---------------------------------------------------------------------------
_DOMAIN_TO_SERVICE: dict[str, str] = {}
_DOMAIN_TO_CATEGORY: dict[str, str] = {}

try:
    from scripts.seed_service_registry import SERVICES  # type: ignore[import]

    for _name, _display, _category, _domains, *_ in SERVICES:
        for _d in _domains:
            _DOMAIN_TO_SERVICE[_d.lower()] = _display
            _DOMAIN_TO_CATEGORY[_d.lower()] = _category
except Exception:
    pass  # not fatal — domain name is used as fallback


def _classify_subject(subject: str | None) -> str:
    if not subject:
        return DiscoveredAccountSourceType.OTHER
    for pattern, source_type in _SUBJECT_PATTERNS:
        if pattern.search(subject):
            return source_type
    return DiscoveredAccountSourceType.OTHER


def _service_name(domain: str) -> str:
    return _DOMAIN_TO_SERVICE.get(domain.lower(), domain)


# ---------------------------------------------------------------------------
# Row dataclass (plain dict so it serialises easily)
# ---------------------------------------------------------------------------
def _process(emails: list[ParsedEmail]) -> list[dict]:
    # Deduplicate: domain → most-interesting source_type + counts
    seen: dict[str, dict] = {}
    _source_priority = {
        DiscoveredAccountSourceType.ACCOUNT_CONFIRMATION: 0,
        DiscoveredAccountSourceType.PASSWORD_RESET: 1,
        DiscoveredAccountSourceType.SECURITY_ALERT: 2,
        DiscoveredAccountSourceType.RECEIPT: 3,
        DiscoveredAccountSourceType.NEWSLETTER: 4,
        DiscoveredAccountSourceType.OTHER: 5,
    }

    for email in emails:
        domain = email.sender_domain or ""
        if not domain or domain in _SKIP_DOMAINS:
            continue

        source_type = _classify_subject(email.subject)
        category = _DOMAIN_TO_CATEGORY.get(domain.lower())

        if domain not in seen:
            seen[domain] = {
                "service": _service_name(domain),
                "domain": domain,
                "category": category,
                "source_type": source_type,
                "email_count": 0,
                "first_seen": email.date,
                "last_seen": email.date,
                "example_subject": email.subject or "",
            }

        row = seen[domain]
        row["email_count"] += 1

        # Upgrade source_type if this email's type is higher priority
        if _source_priority.get(source_type, 99) < _source_priority.get(
            row["source_type"], 99
        ):
            row["source_type"] = source_type
            row["example_subject"] = email.subject or ""
            row["category"] = category or row["category"]

        if email.date:
            if row["first_seen"] is None or email.date < row["first_seen"]:
                row["first_seen"] = email.date
            if row["last_seen"] is None or email.date > row["last_seen"]:
                row["last_seen"] = email.date

    # Score priority (no breach data offline — is_breached=False)
    for row in seen.values():
        p = priority_score(row["category"], row["source_type"], is_breached=False)
        row["priority"] = p

    rows = sorted(
        seen.values(), key=lambda r: (r["priority"].sort_key, r["service"].lower())
    )
    return rows


def _fmt_date(d) -> str:
    return d.strftime("%Y-%m-%d") if d else ""


def _print_table(rows: list[dict], total_parsed: int, total_skipped: int) -> None:
    if not rows:
        print("No accounts discovered.")
        return

    col_service = max(len(r["service"]) for r in rows)
    col_priority = max(len(r["priority"].label) for r in rows)
    col_type = max(len(r["source_type"]) for r in rows)

    header = (
        f"{'SERVICE':<{col_service}}  {'PRIORITY':<{col_priority}}  {'TYPE':<{col_type}}  "
        f"{'EMAILS':>6}  {'FIRST SEEN':>10}  {'LAST SEEN':>10}  EXAMPLE SUBJECT"
    )
    print(header)
    print("-" * (len(header) + 40))

    source_type_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        source_type_counts[row["source_type"]] += 1
        print(
            f"{row['service']:<{col_service}}  "
            f"{row['priority'].label:<{col_priority}}  "
            f"{row['source_type']:<{col_type}}  "
            f"{row['email_count']:>6}  "
            f"{_fmt_date(row['first_seen']):>10}  "
            f"{_fmt_date(row['last_seen']):>10}  "
            f"{row['example_subject'][:60]}"
        )

    print()
    print(
        f"Parsed {total_parsed} messages  •  Skipped {total_skipped} (generic/infra domains)"
    )
    print(f"Discovered {len(rows)} unique services:")
    for stype, count in sorted(source_type_counts.items(), key=lambda x: x[0]):
        print(f"  {stype:<26} {count}")


def _print_csv(rows: list[dict]) -> None:
    writer = csv.DictWriter(
        sys.stdout,
        fieldnames=[
            "priority",
            "service",
            "domain",
            "source_type",
            "email_count",
            "first_seen",
            "last_seen",
            "example_subject",
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                **row,
                "priority": row["priority"].label,
                "first_seen": _fmt_date(row["first_seen"]),
                "last_seen": _fmt_date(row["last_seen"]),
            }
        )


def _print_json(rows: list[dict]) -> None:
    out = [
        {
            **r,
            "priority": r["priority"].label,
            "priority_tier": r["priority"].tier,
            "first_seen": _fmt_date(r["first_seen"]),
            "last_seen": _fmt_date(r["last_seen"]),
        }
        for r in rows
    ]
    print(json.dumps(out, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse a mailbox export file and list discovered accounts."
    )
    parser.add_argument(
        "mbox",
        help="Path to the mailbox export (.mbox file or Proton export directory)",
    )
    parser.add_argument(
        "--format",
        choices=["table", "csv", "json"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include newsletters and other low-signal entries (hidden by default)",
    )
    args = parser.parse_args()

    path = Path(args.mbox)
    if not path.exists():
        sys.exit(f"File not found: {path}")

    provider = MboxParserProvider()

    print(f"Reading {path.name} ({path.stat().st_size:,} bytes)…", file=sys.stderr)
    emails = provider.parse_file(path)
    print(f"Parsed {len(emails)} messages.", file=sys.stderr)

    skipped = sum(
        1 for e in emails if e.sender_domain and e.sender_domain in _SKIP_DOMAINS
    )
    rows = _process(emails)

    if not args.all:
        rows = [
            r
            for r in rows
            if r["source_type"]
            not in (
                DiscoveredAccountSourceType.NEWSLETTER,
                DiscoveredAccountSourceType.OTHER,
            )
        ]

    if args.format == "table":
        _print_table(rows, len(emails), skipped)
    elif args.format == "csv":
        _print_csv(rows)
    else:
        _print_json(rows)


if __name__ == "__main__":
    main()
