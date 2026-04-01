# tests/unit/email_accounts/test_mbox_parser.py
"""Unit tests for the mbox parser provider."""

from backend.app.providers.tools.mbox_parser.client import (
    MboxParserProvider,
    _split_mbox,
)


def _make_mbox(*messages: tuple[str, str, str]) -> bytes:
    """Build a minimal mbox byte-string from (from_addr, subject, date) tuples."""
    lines: list[bytes] = []
    for from_addr, subject, date_str in messages:
        lines.append(f"From {from_addr} {date_str}\n".encode())
        lines.append(f"From: {from_addr}\n".encode())
        lines.append(f"Subject: {subject}\n".encode())
        lines.append(f"Date: {date_str}\n".encode())
        lines.append(b"Message-ID: <test@example.com>\n")
        lines.append(b"\n")
        lines.append(b"Body line.\n\n")
    return b"".join(lines)


class TestMboxSplitter:
    def test_empty_bytes_returns_empty(self) -> None:
        assert _split_mbox(b"") == []

    def test_no_from_line_returns_empty(self) -> None:
        assert _split_mbox(b"Not an mbox file\n") == []

    def test_single_message(self) -> None:
        data = _make_mbox(("a@b.com", "Hi", "Mon, 1 Jan 2024 00:00:00 +0000"))
        chunks = _split_mbox(data)
        assert len(chunks) == 1

    def test_two_messages(self) -> None:
        data = _make_mbox(
            ("a@b.com", "First", "Mon, 1 Jan 2024 00:00:00 +0000"),
            ("c@d.com", "Second", "Tue, 2 Jan 2024 00:00:00 +0000"),
        )
        chunks = _split_mbox(data)
        assert len(chunks) == 2


class TestMboxParserProvider:
    def setup_method(self) -> None:
        self.parser = MboxParserProvider()

    def test_parse_empty_returns_empty(self) -> None:
        assert self.parser.parse(b"") == []

    def test_parse_single_message_extracts_headers(self) -> None:
        data = _make_mbox(
            (
                "noreply@github.com",
                "Welcome to GitHub",
                "Mon, 01 Jan 2024 10:00:00 +0000",
            )
        )
        emails = self.parser.parse(data)
        assert len(emails) == 1
        e = emails[0]
        assert e.from_address == "noreply@github.com"
        assert e.sender_domain == "github.com"
        assert e.subject == "Welcome to GitHub"
        assert e.date is not None

    def test_parse_multiple_messages(self) -> None:
        data = _make_mbox(
            ("a@github.com", "Welcome", "Mon, 01 Jan 2024 00:00:00 +0000"),
            ("b@spotify.com", "Verify", "Tue, 02 Jan 2024 00:00:00 +0000"),
            ("c@netflix.com", "Confirm", "Wed, 03 Jan 2024 00:00:00 +0000"),
        )
        emails = self.parser.parse(data)
        assert len(emails) == 3
        assert emails[0].sender_domain == "github.com"
        assert emails[1].sender_domain == "spotify.com"
        assert emails[2].sender_domain == "netflix.com"

    def test_domain_extracted_correctly(self) -> None:
        data = _make_mbox(
            ("no-reply@sub.example.co.uk", "Hi", "Mon, 1 Jan 2024 00:00:00 +0000")
        )
        emails = self.parser.parse(data)
        assert emails[0].sender_domain == "sub.example.co.uk"

    def test_compute_hash_is_deterministic(self) -> None:
        data = b"some mbox content"
        assert self.parser.compute_hash(data) == self.parser.compute_hash(data)

    def test_compute_hash_changes_with_content(self) -> None:
        assert self.parser.compute_hash(b"aaa") != self.parser.compute_hash(b"bbb")

    def test_date_normalised_to_utc(self) -> None:
        data = _make_mbox(("a@b.com", "Hi", "Mon, 01 Jan 2024 12:00:00 +0500"))
        emails = self.parser.parse(data)
        assert emails[0].date is not None
        assert emails[0].date.tzinfo is not None
        assert emails[0].date.utcoffset().total_seconds() == 0  # type: ignore[union-attr]

    def test_respects_max_messages_cap(self) -> None:
        parser = MboxParserProvider()
        parser.MAX_MESSAGES = 3
        data = _make_mbox(
            *[
                ("a@b.com", f"msg{i}", "Mon, 01 Jan 2024 00:00:00 +0000")
                for i in range(10)
            ]
        )
        emails = parser.parse(data)
        assert len(emails) == 3
