# scripts/validate_services.py
"""
Interactive service validator — reviews unknown domains from an mbox file
and adds approved ones to the service registry.

Usage:
    python -m scripts.validate_services tests/fixtures/sample.mbox
    python -m scripts.validate_services /path/to/export.mbox --min-emails 2
    python -m scripts.validate_services /path/to/export.mbox --seed   # also write to DB

Approved services are saved to scripts/custom_services.json and will be
included the next time `python -m scripts.seed_service_registry` is run.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import uuid
from pathlib import Path

# ---------------------------------------------------------------------------
# Known domains (loaded from seed + custom file) — so we don't re-prompt
# already-registered domains.
# ---------------------------------------------------------------------------
CUSTOM_FILE = Path(__file__).parent / "custom_services.json"

_CATEGORIES = [
    "social",
    "ecommerce",
    "finance",
    "streaming",
    "productivity",
    "developer",
    "travel",
    "food",
    "gaming",
    "health",
    "security",
    "education",
    "media",
    "creative",
    "storage",
    "marketing",
    "events",
    "lifestyle",
    "other",
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

_SUBJECT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"(verify|confirm|activate|complete|validate).{0,30}(account|email|sign.?up|registr)",
            re.IGNORECASE,
        ),
        "account_confirmation",
    ),
    (
        re.compile(
            r"(welcome to|thanks for (joining|signing up|creating|registering))",
            re.IGNORECASE,
        ),
        "account_confirmation",
    ),
    (
        re.compile(r"(reset|change|forgot|recover).{0,20}password", re.IGNORECASE),
        "password_reset",
    ),
    (
        re.compile(
            r"(receipt|order confirm|invoice|your (purchase|order)|payment (confirm|receipt))",
            re.IGNORECASE,
        ),
        "receipt",
    ),
    (
        re.compile(
            r"(security (alert|notice|warning)|unusual (sign.?in|activity|access)|new (device|login|sign.?in)|suspicious)",
            re.IGNORECASE,
        ),
        "security_alert",
    ),
    (
        re.compile(
            r"(unsubscribe|newsletter|digest|weekly|monthly|update from)", re.IGNORECASE
        ),
        "newsletter",
    ),
]


def _classify(subject: str | None) -> str:
    if not subject:
        return "other"
    for pattern, t in _SUBJECT_PATTERNS:
        if pattern.search(subject):
            return t
    return "other"


def _load_known_domains() -> set[str]:
    known: set[str] = set()
    try:
        from scripts.seed_service_registry import SERVICES  # type: ignore[import]

        for _, _, _, domains, *_ in SERVICES:
            known.update(d.lower() for d in domains)
    except Exception:
        pass
    if CUSTOM_FILE.exists():
        for entry in json.loads(CUSTOM_FILE.read_text()):
            known.update(d.lower() for d in entry.get("common_domains", []))
    return known


def _load_custom() -> list[dict]:
    if CUSTOM_FILE.exists():
        return json.loads(CUSTOM_FILE.read_text())
    return []


def _save_custom(entries: list[dict]) -> None:
    CUSTOM_FILE.write_text(json.dumps(entries, indent=2))


def _parse_mbox(path: Path) -> dict[str, dict]:
    """Return domain → {email_count, subjects, source_types} for unknown domains."""
    from backend.app.providers.tools.mbox_parser.client import MboxParserProvider

    data = path.read_bytes()
    provider = MboxParserProvider()
    print(f"Reading {path.name} ({len(data):,} bytes)…", file=sys.stderr)
    emails = provider.parse(data)
    print(f"Parsed {len(emails)} messages.", file=sys.stderr)

    known = _load_known_domains()
    buckets: dict[str, dict] = {}

    for email in emails:
        domain = (email.sender_domain or "").lower()
        if not domain or domain in _SKIP_DOMAINS or domain in known:
            continue
        if domain not in buckets:
            buckets[domain] = {"email_count": 0, "subjects": [], "source_types": set()}
        b = buckets[domain]
        b["email_count"] += 1
        if email.subject and email.subject not in b["subjects"]:
            b["subjects"].append(email.subject)
        b["source_types"].add(_classify(email.subject))

    return buckets


def _prompt(label: str, default: str = "") -> str:
    display = f" [{default}]" if default else ""
    try:
        val = input(f"  {label}{display}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return val if val else default


def _pick_category() -> str:
    print()
    per_row = 4
    for i, cat in enumerate(_CATEGORIES, 1):
        end = "\n" if i % per_row == 0 else "  "
        print(f"  {i:>2}. {cat:<14}", end=end)
    if len(_CATEGORIES) % per_row != 0:
        print()
    while True:
        raw = _prompt("Category number", str(len(_CATEGORIES)))
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(_CATEGORIES):
                return _CATEGORIES[idx]
        except ValueError:
            pass
        # Allow typing the category name directly
        if raw.lower() in _CATEGORIES:
            return raw.lower()
        print("  Invalid choice — enter a number or category name.")


def _review(domain: str, bucket: dict) -> dict | None:
    """Interactively review one domain. Returns entry dict or None if skipped."""
    subjects = bucket["subjects"][:5]
    types = ", ".join(sorted(bucket["source_types"]))

    print(f"\n{'─' * 60}")
    print(f"  Domain  : {domain}")
    print(f"  Emails  : {bucket['email_count']}  |  Types: {types}")
    print("  Subjects:")
    for s in subjects:
        print(f"    • {s[:80]}")

    try:
        action = input("\n  [Enter] Add  [s] Skip  [q] Quit: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)

    if action == "q":
        sys.exit(0)
    if action == "s":
        print("  Skipped.")
        return None

    display_name = _prompt("Display name", domain)
    service_name = re.sub(r"[^a-z0-9_]", "_", display_name.lower()).strip("_")
    service_name = _prompt("service_name (slug)", service_name)
    category = _pick_category()
    extra_domains_raw = _prompt(
        "Additional domains (comma-separated, leave blank for none)"
    )
    extra_domains = [d.strip() for d in extra_domains_raw.split(",") if d.strip()]
    login_url = _prompt("Login URL")
    password_reset_url = _prompt("Password reset URL")

    entry = {
        "service_name": service_name,
        "display_name": display_name,
        "category": category,
        "common_domains": [domain] + extra_domains,
        "login_url": login_url or None,
        "password_reset_url": password_reset_url or None,
    }
    print(f"  ✓ Will add: {display_name} ({category})")
    return entry


async def _seed_entry(entry: dict) -> None:
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from backend.app.core.config import settings
    from backend.app.db.models.email_accounts import ServiceRegistry

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        stmt = (
            pg_insert(ServiceRegistry)
            .values(
                id=uuid.uuid4(),
                service_name=entry["service_name"],
                display_name=entry["display_name"],
                category=entry["category"],
                common_domains=entry["common_domains"],
                login_url=entry.get("login_url"),
                password_reset_url=entry.get("password_reset_url"),
                is_active=True,
            )
            .on_conflict_do_update(
                constraint="uq_service_registry_name",
                set_={
                    "display_name": entry["display_name"],
                    "category": entry["category"],
                    "common_domains": entry["common_domains"],
                    "login_url": entry.get("login_url"),
                    "password_reset_url": entry.get("password_reset_url"),
                    "is_active": True,
                },
            )
        )
        await session.execute(stmt)
        await session.commit()
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interactively validate and register new services from an mbox file."
    )
    parser.add_argument("mbox", help="Path to the .mbox file")
    parser.add_argument(
        "--min-emails",
        type=int,
        default=1,
        help="Minimum email count to prompt (default: 1)",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Also write approved services to the database immediately",
    )
    args = parser.parse_args()

    path = Path(args.mbox)
    if not path.exists():
        sys.exit(f"File not found: {path}")

    buckets = _parse_mbox(path)
    candidates = sorted(
        [(d, b) for d, b in buckets.items() if b["email_count"] >= args.min_emails],
        key=lambda x: -x[1]["email_count"],
    )

    if not candidates:
        print("No unknown domains found — nothing to validate.")
        return

    print(f"\nFound {len(candidates)} unknown domain(s) to review.")

    custom = _load_custom()
    approved: list[dict] = []

    for domain, bucket in candidates:
        entry = _review(domain, bucket)
        if entry:
            approved.append(entry)

    if not approved:
        print("\nNo services approved.")
        return

    # Merge into custom_services.json (avoid duplicates by service_name)
    existing_names = {e["service_name"] for e in custom}
    new_entries = [e for e in approved if e["service_name"] not in existing_names]
    custom.extend(new_entries)
    _save_custom(custom)
    print(f"\nSaved {len(new_entries)} new service(s) to {CUSTOM_FILE}.")
    print("Run `python -m scripts.seed_service_registry` to push to the database.")

    if args.seed:
        print("Seeding to database…")
        for entry in new_entries:
            asyncio.run(_seed_entry(entry))
            print(f"  ✓ {entry['display_name']}")
        print("Done.")


if __name__ == "__main__":
    main()
