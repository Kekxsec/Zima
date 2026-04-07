# backend/app/providers/tools/firefox_enterprise_policies/client.py
from __future__ import annotations

import asyncio
import json
import platform
from pathlib import Path
from typing import Any

from backend.app.providers.base.client import BaseProviderClient

# Default policy file paths per OS
_DEFAULT_PATHS: dict[str, list[str]] = {
    "darwin": [
        "/Library/Preferences/org.mozilla.firefox.plist",
        "/Library/Application Support/Mozilla/policies/policies.json",
    ],
    "linux": [
        "/usr/lib/firefox/distribution/policies.json",
        "/etc/firefox/policies/policies.json",
        "/usr/lib/firefox-esr/distribution/policies.json",
    ],
    "windows": [
        # Registry not supported via file path; pass an exported JSON path explicitly.
    ],
}


class FirefoxEnterprisePoliciesProvider(BaseProviderClient):
    """Read Firefox enterprise policies from a policies.json file.

    Accepts a `policy_path` pointing to Firefox's policies.json.
    Returns a list of policy finding dicts; each has `policy_key` and `value`.

    Does NOT make HTTP requests — reads from the local filesystem.
    """

    name = "firefox_enterprise_policies"

    def __init__(self, timeout_seconds: int = 15) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def read_policies(
        self, policy_path: str | None = None
    ) -> list[dict[str, Any]]:
        """Read Firefox enterprise policies from a JSON policy file.

        If `policy_path` is None, tries platform-default paths.
        Returns list of dicts with keys: policy_key, value, source_path.
        Returns [] if no policy file found or file is unreadable.
        """
        paths_to_try: list[str] = []
        if policy_path:
            paths_to_try.append(policy_path)
        else:
            system = platform.system().lower()
            paths_to_try.extend(_DEFAULT_PATHS.get(system, []))

        for path_str in paths_to_try:
            p = Path(path_str)
            if not p.exists() or not p.is_file():
                continue
            try:
                content = await asyncio.to_thread(p.read_text, encoding="utf-8")
                data = json.loads(content)
                return self._parse_policy_dict(data, str(p))
            except (OSError, PermissionError, json.JSONDecodeError):
                continue

        return []

    @staticmethod
    def _parse_policy_dict(
        data: dict[str, Any], source_path: str
    ) -> list[dict[str, Any]]:
        """Flatten a policies.json into a list of {policy_key, value, source_path} dicts.

        Firefox policies.json has the structure: {"policies": {"PolicyName": value, ...}}
        """
        findings: list[dict[str, Any]] = []
        if not isinstance(data, dict):
            return findings
        policies = data.get("policies", data)
        if not isinstance(policies, dict):
            return findings
        for key, value in policies.items():
            findings.append(
                {"policy_key": key, "value": value, "source_path": source_path}
            )
        return findings
