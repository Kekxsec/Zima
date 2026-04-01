---
title: "output / tools / get_browser_extension_info"
aliases: ["get_browser_extension_info output", "get_browser_extension_info signal registry"]
tags: [zima, research, outputs, signal-registry, tools, get_browser_extension_info, graph_exclude]
type: provider_research_output
provider: get_browser_extension_info
provider_category: tools
status: not_started
prompt_note: prompt.md
provider_folder: get_browser_extension_info.md
obsidianUIMode: preview
---


# A. Tool/API Surface Appendix

**Chrome extension permissions (Manifest V2 & V3):** Chrome extensions declare required privileges in the manifest. In Manifest V2, extensions use two lists: `"permissions"` (API and broad host permissions) and `"optional_permissions"`. Manifest V3 adds separate host-match keys: `"host_permissions"` and `"optional_host_permissions"`. Example JSON (MV3) shows all four keys:

json

Copy

```json
{
  "permissions": ["activeTab", "contextMenus", "storage"],
  "optional_permissions": ["topSites"],
  "host_permissions": ["https://www.example.com/*"],
  "optional_host_permissions": ["https://*/*", "http://*/*"],
  "manifest_version": 3
}
```

.

Chrome supports a large set of permission strings; notable ones include:

- `<all_urls>` or broad match patterns (under host_permissions) – allows access to **all websites** (effectively “full page” access).
- `tabs` – access to tab metadata (URL, title, favicon) and privileged Tab APIs.
- `webRequest` / `webRequestBlocking` – intercept or modify network requests.
- `cookies` – read/write browser cookies.
- `clipboardRead` / `clipboardWrite` – read/write the system clipboard.
- `nativeMessaging` – communicate with native applications.
- `debugger` – full DevTools protocol (inspect/modify pages).
- `management` – view/manage other extensions/apps.
- `proxy` – control browser proxy settings.
- `downloads` (and related) – initiate/manage downloads.
- `history` – read/change browsing history.
- `bookmarks` – read/modify bookmarks.
- `identity` – access user identity (email).
- `storage`, `unlimitedStorage` – local/synced storage (generally benign).

Security-sensitive permissions include any broad host patterns (`<all_urls>`), plus the above that allow reading or modifying sensitive data (tabs, cookies, downloads, etc.). Users see warnings for many of these on install.

**Firefox WebExtension permissions:** Firefox follows the WebExtensions spec similar to Chrome. It uses the `"permissions"` and `"optional_permissions"` keys (an array of strings) for API and (in MV2) host permissions. In Manifest V3, Firefox also supports separate `"host_permissions"`/`"optional_host_permissions"` like Chrome. Key differences:

- Firefox requires setting a fixed extension ID via `browser_specific_settings.gecko.id` when publishing MV3, whereas Chrome ignores this field.
- Firefox adds some manifest keys not in Chrome (e.g. `protocol_handlers`, `theme_experiment`) and omits some Chrome-only keys.
- Common permissions work similarly; e.g. declaring `"tabs"` in Firefox grants access to privileged parts of the tabs API (URL/title), and `<all_urls>` is represented via match patterns (e.g. `"*://*/*"`) granting full web access.

**Normalized extension metadata schema:** The provider outputs a structured object with fields such as:

- `extension_id` (string) – unique ID of the extension (from manifest or store).
- `name` (string) – extension name (mandatory in manifest).
- `version` (string) – version number (mandatory).
- `description` (string) – optional human-readable description.
- `author` (string) – optional author/developer (manifest key `author` or `developer.name`).
- `browser` (string) – which browser (chrome/firefox/edge/etc).
- `manifest_version` (int) – manifest version (2 or 3).
- `permissions` (list[string]) – the `"permissions"` array from manifest.
- `optional_permissions` (list[string]) – the `"optional_permissions"` array.
- `host_permissions` (list[string]) – the `"host_permissions"` array (MV3 only).
- `content_scripts` (list[object]) – each content script’s `matches`, `js`, `css`, `run_at` etc from `content_scripts` section.
- `background` (object) – background scripts or service worker info (e.g. `{"scripts": [...], "persistent": false}` or `{"service_worker": "..."}`).
- `update_url` (string) – URL for auto-updating the extension (optional).
- `homepage_url` (string) – developer’s homepage or support page.
- `store_url` (string) – derived link to the browser’s extension store (see below).
- `enabled` (bool) – whether the extension is currently enabled (in inventory data).
- `install_path` (string) – local filesystem path or identifier (if available).

Fields marked mandatory (`name`, `version`, `manifest_version`) always appear (per spec); others are optional or browser-specific. For example, MV3-only fields like `host_permissions`/`optional_host_permissions` may be empty in MV2; the `browser_specific_settings.gecko.id` used for Firefox is not output here. The raw manifest or relevant fields should be retained as evidence.

**Extension Store URLs:** The store listing URLs can be derived from the extension ID:

- **Chrome Web Store:** `https://chrome.google.com/webstore/detail/{extension_id}`.
- **Firefox Add-ons (AMO):** `https://addons.mozilla.org/firefox/addon/{slug_or_id}/` (usually the add-on’s slug).
- **Edge Add-ons:** `https://microsoftedge.microsoft.com/addons/detail/{extension_id}`.

These can be constructed if the extension is published; if not, treat as unknown.

# B. Module Mapping Table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|extension_risk|enrichment_only|`extract_extension_metadata`|`manifest.json`|enrichment_only|device|Requires a discovered browser extension with available manifest. Only runs when raw extension data (ID & manifest) is present.|[47†L311-L319]|Outputs normalized extension data (permissions, scripts, etc.) for risk assessment; does not itself produce risk signals.|

**Notes:** The `extract_extension_metadata` method ingests raw manifest data (from an upstream detector) and emits a structured metadata object (as per schema above). It does not decide risk; the `extension_risk` module will use its output. The gating logic is simply that an extension was detected (e.g. by `browser_extension_detector`/osquery) and a manifest is available. All manifest fields are forwarded; none are dropped as standalone signals by this provider.

# C. Signal Contract Table

No standalone signals are emitted by **get_browser_extension_info**. It is purely an enrichment component: it parses extension manifests and outputs data, but it **does not directly identify malice or breaches**. All security conclusions (e.g. flagging a suspicious permission) are deferred to the `extension_risk` module. Therefore the signal table is empty.

# D. Confidence Guidance

|module|signal_type_or_use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|extension_risk|extension metadata enrichment|**High.** The manifest is factual browser data.|**Static.** Extension metadata does not change unless updated. Up-to-date inventory is needed (re-run on updates).|N/A (metadata only)|Ensure manifest parser stays synced with browser schema changes (MV3 adoption, new fields).|

**Notes:** The `extract_extension_metadata` output has high reliability (it simply reflects the extension’s manifest file and system info). Freshness depends on how often extension inventories are scanned; stale manifests only matter if the extension was updated. There is no direct “finding” to corroborate – metadata can be cross-checked against actual extension files if needed. Calibration tasks: validate that manifest parsing handles all relevant keys (e.g. new permissions in future MV3 changes).

# E. Provider Summary

1. **Strongest contributions:** Provides comprehensive extension metadata (permissions list, content scripts, background scripts, update/homepage URLs, author, etc.). In particular, the permissions and host patterns are key inputs for assessing extension risk (e.g. broad `<all_urls>` or powerful APIs).
2. **Not to be used for:** No direct risk scores or alerts; it should not be used to flag malicious extensions by itself. It doesn’t infer any malicious behavior (that’s the downstream module’s job). It also cannot discover extensions – it relies on upstream discovery.
3. **Implementation cautions:** This is a local parser (no API keys or rate limits). Ensure that all possible manifest fields survive parsing (handle missing optional fields gracefully). Deduplicate on extension ID and version. Store the raw manifest or key fields (permissions, content script sources) for audit. No authentication or billing concerns.
4. **Treatment:** This provider is **enrichment-only**. It does not emit signals itself, only structured data for `extension_risk` to process.

**References:** Official Chrome and Mozilla extension docs confirm the manifest keys and permissions described above.

# F. Structured JSON

{
  "provider": "get_browser_extension_info",
  "provider_category": "tools",
  "provider_role": "enrichment_only",
  "module_mappings": [
    {
      "module": "extension_risk",
      "provider_role": "enrichment_only",
      "provider_method": "extract_extension_metadata",
      "endpoint_or_artifact": "manifest.json",
      "classification": "enrichment_only",
      "entity_types": ["device"],
      "gating_logic": "Requires extension ID and manifest content from browser_extension_detector output",
      "citation_refs": [],
      "notes": "Provides normalized extension metadata (permissions, content_scripts, etc.) for risk assessment; does not directly produce signals."
    }
  ],
  "signal_contracts": [],
  "confidence_guidance": []
}
