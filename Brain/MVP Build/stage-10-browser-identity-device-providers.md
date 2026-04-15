---
tags: [zima, mvp, stage-10, browser, device, identity, providers, modules]
created: 2026-04-02
updated: 2026-04-14
status: in_progress
related:
  - "[[Zima]]"
  - "[[stage-10-16-implementation-plan]]"
---

> **Status note (2026-04-14):** The identity social providers in the context table below (emailformat, gravatar, emailcrawlr, skymem) have been completed — schemas and mappers added in Stage 10b. The browser and device pillar work (Stages 12–13) has not started. The async client fixes for emailcrawlr and crxcavator were resolved as part of Stage 10b.

← [[MVP Master|Stage Progress]]

# Stage 10 — Browser, Device, and Identity Provider Completion

This stage implements the full provider + module layer for the three pillars that have completed research but no working code:

- **Browser pillar** — `browser_configuration`, `extension_risk`, `browser_inventory` modules
- **Device pillar** — `software_inventory` module
- **Identity pillar** — enhance `username_exposure` and `alias_correlation` with new providers

Exit condition: all modules below emit correctly-structured signals (or enrichment) from their providers, provider failures degrade gracefully, and integration tests cover the primary success and failure paths.

---

## Context

Research is complete for 11 providers. Key facts:

| Provider | Category | Role | Target Modules |
|---|---|---|---|
| `chromium_enterprise_policies` | tools | direct_signal_input | `browser_configuration` |
| `firefox_enterprise_policies` | tools | direct_signal_input | `browser_configuration` |
| `crxcavator` | threat_intel | direct_signal_input | `extension_risk` |
| `chrome_web_store_api` | cloud | enrichment_only | `extension_risk`, `browser_inventory` |
| `firefox_addons_site_api` | cloud | enrichment_only | `extension_risk`, `browser_inventory` |
| `emailformat` | social | enrichment_only | `alias_correlation` |
| `gravatar` | social | enrichment_only | `username_exposure` |
| `emailcrawlr` | social | direct_signal_input | `username_exposure` |
| `skymem` | social | enrichment_only | `username_exposure` |
| `syft` | tools | direct_signal_input | `software_inventory` |
| `truecaller` | phone | **DEFERRED** | `phone_exposure` (no API) |

Provider clients for `emailcrawlr` and `crxcavator` already exist but have synchronous `self._fetch()` calls that need updating to `await self._get()`.

---

## Part A — Provider Client Fixes (Pre-work)

Before any module work, fix the two existing provider clients that use the wrong base class call pattern.

### A.1 Fix `emailcrawlr` client

`backend/app/providers/social/emailcrawlr/client.py` uses `self._fetch()` (synchronous) instead of `await self._get()`. Update to async pattern consistent with `HibpProvider`.

Key changes:
- Add `super().__init__(timeout_seconds=timeout_seconds)` to `__init__`
- Replace all `self._fetch(url)` calls with `await self._get(url, headers=headers)`
- Return `list[dict[str, Any]]` from `search_emails`

### A.2 Fix `crxcavator` client

`backend/app/providers/threat_intel/crxcavator/client.py` uses `self._fetch()` and needs the same async conversion.

Key changes:
- Add `super().__init__(timeout_seconds=timeout_seconds)`
- Replace `self._fetch(url)` with `await self._get(url)`
- The existing `check_extensions(domain)` method searches by domain — also add `check_extension(extension_id: str)` which calls `GET /v1/report/{extension_id}/{version}` for a specific extension ID
- Return `list[dict[str, Any]]` from both methods

---

## Part B — Browser Configuration Module

**New module:** `backend/app/modules/browser/browser_configuration/`

### B.1 New provider clients

#### `backend/app/providers/tools/chromium_enterprise_policies/client.py`

This is a **local reader**, not an HTTP client. It reads Chrome/Chromium enterprise policy JSON from the local filesystem or registry.

```
class ChromiumEnterprisePoliciesProvider(BaseProviderClient):
    name = "chromium_enterprise_policies"

    async def read_policies(self, policy_path: str) -> list[dict[str, Any]]:
        """
        Read Chrome enterprise policies from a JSON file (Chrome Management API export
        or local policy.json). Returns list of policy finding dicts.
        """
```

**Policy paths by platform:**
- macOS: `/Library/Managed Preferences/com.google.Chrome.plist` or Chrome policy JSON
- Windows: Registry `HKLM\SOFTWARE\Policies\Google\Chrome`
- Cross-platform JSON: passed in as `policy_path` parameter

**Signals produced by this provider** (from research):

| signal_type | severity | trigger_condition |
|---|---|---|
| `extension_force_installed` | low | `ExtensionInstallForcelist` is non-empty |
| `safe_browsing_disabled` | high | `SafeBrowsingEnabled = false` |
| `third_party_cookies_allowed` | medium | `BlockThirdPartyCookies = false` or policy absent |

#### `backend/app/providers/tools/firefox_enterprise_policies/client.py`

Reads Firefox enterprise policies from `policies.json` or Windows registry.

```
class FirefoxEnterprisePoliciesProvider(BaseProviderClient):
    name = "firefox_enterprise_policies"

    async def read_policies(self, policy_path: str) -> list[dict[str, Any]]:
```

**Policy paths by platform:**
- macOS: `/Library/Application Support/Mozilla/policies/policies.json`
- Windows: Registry `HKLM\SOFTWARE\Policies\Mozilla\Firefox`
- Cross-platform: `distribution/policies.json` next to Firefox binary

**Signals produced** (from research, 12 signals):

| signal_type | severity | trigger_condition |
|---|---|---|
| `browser_update_disabled` | medium | `DisableAppUpdate = true` or `AppAutoUpdate = false` |
| `browser_update_pinned` | low | `AppUpdatePin` is set |
| `browser_update_url_changed` | medium | `AppUpdateURL` is non-default |
| `dns_over_https_disabled` | low | `DNSOverHTTPS.Enabled = false` |
| `tracking_protection_disabled` | low | `EnableTrackingProtection.Value = false` |
| `tracking_cryptomining_disabled` | low | `EnableTrackingProtection.Cryptomining = false` |
| `tracking_fingerprinting_disabled` | low | `EnableTrackingProtection.Fingerprinting = false` |
| `tracking_email_disabled` | low | `EnableTrackingProtection.EmailTracking = false` |
| `cookies_third_party_allowed` | low | `Cookies.Behavior != "reject-foreign"` |
| `private_browsing_disabled` | low | `DisablePrivateBrowsing = true` |
| `password_manager_disabled` | low | `PasswordManagerEnabled = false` |
| `extension_updates_disabled` | low | `ExtensionUpdate = false` |

### B.2 Module structure

Create `backend/app/modules/browser/` domain with `__init__.py`.

Create `backend/app/modules/browser/browser_configuration/`:
- `__init__.py`
- `service.py` — `BrowserConfigurationService(BaseModuleService)`
- `rules.py` — severity helper functions

#### `service.py` pattern

```python
class BrowserConfigurationService(BaseModuleService):
    module_name = "browser_configuration"
    module_domain = "browser"
    required_entity_types = [EntityType.DEVICE]  # or EMAIL if running per-user

    async def run(self, user_id, asset_id, asset_value, ctx=None) -> list[SignalCreate]:
        signals = []
        # ctx should carry policy_paths: dict[str, str] with keys "chrome", "firefox"
        # call ChromiumEnterprisePoliciesProvider and FirefoxEnterprisePoliciesProvider
        # map each finding to a SignalCreate using the signal table above
        return signals
```

**Severity helpers in `rules.py`:**
- `safe_browsing_severity()` → always `Severity.HIGH`
- `update_disabled_severity()` → always `Severity.MEDIUM`
- All others → `Severity.LOW`

---

## Part C — Extension Risk Module

**New module:** `backend/app/modules/browser/extension_risk/`

### C.1 Provider clients

**CRXcavator** — already scaffolded (fix in Part A). After Part A fix, add a `check_extension(extension_id)` method for single-extension lookup.

#### `backend/app/providers/cloud/chrome_web_store_api/client.py`

Enrichment-only. Uses the `chrome-extension-info` Python package or scraping of the Chrome Web Store.

```python
class ChromeWebStoreApiProvider(BaseProviderClient):
    name = "chrome_web_store_api"

    async def get_extension(self, extension_id: str) -> dict[str, Any] | None:
        """
        Fetch Chrome Web Store metadata for an extension.
        Returns enrichment dict or None on miss.
        Key fields: id, name, version, developer, permissions, user_count,
                    rating, last_updated, manifest_version
        """
```

#### `backend/app/providers/cloud/firefox_addons_site_api/client.py`

Official Mozilla AMO API. Returns AMO add-on metadata.

```python
class FirefoxAddonsSiteApiProvider(BaseProviderClient):
    name = "firefox_addons_site_api"
    base_url = "https://addons.mozilla.org/api/v5"

    async def get_addon(self, guid: str) -> dict[str, Any] | None:
        """
        GET /api/v5/addons/addon/{guid}/
        Returns enrichment dict or None on 404.
        Key enrichment fields: guid, name, status, promoted,
                               average_daily_users, ratings.average, last_updated,
                               is_experimental, has_privacy_policy
        """

    async def get_version_detail(self, addon_id: int, version_id: int) -> dict[str, Any] | None:
        """
        GET /api/v5/addons/addon/{addon_id}/versions/{version_id}/
        Key fields: file.permissions, file.optional_permissions, file.host_permissions
        """
```

No auth required for public listed add-ons.

### C.2 Signal contract

CRXcavator emits ONE conditional signal:

| signal_type | severity | conditional_rule |
|---|---|---|
| `browser_extension_risk` | low | `data.risk.total <= 377` |
| `browser_extension_risk` | medium | `378 <= data.risk.total <= 478` |
| `browser_extension_risk` | high | `data.risk.total > 478` |

Chrome Web Store and AMO are **enrichment-only** — they add metadata to the signal's `evidence` dict but do not generate standalone signals.

### C.3 Module structure

`backend/app/modules/browser/extension_risk/`:
- `__init__.py`
- `service.py` — `ExtensionRiskService(BaseModuleService)`
- `rules.py` — `crxcavator_severity(total_risk: int) -> Severity`

```python
class ExtensionRiskService(BaseModuleService):
    module_name = "extension_risk"
    module_domain = "browser"
    required_entity_types = [EntityType.URL]  # extension_id passed as URL-like asset

    async def run(self, user_id, asset_id, asset_value, ctx=None) -> list[SignalCreate]:
        signals = []
        # asset_value = Chrome extension ID (e.g. "cfhdojbkjhnklbpkdaibdccddilifddb")
        # 1. Call CrxcavatorProvider.check_extension(extension_id)
        # 2. If hit, compute severity from data.risk.total
        # 3. Optionally enrich with ChromeWebStoreApiProvider.get_extension()
        # 4. Emit browser_extension_risk signal with full evidence
        return signals
```

---

## Part D — Software Inventory Module

**New module:** `backend/app/modules/device/software_inventory/`

### D.1 Provider client

#### `backend/app/providers/tools/syft/client.py`

Local tool runner. Syft is installed separately; this provider shells out to it.

```python
class SyftProvider(BaseProviderClient):
    name = "syft"

    async def scan(self, target: str, output_format: str = "json") -> dict[str, Any]:
        """
        Run `syft {target} -o json` as a subprocess.
        target: e.g. "/", "dir:/path", "docker:image:tag"
        Returns parsed Syft JSON output or raises ProviderError.
        """
```

Key Syft JSON fields to extract per package:
- `name`, `version`, `type`, `purl`, `language`
- `locations[*].path`
- `source.type`, `distro`

### D.2 Signals

Syft emits INFO-level coverage signals only (from research):

| signal_type | severity | trigger_condition |
|---|---|---|
| `software_inventory_scan_completed` | info | scan ran, ≥1 package found |
| `software_inventory_scan_empty` | info | scan ran, 0 packages found |

These are **coverage signals**, not risk signals. They confirm that an inventory was collected.

### D.3 Module structure

Create `backend/app/modules/device/` domain with `__init__.py`.

`backend/app/modules/device/software_inventory/`:
- `__init__.py`
- `service.py` — `SoftwareInventoryService(BaseModuleService)`

```python
class SoftwareInventoryService(BaseModuleService):
    module_name = "software_inventory"
    module_domain = "device"
    required_entity_types = [EntityType.DEVICE]

    async def run(self, user_id, asset_id, asset_value, ctx=None) -> list[SignalCreate]:
        # asset_value = scan target (e.g. "/")
        # Run syft, store packages in evidence, emit coverage signal
```

Store the full package list in `evidence.packages` as a list of dicts. This drives the software inventory UI view.

---

## Part E — Identity Module Enhancements

### E.1 Enhance `username_exposure` with emailcrawlr + gravatar

Update `backend/app/modules/identity/username_exposure/service.py`:

**EmailcrawlrProvider additions:**
- Call `search_emails(email=asset_value)` — emits `email_public_exposure` signal
  - `severity = MEDIUM` baseline
  - Escalate to `HIGH` if response contains phone number, physical address, or full name fields
- Call `search_emails(domain=domain_from_email)` — also emits `email_public_exposure`
  - Same severity rules

**GravatarProvider additions (enrichment only):**
- Create `backend/app/providers/social/gravatar/client.py`
- Call `lookup(email=asset_value)` → `GET https://api.gravatar.com/v3/profiles/{sha256_hash}`
- On 200: attach enrichment dict to existing signals (do NOT emit standalone signal)
- On 404: skip silently

New settings keys required:
- `emailcrawlr_api_key: SecretStr | None`
- `gravatar_api_key: SecretStr | None` (optional — falls back to unauthenticated)

### E.2 Enhance `alias_correlation` with emailformat

Update `backend/app/modules/identity/alias_correlation/service.py`.

Create `backend/app/providers/social/emailformat/client.py`:

```python
class EmailformatProvider(BaseProviderClient):
    name = "emailformat"
    base_url = "https://api.hunter.io/v2"  # NOTE: verify this — research showed emailformat.com

    async def get_formats(self, domain: str) -> list[dict[str, Any]]:
        """
        GET /api/v2/get_formats?domain={domain}
        Auth: Authorization: api_private_key header
        Returns list of email format patterns for the domain.
        Enrichment only — no signals.
        """
```

`alias_correlation` uses the format data to expand discovered aliases by predicting likely email patterns for a given domain. No new signal types; enriches existing alias correlation findings.

New settings key: `emailformat_api_key: SecretStr | None`

---

## Part F — Deferred

**Truecaller** (`phone_exposure` module): No commercial spam/lookup API exists. The legacy REST API was deprecated in 2017. Treat as `local_tool_or_deferred` until Truecaller exposes a data API. The `phone_exposure` module stub remains but no Truecaller provider should be wired in.

**skymem** (`username_exposure` enrichment): HTML scraping of `skymem.info`. Lower priority than other work. Defer to post-launch as it has no official API and would require maintaining a fragile scraper.

---

## Implementation Order

1. **A.1 + A.2** — Fix `emailcrawlr` and `crxcavator` async patterns (blocking for E.1 + C.3)
2. **E.1** — Enhance `username_exposure` with emailcrawlr signals (emailcrawlr fix must be first)
3. **D.1 + D.3** — Syft provider + software_inventory module
4. **B.1 + B.2** — Browser config providers + module
5. **C.1 + C.3** — Extension risk providers + module
6. **E.2** — Alias correlation emailformat enrichment
7. **D.4 (skymem)** — Defer post-launch

---

## New Settings Keys to Add

Add to `backend/app/core/config.py` Settings class:

```python
emailcrawlr_api_key: SecretStr | None = None
gravatar_api_key: SecretStr | None = None
emailformat_api_key: SecretStr | None = None
# crxcavator: no key needed (public API)
# chrome_web_store_api: no key needed
# firefox_addons_site_api: no key needed
```

---

## New Files Created

```
backend/app/modules/browser/__init__.py
backend/app/modules/browser/browser_configuration/__init__.py
backend/app/modules/browser/browser_configuration/service.py
backend/app/modules/browser/browser_configuration/rules.py
backend/app/modules/browser/extension_risk/__init__.py
backend/app/modules/browser/extension_risk/service.py
backend/app/modules/browser/extension_risk/rules.py
backend/app/modules/device/__init__.py
backend/app/modules/device/software_inventory/__init__.py
backend/app/modules/device/software_inventory/service.py

backend/app/providers/tools/chromium_enterprise_policies/client.py
backend/app/providers/tools/firefox_enterprise_policies/client.py
backend/app/providers/tools/syft/client.py
backend/app/providers/social/gravatar/client.py
backend/app/providers/social/emailformat/client.py
backend/app/providers/cloud/chrome_web_store_api/client.py
backend/app/providers/cloud/firefox_addons_site_api/client.py
```

Modified:
```
backend/app/providers/social/emailcrawlr/client.py  (async fix)
backend/app/providers/threat_intel/crxcavator/client.py  (async fix + add check_extension)
backend/app/modules/identity/username_exposure/service.py  (add emailcrawlr + gravatar)
backend/app/modules/identity/alias_correlation/service.py  (add emailformat enrichment)
backend/app/core/config.py  (new secret keys)
```

---

## Module Registration

New modules must be added to `DOMAIN_MODULES` in `backend/app/jobs/runner.py`:

```python
DOMAIN_MODULES: dict[str, list[type[BaseModuleService]]] = {
    "identity": [...existing...],
    "browser": [
        BrowserConfigurationService,
        ExtensionRiskService,
    ],
    "device": [
        SoftwareInventoryService,
    ],
}
```

`browser` and `device` are already listed in `backend/app/tiers/config/core.yaml` `enabled_domains`, so no tier config changes are needed.

---

## Dependency Chain Notes

- `browser_configuration` module: entity_type = DEVICE. Run during device scan, not email scan.
- `extension_risk` module: entity_type = URL (for extension IDs). Needs new EntityType or use existing URL type for extension IDs.
- `software_inventory` module: entity_type = DEVICE.
- `username_exposure` enhancement: entity_type = EMAIL (unchanged).
- `alias_correlation` enhancement: entity_type = EMAIL (unchanged).

Check `backend/app/core/enums.py` for available EntityType values before implementing. If DEVICE or EXTENSION are missing, add them.

---

## Testing Requirements

Per module, write tests covering:
- Provider success path (mock HTTP response or subprocess)
- Provider 404/empty/no-hit (no signal emitted, no exception)
- Provider auth failure (`ProviderAuthError` caught, logged, degraded gracefully)
- Provider rate limit (`ProviderRateLimitError` caught, logged, degraded gracefully)
- Correct signal shape validation (signal_type, category, severity, entity_type)
- Conditional severity logic (for crxcavator: test all three threshold bands)
