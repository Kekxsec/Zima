# backend/app/providers/tools/get_browser_extension_info/client.py
from __future__ import annotations

from typing import Any

from backend.app.providers.base.client import BaseProviderClient

# Permissions that indicate elevated risk — broad access or data-sensitive APIs.
SENSITIVE_PERMISSIONS: frozenset[str] = frozenset(
    [
        "<all_urls>",
        "*://*/*",
        "http://*/*",
        "https://*/*",
        "tabs",
        "webRequest",
        "webRequestBlocking",
        "cookies",
        "clipboardRead",
        "clipboardWrite",
        "nativeMessaging",
        "debugger",
        "management",
        "proxy",
        "history",
        "bookmarks",
        "identity",
        "downloads",
        "downloads.open",
        "storage",
        "unlimitedStorage",
    ]
)


class GetBrowserExtensionInfoProvider(BaseProviderClient):
    """Manifest parser and metadata normalizer for browser extensions.

    Converts a raw manifest.json dict (from browser_extension_detector) into a
    structured, normalized metadata object. Enrichment-only — no signals are
    emitted by this provider.

    No network requests, no I/O, no API key required.
    """

    name = "get_browser_extension_info"

    def __init__(self) -> None:
        super().__init__(timeout_seconds=0)

    def extract_metadata(
        self,
        manifest: dict[str, Any],
        browser: str,
        extension_id: str,
        *,
        enabled: bool = True,
        install_path: str = "",
    ) -> dict[str, Any]:
        """Normalize raw manifest data into a structured metadata dict.

        Returns a dict with the following fields (absent optional fields are
        omitted rather than set to None):
          extension_id        — the extension's unique ID
          browser             — which browser owns this extension
          name                — extension name
          version             — version string
          description         — human-readable description (optional)
          author              — author / developer name (optional)
          manifest_version    — 2 or 3
          permissions         — list of required permission strings
          optional_permissions — list of optional permission strings
          host_permissions    — list of host match patterns (MV3)
          optional_host_permissions — list of optional host patterns (MV3)
          content_scripts     — list of content script entries
          background          — background script / service worker info
          update_url          — extension update URL (optional)
          homepage_url        — developer homepage (optional)
          store_url           — derived store listing URL
          sensitive_permissions — subset of permissions that are security-sensitive
          enabled             — whether the extension is currently enabled
          install_path        — local filesystem path to the extension
        """
        permissions: list[str] = manifest.get("permissions") or []
        optional_permissions: list[str] = manifest.get("optional_permissions") or []
        host_permissions: list[str] = manifest.get("host_permissions") or []
        optional_host_permissions: list[str] = (
            manifest.get("optional_host_permissions") or []
        )
        content_scripts: list[dict[str, Any]] = manifest.get("content_scripts") or []
        background_raw = manifest.get("background") or {}
        manifest_version = manifest.get("manifest_version", 2)

        # Normalize background section
        background: dict[str, Any] = {}
        if isinstance(background_raw, dict):
            if "service_worker" in background_raw:
                background["service_worker"] = background_raw["service_worker"]
            if "scripts" in background_raw:
                background["scripts"] = background_raw["scripts"]
            if "persistent" in background_raw:
                background["persistent"] = background_raw["persistent"]

        # Derive store URL from extension ID and browser
        store_url = _derive_store_url(browser, extension_id)

        # Author: Firefox supports 'author' field; Chrome uses developer.name or author
        author = manifest.get("author") or ""
        developer = manifest.get("developer") or {}
        if not author and isinstance(developer, dict):
            author = developer.get("name") or developer.get("email") or ""

        # All permission strings that are sensitive
        all_permissions = set(permissions) | set(host_permissions)
        sensitive = sorted(all_permissions & SENSITIVE_PERMISSIONS)

        meta: dict[str, Any] = {
            "extension_id": extension_id,
            "browser": browser,
            "name": manifest.get("name") or "",
            "version": manifest.get("version") or "",
            "manifest_version": manifest_version,
            "permissions": list(permissions),
            "optional_permissions": list(optional_permissions),
            "host_permissions": list(host_permissions),
            "optional_host_permissions": list(optional_host_permissions),
            "content_scripts": content_scripts,
            "background": background,
            "sensitive_permissions": sensitive,
            "enabled": enabled,
        }

        # Optional fields — only include if present
        if manifest.get("description"):
            meta["description"] = manifest["description"]
        if author:
            meta["author"] = author
        if manifest.get("update_url"):
            meta["update_url"] = manifest["update_url"]
        if manifest.get("homepage_url"):
            meta["homepage_url"] = manifest["homepage_url"]
        if store_url:
            meta["store_url"] = store_url
        if install_path:
            meta["install_path"] = install_path

        return meta


def _derive_store_url(browser: str, extension_id: str) -> str:
    """Derive a browser extension store listing URL from the browser and ID."""
    if not extension_id:
        return ""
    b = browser.lower()
    if b in {"chrome", "chromium", "brave"}:
        return f"https://chrome.google.com/webstore/detail/{extension_id}"
    if b == "edge":
        return f"https://microsoftedge.microsoft.com/addons/detail/{extension_id}"
    if b == "firefox":
        return f"https://addons.mozilla.org/firefox/addon/{extension_id}/"
    return ""
