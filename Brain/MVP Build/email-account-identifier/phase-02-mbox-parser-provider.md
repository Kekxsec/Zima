# Phase 2 — Mbox Parser Provider

## Goal
Parse a raw mbox file (bytes) into a list of typed `ParsedEmail` objects. Pure parsing — no HTTP, no business logic, no DB access. Uses only Python stdlib.

---

## Files to Create

### 1. `backend/app/providers/tools/mbox_parser/__init__.py`
Empty.

### 2. `backend/app/providers/tools/mbox_parser/models.py`

Typed output models (Pydantic v2) returned by the provider.

```python
# backend/app/providers/tools/mbox_parser/models.py
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class ParsedEmail(BaseModel):
    """
    Normalised representation of a single email extracted from an mbox.
    Raw body content is NEVER included — privacy requirement.
    """
    sender_address: str = Field(..., max_length=512)   # e.g. "noreply@github.com"
    sender_domain: str = Field(..., max_length=255)    # e.g. "github.com"
    sender_name: str = Field("", max_length=255)       # e.g. "GitHub"
    recipient_address: str = Field("", max_length=512)
    subject: str = Field("", max_length=512)
    date: datetime | None = None
    message_id: str = Field("", max_length=512)        # for dedup within a file
```

### 3. `backend/app/providers/tools/mbox_parser/client.py`

```python
# backend/app/providers/tools/mbox_parser/client.py
from __future__ import annotations

import email as stdlib_email
import email.header
import email.utils
import hashlib
import io
import mailbox
import re
from datetime import datetime, timezone
from typing import Any

from backend.app.core.logging import get_logger
from backend.app.providers.tools.mbox_parser.models import ParsedEmail

logger = get_logger(__name__)

_MAX_MESSAGES = 50_000        # hard cap — prevents OOM on malicious files
_MIN_SENDER_LENGTH = 3        # skip obviously broken senders


def _decode_header_value(raw: str | None) -> str:
    """Decode RFC 2047 encoded header values to plain str."""
    if not raw:
        return ""
    parts = email.header.decode_header(raw)
    decoded: list[str] = []
    for part, charset in parts:
        if isinstance(part, bytes):
            try:
                decoded.append(part.decode(charset or "utf-8", errors="replace"))
            except (LookupError, UnicodeDecodeError):
                decoded.append(part.decode("latin-1", errors="replace"))
        else:
            decoded.append(str(part))
    return " ".join(decoded).strip()


def _extract_domain(address: str) -> str:
    """Returns the domain part of an email address, lowercased."""
    address = address.strip().lower()
    at_idx = address.rfind("@")
    if at_idx == -1:
        return ""
    return address[at_idx + 1:].strip(">").strip()


def _parse_date(raw: str | None) -> datetime | None:
    """Parse RFC 2822 date header to timezone-aware datetime."""
    if not raw:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None


def _parse_single_message(msg: Any) -> ParsedEmail | None:
    """
    Convert a stdlib email.message.Message to ParsedEmail.
    Returns None if the message is unrecoverable or has no usable sender.
    """
    try:
        raw_from = msg.get("From", "") or ""
        name_part, addr_part = email.utils.parseaddr(raw_from)
        sender_address = addr_part.strip().lower()

        if len(sender_address) < _MIN_SENDER_LENGTH or "@" not in sender_address:
            return None

        sender_domain = _extract_domain(sender_address)
        if not sender_domain:
            return None

        raw_to = msg.get("To", "") or ""
        _, recipient_address = email.utils.parseaddr(raw_to)

        subject = _decode_header_value(msg.get("Subject"))
        date = _parse_date(msg.get("Date"))
        message_id = (msg.get("Message-ID") or "").strip()
        sender_name = _decode_header_value(name_part) if name_part else ""

        return ParsedEmail(
            sender_address=sender_address[:512],
            sender_domain=sender_domain[:255],
            sender_name=sender_name[:255],
            recipient_address=recipient_address.strip().lower()[:512],
            subject=subject[:512],
            date=date,
            message_id=message_id[:512],
        )
    except Exception as exc:
        logger.debug("mbox_parser.message_parse_error", error=str(exc))
        return None


class MboxParserProvider:
    """
    Parses a raw mbox file (bytes) into a list of ParsedEmail objects.

    Rules:
    - Never stores or returns email body content.
    - Skips unparseable messages gracefully.
    - Hard cap at _MAX_MESSAGES to prevent OOM.
    - Deduplicates by Message-ID within the same parse call.
    """

    name = "tool_mbox_parser"

    def parse(self, raw_bytes: bytes) -> list[ParsedEmail]:
        """
        Parse raw mbox bytes. Returns list of ParsedEmail (headers only, no body).
        Thread-safe — creates a fresh mailbox.mbox from a BytesIO each call.
        """
        file_obj = io.BytesIO(raw_bytes)
        mbox = mailbox.mbox(file_obj)  # type: ignore[arg-type]

        results: list[ParsedEmail] = []
        seen_message_ids: set[str] = set()
        skipped = 0

        for i, raw_msg in enumerate(mbox):
            if i >= _MAX_MESSAGES:
                logger.warning(
                    "mbox_parser.cap_reached",
                    cap=_MAX_MESSAGES,
                    total_skipped_after_cap=len(list(mbox)) - _MAX_MESSAGES,
                )
                break

            parsed = _parse_single_message(raw_msg)
            if parsed is None:
                skipped += 1
                continue

            # Dedup within file by Message-ID
            if parsed.message_id and parsed.message_id in seen_message_ids:
                skipped += 1
                continue
            if parsed.message_id:
                seen_message_ids.add(parsed.message_id)

            results.append(parsed)

        logger.info(
            "mbox_parser.completed",
            total_parsed=len(results),
            skipped=skipped,
        )
        return results

    @staticmethod
    def compute_hash(raw_bytes: bytes) -> str:
        """Returns SHA-256 hex digest of the raw file — used as idempotency key."""
        return hashlib.sha256(raw_bytes).hexdigest()
```

---

## Notes

**Why `mailbox.mbox` instead of a streaming approach?**
`mailbox.mbox` is the stdlib standard for mbox parsing and handles the From_ separator line correctly. It loads message headers lazily enough for our use. At 100 MB with ~50k messages this is acceptable. If we need streaming in future, we can switch to a line-by-line From_ splitter.

**Why no body content?**
Privacy requirement. We only need sender, subject, date to classify accounts. The body is discarded immediately after header extraction.

**Thread safety**
The provider is stateless. `parse()` creates a fresh `mailbox.mbox` instance each call — safe for concurrent invocations.

**Error handling**
Individual unparseable messages are skipped with a debug log, not raised. The caller gets however many emails could be parsed. If zero are parsed from a non-empty file, the background task will log a warning and mark the upload completed with 0 accounts.

---

## Checklist
- [ ] `backend/app/providers/tools/mbox_parser/__init__.py`
- [ ] `backend/app/providers/tools/mbox_parser/models.py` — `ParsedEmail` Pydantic model
- [ ] `backend/app/providers/tools/mbox_parser/client.py` — `MboxParserProvider` with `parse()` and `compute_hash()`
- [ ] No imports of DB models, repositories, or modules (import checker will catch violations)
- [ ] Passes mypy

## Dependencies
Phase 1 models not needed here — this provider is self-contained.

## Validation
```python
provider = MboxParserProvider()
raw = open("test.mbox", "rb").read()
emails = provider.parse(raw)
assert all(isinstance(e, ParsedEmail) for e in emails)
assert all("@" in e.sender_address for e in emails)
```
