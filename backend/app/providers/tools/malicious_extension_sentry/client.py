# backend/app/providers/tools/malicious_extension_sentry/client.py
from __future__ import annotations

import csv
import io
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import ProviderError

# GitHub raw URL for the simple (plain ID list) CSV.
# Maintained by toborrm9 — updated nearly daily with known-malicious Chrome/Edge IDs.
_DEFAULT_CSV_URL = (
    "https://raw.githubusercontent.com/"
    "toborrm9/malicious_extension_sentry/main/Malicious-Extensions.csv"
)

# Detailed CSV URL: ID, Name, source URL, date added
_DETAILED_CSV_URL = (
    "https://raw.githubusercontent.com/"
    "toborrm9/malicious_extension_sentry/main/malicious_extensions_detailed.csv"
)


class _DbEntry:
    __slots__ = ("extension_id", "name", "date_added", "source_url")

    def __init__(
        self,
        extension_id: str,
        name: str = "",
        date_added: str = "",
        source_url: str = "",
    ) -> None:
        self.extension_id = extension_id.strip().lower()
        self.name = name.strip()
        self.date_added = date_added.strip()
        self.source_url = source_url.strip()


class MaliciousExtensionSentryProvider(BaseProviderClient):
    """Local-lookup provider for known-malicious Chrome/Edge extension IDs.

    Fetches a CSV database of known-malicious extension IDs from the
    `toborrm9/malicious_extension_sentry` GitHub repository and performs
    exact-match lookups against installed extension IDs.

    Coverage: Chrome and Chromium-based Edge extensions only. Firefox add-ons
    use a different ID scheme and are not in scope for this database.

    The database is cached in memory for the lifetime of the provider instance.
    No data is sent to any external service — only a one-time HTTP GET is made
    to fetch the CSV.

    Reliability: medium (community-maintained, not official vendor feed).
    Updated daily by the maintainer.
    """

    name = "malicious_extension_sentry"

    def __init__(
        self,
        csv_url: str = _DETAILED_CSV_URL,
        timeout_seconds: int = 20,
    ) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self._csv_url = csv_url
        # In-memory cache: extension_id → _DbEntry
        self._db: dict[str, _DbEntry] | None = None

    async def load_database(self) -> dict[str, _DbEntry]:
        """Fetch and parse the malicious extension CSV database.

        Returns a dict of {lowercase_extension_id: _DbEntry}.
        Returns {} if the database cannot be fetched (degrades gracefully).
        """
        if self._db is not None:
            return self._db

        try:
            raw = await self._get(self._csv_url, label="malicious_extension_sentry")
        except Exception:
            # Any fetch failure degrades gracefully — return empty dict
            self._db = {}
            return self._db

        if not isinstance(raw, str | bytes):
            # _get returns parsed JSON for non-text; fall back to plain CSV fetch
            raw_text = await self._fetch_raw_text(self._csv_url)
        else:
            raw_text = (
                raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")
            )

        self._db = self._parse_csv(raw_text)
        return self._db

    async def _fetch_raw_text(self, url: str) -> str:
        """Fetch raw text content (CSV) from a URL."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                resp = await client.get(url)
        except Exception:
            return ""
        if resp.status_code != 200:
            return ""
        return resp.text

    @staticmethod
    def _parse_csv(raw: str) -> dict[str, _DbEntry]:
        """Parse the malicious extensions CSV into an id→entry map.

        Handles both the simple (id-only) CSV and the detailed (id, name,
        source, date) CSV. Rows with malformed or short IDs are skipped.
        """
        db: dict[str, _DbEntry] = {}
        if not raw.strip():
            return db
        try:
            reader = csv.reader(io.StringIO(raw))
            for row in reader:
                if not row:
                    continue
                ext_id = row[0].strip().lower()
                # Chromium extension IDs are exactly 32 lowercase letters
                if not ext_id or len(ext_id) != 32:
                    continue
                name = row[1].strip() if len(row) > 1 else ""
                source_url = row[2].strip() if len(row) > 2 else ""
                date_added = row[3].strip() if len(row) > 3 else ""
                db[ext_id] = _DbEntry(
                    extension_id=ext_id,
                    name=name,
                    date_added=date_added,
                    source_url=source_url,
                )
        except (csv.Error, UnicodeDecodeError):
            pass
        return db

    async def check_extensions(self, extension_ids: list[str]) -> list[dict[str, Any]]:
        """Check a list of extension IDs against the malicious extensions database.

        Returns a list of match dicts for any extensions found in the database.
        Each match dict contains:
          extension_id  — the matched extension ID
          name          — extension name from the database (may be empty)
          date_added    — date the ID was added to the database (may be empty)
          source_url    — reference URL for the discovery report (may be empty)

        Returns [] if no matches are found or the database cannot be loaded.
        Raises ProviderError if extension_ids is non-empty and a fatal error occurs.
        """
        if not extension_ids:
            return []

        try:
            db = await self.load_database()
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                message=f"malicious_extension_sentry: failed to load database: {exc}",
                retryable=True,
            ) from exc

        matches: list[dict[str, Any]] = []
        for raw_id in extension_ids:
            normalized = raw_id.strip().lower()
            if not normalized:
                continue
            entry = db.get(normalized)
            if entry is not None:
                matches.append(
                    {
                        "extension_id": entry.extension_id,
                        "name": entry.name,
                        "date_added": entry.date_added,
                        "source_url": entry.source_url,
                    }
                )
        return matches

    async def database_size(self) -> int:
        """Return the number of entries in the loaded database (for diagnostics)."""
        db = await self.load_database()
        return len(db)
