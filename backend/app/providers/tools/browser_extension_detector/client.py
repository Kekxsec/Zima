# backend/app/providers/tools/browser_extension_detector/client.py
from __future__ import annotations

import asyncio
import json
import platform
from pathlib import Path
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import ProviderError

# Browser profile root directories, keyed by (system, browser).
# Each entry is a list of candidate base directories (first readable one is used).
_PROFILE_ROOTS: dict[tuple[str, str], list[str]] = {
    ("darwin", "chrome"): [
        "~/Library/Application Support/Google/Chrome",
        "~/Library/Application Support/Google/Chrome Beta",
        "~/Library/Application Support/Google/Chrome Dev",
    ],
    ("darwin", "edge"): [
        "~/Library/Application Support/Microsoft Edge",
        "~/Library/Application Support/Microsoft Edge Beta",
    ],
    ("darwin", "brave"): [
        "~/Library/Application Support/BraveSoftware/Brave-Browser",
    ],
    ("darwin", "chromium"): [
        "~/Library/Application Support/Chromium",
    ],
    ("linux", "chrome"): [
        "~/.config/google-chrome",
        "~/.config/google-chrome-beta",
        "~/.config/google-chrome-unstable",
    ],
    ("linux", "edge"): [
        "~/.config/microsoft-edge",
        "~/.config/microsoft-edge-beta",
    ],
    ("linux", "brave"): [
        "~/.config/BraveSoftware/Brave-Browser",
    ],
    ("linux", "chromium"): [
        "~/.config/chromium",
    ],
    ("windows", "chrome"): [
        "~/AppData/Local/Google/Chrome/User Data",
    ],
    ("windows", "edge"): [
        "~/AppData/Local/Microsoft/Edge/User Data",
    ],
    ("windows", "brave"): [
        "~/AppData/Local/BraveSoftware/Brave-Browser/User Data",
    ],
    ("windows", "chromium"): [
        "~/AppData/Local/Chromium/User Data",
    ],
}

_FIREFOX_PROFILE_ROOTS: dict[str, list[str]] = {
    "darwin": ["~/Library/Application Support/Firefox/Profiles"],
    "linux": ["~/.mozilla/firefox"],
    "windows": ["~/AppData/Roaming/Mozilla/Firefox/Profiles"],
}

# Profile directory names in Chromium user-data dirs that are real profiles
# (not the root config directory itself).
_CHROMIUM_PROFILE_NAMES = frozenset({"Default", "Profile 1", "Profile 2", "Profile 3"})


def _iter_chromium_profiles(user_data_dir: Path) -> list[Path]:
    """Return all profile directories under a Chromium user data dir."""
    if not user_data_dir.is_dir():
        return []
    profiles: list[Path] = []
    for child in sorted(user_data_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name == "Default" or child.name.startswith("Profile "):
            profiles.append(child)
    return profiles


def _read_chromium_enabled_state(profile_dir: Path) -> dict[str, bool]:
    """Parse Secure Preferences to get extension enabled flags.

    Returns a dict of {extension_id: enabled} for all extensions.
    Missing extensions default to enabled=True.
    """
    prefs_path = profile_dir / "Secure Preferences"
    if not prefs_path.is_file():
        prefs_path = profile_dir / "Preferences"
    if not prefs_path.is_file():
        return {}
    try:
        data = json.loads(prefs_path.read_bytes())
        settings = data.get("extensions", {}).get("settings", {})
        return {
            ext_id: (entry.get("state", 1) == 1)
            for ext_id, entry in settings.items()
            if isinstance(entry, dict)
        }
    except (OSError, PermissionError, json.JSONDecodeError, ValueError):
        return {}


def _scan_chromium_extensions(
    browser: str, user_data_dir: Path
) -> list[dict[str, Any]]:
    """Enumerate extensions for all profiles under a Chromium user-data dir."""
    results: list[dict[str, Any]] = []
    for profile_dir in _iter_chromium_profiles(user_data_dir):
        extensions_dir = profile_dir / "Extensions"
        if not extensions_dir.is_dir():
            continue
        enabled_map = _read_chromium_enabled_state(profile_dir)
        for ext_dir in sorted(extensions_dir.iterdir()):
            if not ext_dir.is_dir():
                continue
            ext_id = ext_dir.name
            # Chromium extension IDs are 32 lowercase letters
            if len(ext_id) != 32 or not ext_id.isalpha():
                continue
            # Each version is a subdirectory; pick the lexicographically last one
            version_dirs = sorted(
                [d for d in ext_dir.iterdir() if d.is_dir()],
                key=lambda p: p.name,
            )
            if not version_dirs:
                continue
            version_dir = version_dirs[-1]
            manifest_path = version_dir / "manifest.json"
            if not manifest_path.is_file():
                continue
            try:
                manifest = json.loads(manifest_path.read_bytes())
            except (OSError, PermissionError, json.JSONDecodeError, ValueError):
                continue
            name = manifest.get("name", "")
            version = manifest.get("version", version_dir.name.rstrip("_0"))
            enabled = enabled_map.get(ext_id, True)
            results.append(
                {
                    "browser": browser,
                    "profile": profile_dir.name,
                    "extension_id": ext_id,
                    "name": name,
                    "version": version,
                    "path": str(version_dir),
                    "manifest": manifest,
                    "enabled": enabled,
                }
            )
    return results


def _read_firefox_enabled_state(profile_dir: Path) -> dict[str, bool]:
    """Parse extensions.json to get addon enabled flags."""
    ext_json = profile_dir / "extensions.json"
    if not ext_json.is_file():
        return {}
    try:
        data = json.loads(ext_json.read_bytes())
        addons = data.get("addons", [])
        state_map: dict[str, bool] = {}
        for addon in addons:
            if isinstance(addon, dict):
                addon_id = addon.get("id", "")
                active = addon.get("active", True)
                user_disabled = addon.get("userDisabled", False)
                if addon_id:
                    state_map[addon_id] = bool(active) and not bool(user_disabled)
        return state_map
    except (OSError, PermissionError, json.JSONDecodeError, ValueError):
        return {}


def _scan_firefox_profiles(profiles_root: Path) -> list[dict[str, Any]]:
    """Enumerate Firefox extensions across all profiles in a profiles root."""
    results: list[dict[str, Any]] = []
    if not profiles_root.is_dir():
        return results
    for profile_dir in sorted(profiles_root.iterdir()):
        if not profile_dir.is_dir():
            continue
        extensions_dir = profile_dir / "extensions"
        if not extensions_dir.is_dir():
            continue
        enabled_map = _read_firefox_enabled_state(profile_dir)
        for entry in sorted(extensions_dir.iterdir()):
            # Extensions may be .xpi files or directories named by ID
            if entry.is_file() and entry.suffix == ".xpi":
                ext_id = entry.stem
                # Read manifest.json from inside the XPI (it's a zip)
                manifest = _read_xpi_manifest(entry)
                if manifest is None:
                    continue
                name = manifest.get("name", "")
                version = manifest.get("version", "")
                enabled = enabled_map.get(ext_id, True)
                results.append(
                    {
                        "browser": "firefox",
                        "profile": profile_dir.name,
                        "extension_id": ext_id,
                        "name": name,
                        "version": version,
                        "path": str(entry),
                        "manifest": manifest,
                        "enabled": enabled,
                    }
                )
            elif entry.is_dir():
                manifest_path = entry / "manifest.json"
                if not manifest_path.is_file():
                    continue
                try:
                    manifest = json.loads(manifest_path.read_bytes())
                except (OSError, PermissionError, json.JSONDecodeError, ValueError):
                    continue
                ext_id = entry.name
                name = manifest.get("name", "")
                version = manifest.get("version", "")
                enabled = enabled_map.get(ext_id, True)
                results.append(
                    {
                        "browser": "firefox",
                        "profile": profile_dir.name,
                        "extension_id": ext_id,
                        "name": name,
                        "version": version,
                        "path": str(entry),
                        "manifest": manifest,
                        "enabled": enabled,
                    }
                )
    return results


def _read_xpi_manifest(xpi_path: Path) -> dict[str, Any] | None:
    """Extract manifest.json from an XPI (zip) file."""
    import zipfile

    try:
        with zipfile.ZipFile(xpi_path, "r") as zf:
            with zf.open("manifest.json") as f:
                return json.loads(f.read())
    except (OSError, PermissionError, KeyError, json.JSONDecodeError, ValueError):
        return None


def _do_scan() -> list[dict[str, Any]]:
    """Synchronous scan of all browser extension directories.

    Called via asyncio.to_thread so it does not block the event loop.
    """
    system = platform.system().lower()
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = (
        set()
    )  # (browser, profile, extension_id, version)

    # Chromium-based browsers
    chromium_browsers = ["chrome", "edge", "brave", "chromium"]
    for browser in chromium_browsers:
        candidate_roots = _PROFILE_ROOTS.get((system, browser), [])
        for root_str in candidate_roots:
            user_data_dir = Path(root_str).expanduser()
            if not user_data_dir.is_dir():
                continue
            try:
                found = _scan_chromium_extensions(browser, user_data_dir)
            except (OSError, PermissionError):
                continue
            for ext in found:
                key = (
                    ext["browser"],
                    ext["profile"],
                    ext["extension_id"],
                    ext["version"],
                )
                if key not in seen:
                    seen.add(key)
                    results.append(ext)
            break  # Use first accessible root for this browser

    # Firefox
    ff_roots = _FIREFOX_PROFILE_ROOTS.get(system, [])
    for root_str in ff_roots:
        profiles_root = Path(root_str).expanduser()
        if not profiles_root.is_dir():
            continue
        try:
            found = _scan_firefox_profiles(profiles_root)
        except (OSError, PermissionError):
            continue
        for ext in found:
            key = (ext["browser"], ext["profile"], ext["extension_id"], ext["version"])
            if key not in seen:
                seen.add(key)
                results.append(ext)
        break

    return results


class BrowserExtensionDetectorProvider(BaseProviderClient):
    """Local filesystem scanner that enumerates installed browser extensions.

    Scans Chrome, Edge, Brave, Chromium, and Firefox profile directories on
    the current host. Returns a list of installed extension records; does NOT
    assess risk or emit signals — it is utility-only.

    Supports macOS, Linux, and Windows. Safari App Extensions are out of scope
    (require Full Disk Access to the Safari container on modern macOS).

    No network requests are made. No API key is required.
    """

    name = "browser_extension_detector"

    def __init__(self, timeout_seconds: int = 30) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def scan(self) -> list[dict[str, Any]]:
        """Scan local browser profiles and return installed extension records.

        Each record contains:
          browser       — "chrome" | "edge" | "brave" | "chromium" | "firefox"
          profile       — profile directory name (e.g. "Default")
          extension_id  — extension ID string (32-char for Chromium, GUID for Firefox)
          name          — extension name from manifest
          version       — extension version string
          path          — absolute path to the extension version directory
          manifest      — parsed manifest.json dict
          enabled       — True if the extension is currently enabled

        Returns [] if no browser profiles or extensions are found.
        Raises ProviderError only on unrecoverable failures (e.g. asyncio error).
        Individual unreadable extensions are silently skipped.
        """
        try:
            results: list[dict[str, Any]] = await asyncio.to_thread(_do_scan)
        except Exception as exc:
            raise ProviderError(
                message=f"browser_extension_detector scan failed: {exc}",
                retryable=False,
            ) from exc
        return results
