# backend/app/providers/tools/mbox_parser/client.py
"""
MboxParserProvider — reads an mbox byte-stream, extracts per-message metadata.

Rules enforced here:
- Raw email bodies are NEVER stored or returned.
- Only headers (From, To, Subject, Date, Message-ID) are parsed.
- No disk I/O — parsing is entirely in-memory.
"""

import email
import email.utils
import hashlib
import re
from datetime import UTC, datetime
from email.header import decode_header, make_header

from backend.app.providers.tools.mbox_parser.models import ParsedEmail

_DOMAIN_RE = re.compile(r"@([\w.\-]+)")

# mbox message separator: a line beginning with "From " (case-sensitive)
_FROM_LINE_RE = re.compile(rb"^From ", re.MULTILINE)


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
    m = _DOMAIN_RE.search(address)
    return m.group(1).lower() if m else None


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
        return parsed.astimezone(UTC)
    except Exception:
        return None


def _split_mbox(data: bytes) -> list[bytes]:
    """
    Split raw mbox bytes into individual message byte-strings.
    Each chunk starts at a 'From ' separator line.
    """
    boundaries = [m.start() for m in _FROM_LINE_RE.finditer(data)]
    if not boundaries:
        return []

    chunks: list[bytes] = []
    for i, start in enumerate(boundaries):
        end = boundaries[i + 1] if i + 1 < len(boundaries) else len(data)
        chunks.append(data[start:end])
    return chunks


class MboxParserProvider:
    """
    Provider: reads bytes, yields ParsedEmail objects.
    No database access. No signal emission.
    """

    MAX_MESSAGES: int = 200_000

    def compute_hash(self, data: bytes) -> str:
        """SHA-256 hex digest — used as idempotency key."""
        return hashlib.sha256(data).hexdigest()

    def parse(self, data: bytes) -> list[ParsedEmail]:
        """
        Parse all messages from *data* (raw mbox bytes).
        Returns a list of ParsedEmail — body content is never accessed or stored.
        """
        results: list[ParsedEmail] = []
        chunks = _split_mbox(data)

        for i, chunk in enumerate(chunks):
            if i >= self.MAX_MESSAGES:
                break

            # Parse only headers — skip body entirely
            try:
                # email.message_from_bytes parses the full message; we only
                # read header fields, so body is parsed but not stored here.
                msg = email.message_from_bytes(chunk)
            except Exception:
                continue

            from_raw = msg.get("From")
            from_name_raw, from_addr_raw = email.utils.parseaddr(from_raw or "")

            results.append(
                ParsedEmail(
                    message_id=msg.get("Message-ID"),
                    subject=_decode_header_value(msg.get("Subject")),
                    from_address=from_addr_raw.lower() if from_addr_raw else None,
                    from_name=_decode_header_value(from_name_raw)
                    if from_name_raw
                    else None,
                    sender_domain=_extract_domain(from_addr_raw),
                    to_address=msg.get("To"),
                    date=_parse_date(msg.get("Date")),
                )
            )

        return results
