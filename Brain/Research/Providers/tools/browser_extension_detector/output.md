---
title: "output / tools / browser_extension_detector"
aliases: ["browser_extension_detector output", "browser_extension_detector signal registry"]
tags: [zima, research, outputs, signal-registry, tools, browser_extension_detector, graph_exclude]
type: provider_research_output
provider: browser_extension_detector
provider_category: tools
status: not_started
prompt_note: prompt.md
provider_folder: browser_extension_detector.md
obsidianUIMode: preview
kind: artifact
llm_include: false
code_scope: backend
---


## A. Tool/API Surface Appendix

- **Chrome/Chromium (Windows, macOS, Linux):** Each Chrome profile has an “Extensions” subfolder under the user data directory. Default paths:

    - **Windows:** `%LOCALAPPDATA%\Google\Chrome\User Data\<Profile>\Extensions` (e.g. `Default\Extensions`).
    - **macOS:** `~/Library/Application Support/Google/Chrome/<Profile>/Extensions`.
    - **Linux:** `~/.config/google-chrome/<profile>/Extensions` (or `~/.config/chromium/<profile>/Extensions`).
        Each extension’s files reside in a subfolder named by its extension ID, with version subfolders inside (each containing a `manifest.json`). The same structure applies to Chromium (paths under `Chromium/User Data`) and Chrome variants (Beta, Dev, etc., with different “User Data” suffixes).
    - **Manifest format:** Chrome extensions use `manifest.json` in WebExtension format (Manifest v3). Key fields: `manifest_version` (must be 3), `name`, `version` (mandatory keys), and common entries like `description`, `icons`, `permissions`, `content_scripts`, `background.service_worker` (MV3) or `background.scripts` (legacy MV2), `update_url`, `homepage_url`, etc.. Chrome ignores the `author` field (only Firefox uses it).
    - **Enabled/disabled state (Chrome/Edge/Brave):** The file `Secure Preferences` in the profile directory (e.g. `%LOCALAPPDATA%\Google\Chrome\User Data\<Profile>\Secure Preferences`) is JSON and contains an `"extensions":{"settings":{<extensionID>:{...}}}` section. Each extension entry has `"state":1` if enabled (0 if disabled). This file is read-only trusted; do not modify it.
- **Firefox (Windows, macOS, Linux):** Firefox stores each profile under:

    - **Windows:** `%APPDATA%\Mozilla\Firefox\Profiles\<profile>\` (find profiles via `profiles.ini`).
    - **macOS:** `~/Library/Application Support/Firefox/Profiles/<profile>/`.
    - **Linux:** `~/.mozilla/firefox/<profile>/`.
        Inside each profile:
    - **Extension files:** Modern WebExtensions live under `<profile>/extensions/` (often as `.xpi` files or subfolders named by ID), or under `~/.mozilla/firefox/<id>.default-release/extensions/`. Legacy (pre-FX57) extensions also had install manifests (`install.rdf`), but ignore those.
    - **extensions.json:** This file in the profile root lists every add-on. Each entry includes `id`, `version`, `defaultLocale.name` (the human name), and flags such as `"active": true/false` and `"userDisabled": true/false` to indicate enablement. (E.g. `"active":false,"userDisabled":true` means an add-on is disabled). The `extensions.json` also contains the `descriptor` or `path` to the extension’s location and install/update dates.
    - **Manifest format:** Firefox uses WebExtension `manifest.json` (supports both Manifest v2 and v3). Fields mirror Chrome’s (plus `author` and optional `browser_specific_settings`). Mandatory keys: `manifest_version`, `name`, `version`.
- **Microsoft Edge (Chromium-based, Windows/macOS/Linux):** Edge uses a Chromium engine and essentially the same directories as Chrome, but under “Microsoft/Edge”:

    - **Windows:** `%LOCALAPPDATA%\Microsoft\Edge\User Data\<Profile>\Extensions`.
    - **macOS:** `~/Library/Application Support/Microsoft Edge/<Profile>/Extensions`.
    - **Linux:** `~/.config/microsoft-edge/<profile>/Extensions`.
        The manifest structure and state file (`Secure Preferences`) are analogous to Chrome’s. The Edge “Secure Preferences” file (`...Edge/User Data/<Profile>/Secure Preferences`) also contains extension `state` flags (1=enabled) just like Chrome’s.
- **Brave Browser (Windows/macOS/Linux):** Brave is Chromium-based with paths:

    - **Windows:** `%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\<Profile>\Extensions`.
    - **macOS:** `~/Library/Application Support/BraveSoftware/Brave-Browser/User Data/<Profile>/Extensions`.
    - **Linux:** `~/.config/BraveSoftware/Brave-Browser/Default/Extensions`.
        The Brave preferences file (`...Brave-Browser\User Data\<Profile>\Secure Preferences`) similarly holds enabled/disabled flags.
- **Safari (macOS only):** Safari used to use `.safariextz` files and a user Extensions folder; now it uses App Extensions from the App Store:

    - **Legacy (pre-2018):** Extensions were `.safariextz` in `~/Library/Safari/Extensions/` or `/Library/Safari/Extensions/`.
    - **Modern (Safari 13+):** Safari “Web Extensions” (Safari App Extensions) are bundled with macOS apps. Installed Safari extensions are listed in `~/Library/Containers/com.apple.Safari/Data/Library/Safari/WebExtensions/Extensions.plist`. Each entry shows its state and metadata. However, these extensions are not easily enumerated via a public API or flat files; the Safari container directories (under `~/Library/Containers/`) may require special permissions (e.g. Full Disk Access on newer macOS). In practice, enumeration of Safari App Extensions is out of scope for a simple filesystem scan.
- **Multiple Profiles:** All browsers can have multiple profiles (Default, Profile 1, Profile 2, etc.). The tool should enumerate _all_ subfolders under the user data/profiles parent directory to cover each profile’s extensions. Chromium-based browsers list profiles in a top-level “User Data” folder; Firefox uses `profiles.ini` or the “Profiles” directory.

- **Detection methods:** This component will **scan the local filesystem**: for each installed browser, locate user profile directories (as above), then list extension folders and read each `manifest.json`. It will also parse the browser’s preferences (Chrome/Edge/Brave) or `extensions.json` (Firefox) to mark enabled state. No external APIs or network calls are used; access requires read permission to the user’s browser data directories.

- **Output schema (inventory):** The provider should output a list of installed extensions, e.g.:

    swift

    Copy

    ```
    [
      {
        "browser": "chrome",
        "profile": "Default",
        "extension_id": "abcdefghijklmnop",
        "name": "Example Extension",
        "version": "1.2.3",
        "path": "C:\\Users\\UserName\\...\\Default\\Extensions\\abcdefghijklmnop\\1.2.3",
        "manifest": { ...contents of manifest.json... },
        "enabled": true
      },
      ...
    ]
    ```

    Fields: `browser` (chrome/edge/firefox/brave), `profile` (profile directory name), `extension_id` (the folder name), `name`, `version`, `path` (filesystem path to version folder), `manifest` (parsed JSON), and `enabled` (boolean). All fields come from the filesystem or JSON files (none are guessed).


## B. Module Mapping Table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|`extension_risk`|utility_only|`extension_inventory`|Local browser profile directories & manifests|utility_only|device|Browser profile directory exists (browser installed and accessible)||Enumerates installed extensions; does not itself assess risk.|

**Notes:** The `extension_risk` module will consume the raw extension inventory (utility output). It uses filesystem scanning (no network endpoints). Classification is _utility_only_ (no standalone signals). The entity type is the host/device. The only gating is presence of browser data directories (i.e. the user has the browser and its profile exists). References show default profile paths for Chrome/Edge and how state is stored.

## C. Signal Contract Table

No standalone signals are emitted by **browser_extension_detector**, since it only provides utility data (the list of installed extensions). All findings (risk signals) are to be generated downstream in the `extension_risk` module. Therefore, no signal contract rows are defined for this provider.

## D. Confidence Guidance

|module|use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|`extension_risk`|extension_inventory|**High** – direct filesystem read. Data (ID, version, manifest) is factual and authoritative.|Inventory is current at scan time. Staleness if extensions change between scans.|N/A – extension list is definitive from this host.|None needed – factual collection, not scored data.|

**Details:** Reading the browser’s files (manifests, prefs) is highly reliable (no network/API uncertainty). Data is only as fresh as the last scan; newly installed/uninstalled extensions after the scan won’t appear. There’s no need to correlate with external sources for accuracy (the filesystem is the source of truth for that host). No statistical calibration is needed since this isn’t a probabilistic signal.

## E. Provider Summary

- **Contribution:** Provides a complete inventory of installed browser extensions (ID, version, manifest data, enabled state) for Chrome, Edge, Brave, and Firefox on the host. This serves as enrichment for the `extension_risk` module to evaluate extension risk.
- **Not for:** It does _not_ assess or rate risk itself. It should **not** generate alerts or signals about malicious extensions — it merely reports what is installed. Also, it cannot fully enumerate Safari App Extensions on recent macOS.
- **Cautions:** Must run with permission to read user profiles (on Windows/Mac/Linux this is normally allowed for the logged-in user). On macOS, reading `~/Library/Containers/com.apple.Safari/...` may require Full Disk Access. If a browser is running, its preferences file may be locked for writing – the tool should handle read errors gracefully (e.g. skip or retry on profile busy).
- **Corollary:** Osquery’s built-in tables (`chrome_extensions`, `firefox_addons`, `safari_extensions`) cover similar data; use this component only if osquery is unavailable or as a complementary fallback.
- **Role:** This is strictly a _utility-only_ provider (no direct signal generation). It enriches the data for the `extension_risk` module, which will handle risk scoring and signal emission.

{
  "provider": "browser_extension_detector",
  "provider_category": "tools",
  "provider_role": "utility_only",
  "module_mappings": [
    {
      "module": "extension_risk",
      "provider_method": "extension_inventory",
      "endpoint_or_artifact": "Local browser profile directories & manifests",
      "classification": "utility_only",
      "entity_types": ["device"],
      "gating_logic": "Browser profile directory exists (browser installed)",
      "notes": "Enumerates extensions; does not assess risk【40†L76-L84】【31†L170-L174】"
    }
  ],
  "signal_contracts": [],
  "confidence_guidance": [
    {
      "module": "extension_risk",
      "signal_type_or_use_case": "extension_inventory",
      "source_reliability": "High (direct file read)",
      "freshness_considerations": "Data is as fresh as last scan; new changes not seen until next run",
      "corroboration_rules": "N/A – inventory is authoritative from host",
      "calibration_todo": "None – factual collection"
    }
  ]
}
