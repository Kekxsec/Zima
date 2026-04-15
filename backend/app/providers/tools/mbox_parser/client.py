# backend/app/providers/tools/mbox_parser/client.py
"""
MboxParserProvider — reads an mbox byte-stream, extracts per-message metadata.

Rules enforced here:
- Raw email bodies are NEVER stored or returned.
- Only headers (From, To, Subject, Date, Message-ID, List-*) are parsed.
- Supports both in-memory bytes and temp-file parsing so uploads do not need
  to be materialised twice in memory.
- Deduplicates by Message-ID within the same parse call.
"""

from __future__ import annotations

import email
import email.utils
import hashlib
import io
from collections.abc import Iterator
from datetime import UTC, datetime
from email.header import decode_header, make_header
from email.message import Message
from email.parser import BytesParser
from email.policy import default as default_policy
from pathlib import Path
from typing import BinaryIO

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


def _normalise_addresses(raw: str | None) -> list[str]:
    if not raw:
        return []

    addresses: list[str] = []
    seen: set[str] = set()
    for _, addr in email.utils.getaddresses([raw]):
        normalised = addr.strip().lower()
        if "@" not in normalised or normalised in seen:
            continue
        seen.add(normalised)
        addresses.append(normalised)
    return addresses


def _extract_references(raw: str | None) -> list[str]:
    if not raw:
        return []
    references: list[str] = []
    seen: set[str] = set()
    for token in raw.split():
        ref = token.strip()
        if not ref:
            continue
        if not ref.startswith("<"):
            ref = f"<{ref}>"
        if not ref.endswith(">"):
            ref = f"{ref}>"
        ref = ref.lower()
        if ref in seen:
            continue
        seen.add(ref)
        references.append(ref)
    return references


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
    Parses a raw mbox file into a list of ParsedEmail objects.

    - Supports bytes and temp-file inputs without loading the upload twice.
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
        return list(self.iter_parse(data))

    def parse_file(self, path: str | Path) -> list[ParsedEmail]:
        """Parse an mbox file from disk without materialising it as bytes first."""
        return list(self.iter_parse_file(path))

    def iter_parse(self, data: bytes) -> Iterator[ParsedEmail]:
        """Yield ParsedEmail records one at a time from an mbox byte stream."""
        yield from self._iter_parsed_messages(
            _iter_mbox_messages_from_stream(io.BytesIO(data))
        )

    def iter_parse_file(self, path: str | Path) -> Iterator[ParsedEmail]:
        """Yield ParsedEmail records one at a time from an mbox file on disk."""
        with Path(path).open("rb") as stream:
            yield from self._iter_parsed_messages(
                _iter_mbox_messages_from_stream(stream)
            )

    def _iter_parsed_messages(
        self,
        messages: Iterator[tuple[Message, int]],
    ) -> Iterator[ParsedEmail]:
        """Normalise and deduplicate a message stream into ParsedEmail objects."""
        seen_keys: set[str] = set()

        for i, (msg, message_size_bytes) in enumerate(messages):
            if i >= self.MAX_MESSAGES:
                break
            parsed = self._parse_message(msg, message_size_bytes)
            if parsed is None:
                continue
            dedup_key = _build_dedup_key(parsed)
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)
            yield parsed

    def _parse_message(
        self,
        msg: Message,
        message_size_bytes: int,
    ) -> ParsedEmail | None:
        try:
            from_raw = msg.get("From", "") or ""
            from_name_raw, from_addr_raw = email.utils.parseaddr(from_raw)
            from_addr = from_addr_raw.lower().strip() if from_addr_raw else None
            to_addresses = _normalise_addresses(msg.get("To"))
            reply_to_addresses = _normalise_addresses(msg.get("Reply-To"))

            if not from_addr or "@" not in from_addr:
                return None

            return ParsedEmail(
                message_id=(msg.get("Message-ID") or "").strip().lower() or None,
                subject=_decode_header_value(msg.get("Subject")),
                from_address=from_addr,
                from_name=(
                    _decode_header_value(from_name_raw) if from_name_raw else None
                ),
                sender_domain=_extract_domain(from_addr),
                to_address=to_addresses[0] if to_addresses else None,
                to_addresses=to_addresses,
                date=_parse_date(msg.get("Date")),
                references=_extract_references(msg.get("References")),
                list_id=_decode_header_value(msg.get("List-ID")),
                list_unsubscribe=msg.get("List-Unsubscribe"),
                precedence=_decode_header_value(msg.get("Precedence")),
                reply_to=reply_to_addresses[0] if reply_to_addresses else None,
                mime_type=msg.get_content_type(),
                message_size_bytes=message_size_bytes,
            )
        except Exception:
            return None


def _iter_mbox_messages_from_stream(
    stream: BinaryIO,
) -> Iterator[tuple[Message, int]]:
    """
    Parse an mbox byte stream incrementally from a binary stream.

    stdlib mailbox.mbox requires a filesystem path, which does not fit the
    upload pipeline well. We iterate over one message chunk at a time so large
    mbox uploads do not materialise every message twice in memory.
    """
    parser = BytesParser(policy=default_policy)
    for chunk in _iter_mbox_chunks_from_stream(stream):
        yield parser.parsebytes(chunk), len(chunk)


def _split_mbox(data: bytes) -> list[bytes]:
    """Split an mbox byte stream into raw RFC822 message payloads."""
    return list(_iter_mbox_chunks_from_stream(io.BytesIO(data)))


def _iter_mbox_chunks_from_stream(stream: BinaryIO) -> Iterator[bytes]:
    """Yield one raw RFC822 message payload at a time from an mbox stream."""
    current = bytearray()
    in_message = False

    while True:
        line = stream.readline()
        if not line:
            break
        if line.startswith(b"From "):
            in_message = True
            if current:
                yield bytes(current)
                current.clear()
            continue
        if not in_message:
            continue
        current.extend(line)

    if current:
        yield bytes(current)


def _build_dedup_key(parsed: ParsedEmail) -> str:
    """Build a stable deduplication key for one parsed message."""
    if parsed.message_id:
        return f"message-id:{parsed.message_id}"

    minute_bucket = ""
    if parsed.date is not None:
        minute_bucket = str(int(parsed.date.timestamp() // 60))

    fallback = "|".join(
        [
            parsed.from_address or "",
            parsed.to_address or "",
            (parsed.subject or "").strip().lower(),
            minute_bucket,
        ]
    )
    digest = hashlib.sha256(fallback.encode("utf-8")).hexdigest()
    return f"fallback:{digest}"
