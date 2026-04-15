# tests/unit/email_accounts/test_mbox_parser.py
"""Unit tests for the mbox parser provider."""

from pathlib import Path

from backend.app.providers.tools.mbox_parser.client import (
    MboxParserProvider,
    _split_mbox,
)


def _make_mbox(*messages: tuple[str, str, str]) -> bytes:
    """Build a minimal mbox byte-string from (from_addr, subject, date) tuples."""
    lines: list[bytes] = []
    for i, (from_addr, subject, date_str) in enumerate(messages):
        lines.append(f"From {from_addr} {date_str}\n".encode())
        lines.append(f"From: {from_addr}\n".encode())
        lines.append(b"To: testuser@example.com\n")
        lines.append(f"Subject: {subject}\n".encode())
        lines.append(f"Date: {date_str}\n".encode())
        lines.append(f"Message-ID: <test-{i}@example.com>\n".encode())
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
        assert e.to_address == "testuser@example.com"
        assert e.subject == "Welcome to GitHub"
        assert e.date is not None
        assert e.mime_type == "text/plain"
        assert e.message_size_bytes is not None
        assert e.message_size_bytes > 0

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

    def test_normalises_addresses_and_extracts_references(self) -> None:
        data = (
            b"From NoReply@GitHub.com Mon, 01 Jan 2024 10:00:00 +0000\n"
            b"From: GitHub <NoReply@GitHub.com>\n"
            b"To: USER@Example.com, Second@Example.com\n"
            b"Reply-To: Support@GitHub.com\n"
            b"Subject: Welcome to GitHub\n"
            b"Date: Mon, 01 Jan 2024 10:00:00 +0000\n"
            b"Message-ID: <Case@Test.Example>\n"
            b"References: <Prev@Test.Example> next@test.example\n"
            b"List-Unsubscribe: <https://example.com/unsub>\n"
            b"Content-Type: text/html; charset=UTF-8\n"
            b"\n"
            b"<html><body>Hello</body></html>\n"
        )

        emails = self.parser.parse(data)

        assert len(emails) == 1
        email_obj = emails[0]
        assert email_obj.from_address == "noreply@github.com"
        assert email_obj.to_address == "user@example.com"
        assert email_obj.to_addresses == ["user@example.com", "second@example.com"]
        assert email_obj.reply_to == "support@github.com"
        assert email_obj.message_id == "<case@test.example>"
        assert email_obj.references == ["<prev@test.example>", "<next@test.example>"]
        assert email_obj.list_unsubscribe == "<https://example.com/unsub>"
        assert email_obj.mime_type == "text/html"

    def test_deduplicates_without_message_id_using_fallback_hash(self) -> None:
        data = (
            b"From sender@example.com Mon, 01 Jan 2024 10:00:05 +0000\n"
            b"From: Sender <sender@example.com>\n"
            b"To: user@example.com\n"
            b"Subject: Welcome to Example\n"
            b"Date: Mon, 01 Jan 2024 10:00:05 +0000\n"
            b"\n"
            b"Body one.\n"
            b"From sender@example.com Mon, 01 Jan 2024 10:00:45 +0000\n"
            b"From: Sender <sender@example.com>\n"
            b"To: user@example.com\n"
            b"Subject: Welcome to Example\n"
            b"Date: Mon, 01 Jan 2024 10:00:45 +0000\n"
            b"\n"
            b"Body two.\n"
        )

        emails = self.parser.parse(data)

        assert len(emails) == 1

    def test_iter_parse_supports_large_message_sets(self) -> None:
        data = _make_mbox(
            *[
                (
                    f"sender{i}@example.com",
                    f"msg{i}",
                    "Mon, 01 Jan 2024 00:00:00 +0000",
                )
                for i in range(1000)
            ]
        )

        emails = list(self.parser.iter_parse(data))

        assert len(emails) == 1000

    def test_parse_file_streams_from_disk(self, tmp_path: Path) -> None:
        data = _make_mbox(
            ("noreply@github.com", "Welcome", "Mon, 01 Jan 2024 00:00:00 +0000"),
            ("noreply@spotify.com", "Verify", "Tue, 02 Jan 2024 00:00:00 +0000"),
        )
        upload_path = tmp_path / "upload.mbox"
        upload_path.write_bytes(data)

        emails = self.parser.parse_file(upload_path)

        assert [email.sender_domain for email in emails] == [
            "github.com",
            "spotify.com",
        ]
