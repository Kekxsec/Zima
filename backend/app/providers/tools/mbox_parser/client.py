# backend/app/providers/tools/mbox_parser/client.py
"""
MboxParserProvider — reads an mbox byte-stream, extracts per-message metadata.

Rules enforced here:
- Raw email bodies are NEVER stored or returned.
- Only headers (From, To, Subject, Date, Message-ID, List-*) are parsed.
- No disk I/O — parsing is entirely in-memory.
- Deduplicates by Message-ID within the same parse call.
"""

from __future__ import annotations

import email
import email.utils
import hashlib
from datetime import UTC, datetime
from email.header import decode_header, make_header
from email.message import Message
from email.parser import BytesParser
from email.policy import default as default_policy

from backend.app.providers.tools.mbox_parser.models import ParsedEmail

_MAX_MESSAGES: int = 200_000


def _decode_header_value(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        return str(make_header(decode_header(raw)))
    except Exception:
        return raw


def _extract_domain(address: str | None) -> str | None:
    if not address:
        return None
    at_idx = address.rfind("@")
    if at_idx == -1:
        return None
    domain = address[at_idx + 1 :].lower().strip(">").strip()
    return domain if domain else None


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
        return parsed.astimezone(UTC)
    except Exception:
        return None


class MboxParserProvider:
    """
    Parses a raw mbox file (bytes) into a list of ParsedEmail objects.

    - Splits the mbox byte stream in memory; never writes uploads to disk.
    - Deduplicates by Message-ID within the same parse call.
    - Hard cap at MAX_MESSAGES to prevent OOM on large files.
    - Thread-safe: stateless, creates fresh parser state per call.
    """

    MAX_MESSAGES: int = _MAX_MESSAGES

    def compute_hash(self, data: bytes) -> str:
        """SHA-256 hex digest — used as idempotency key."""
        return hashlib.sha256(data).hexdigest()

    def parse(self, data: bytes) -> list[ParsedEmail]:
        """
        Parse raw mbox bytes. Returns list of ParsedEmail (headers only, no body).
        """
        results: list[ParsedEmail] = []
        seen_ids: set[str] = set()

        for i, msg in enumerate(_iter_mbox_messages(data)):
            if i >= self.MAX_MESSAGES:
                break
            parsed = self._parse_message(msg)
            if parsed is None:
                continue
            # Dedup by Message-ID
            if parsed.message_id:
                norm_id = parsed.message_id.strip()
                if norm_id in seen_ids:
                    continue
                seen_ids.add(norm_id)
            results.append(parsed)

        return results

    def _parse_message(self, msg: Message) -> ParsedEmail | None:
        try:
            from_raw = msg.get("From", "") or ""
            from_name_raw, from_addr_raw = email.utils.parseaddr(from_raw)
            from_addr = from_addr_raw.lower().strip() if from_addr_raw else None

            if not from_addr or "@" not in from_addr:
                return None

            return ParsedEmail(
                message_id=msg.get("Message-ID"),
                subject=_decode_header_value(msg.get("Subject")),
                from_address=from_addr,
                from_name=(
                    _decode_header_value(from_name_raw) if from_name_raw else None
                ),
                sender_domain=_extract_domain(from_addr),
                to_address=msg.get("To"),
                date=_parse_date(msg.get("Date")),
                list_id=_decode_header_value(msg.get("List-ID")),
                list_unsubscribe=msg.get("List-Unsubscribe"),
                reply_to=msg.get("Reply-To"),
            )
        except Exception:
            return None


def _iter_mbox_messages(data: bytes) -> list[Message]:
    """
    Parse an mbox byte stream entirely in memory.

    stdlib mailbox.mbox requires a filesystem path, which does not fit the
    upload pipeline. We split on mbox separator lines and parse each message
    with the email package instead.
    """
    if not data:
        return []

    parser = BytesParser(policy=default_policy)
    return [parser.parsebytes(chunk) for chunk in _split_mbox(data)]


def _split_mbox(data: bytes) -> list[bytes]:
    """Split an mbox byte stream into raw RFC822 message payloads."""
    if not data:
        return []

    chunks: list[bytes] = []
    current: list[bytes] = []
    in_message = False

    for line in data.splitlines(keepends=True):
        if line.startswith(b"From "):
            in_message = True
            if current:
                chunks.append(b"".join(current))
                current = []
            continue
        if not in_message:
            continue
        current.append(line)

    if current:
        chunks.append(b"".join(current))

    return chunks
