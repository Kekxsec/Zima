---
title: "output / tools / firefox_enterprise_policies"
aliases: ["firefox_enterprise_policies output", "firefox_enterprise_policies signal registry"]
tags: [zima, research, outputs, signal-registry, tools, firefox_enterprise_policies, graph_exclude]
type: provider_research_output
provider: firefox_enterprise_policies
provider_category: tools
status: complete
prompt_note: prompt.md
provider_folder: firefox_enterprise_policies.md
obsidianUIMode: preview
---

# firefox_enterprise_policies Provider Integration Research for Zima

## API Surface Appendix

Windows Registry – Firefox policies are stored under the Windows Group Policy registry keys. Machine-wide policies live in HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Mozilla\Firefox and user policies in HKEY_CURRENT_USER\SOFTWARE\Policies\Mozilla\Firefox
. Each supported policy is a subkey or value under this path. Values are typically REG_DWORD (0x1 or 0x0 for boolean flags) or REG_SZ for string settings (e.g. URLs). For example, AppAutoUpdate = 0x1|0x0 disables/enables auto-update
, and Cookies\Behavior = "accept" | "reject-foreign" | ... sets the cookie behavior
. Policy keys may have accompanying "Locked" flags (REG_DWORD 0/1) indicating whether the setting is enforced. Missing keys imply no override. Reading requires Registry query privileges; permission errors or 32/64‑bit registry redirection issues are possible. Notable keys:

Update Policies – AppAutoUpdate, DisableAppUpdate, AppUpdatePin, AppUpdateURL under ...Firefox\. AppAutoUpdate=0 or DisableAppUpdate=1 means auto-updates off
. AppUpdatePin is a string specifying a version prefix
. AppUpdateURL is an alternate update server
.
Tracking/Privacy – DNSOverHTTPS\Enabled (0/1) controls DNS-over-HTTPS
. EnableTrackingProtection\Value (0/1) turns off/on tracking protection
. Subkeys Cryptomining=0|1, Fingerprinting=0|1, EmailTracking=0|1 disable the respective protections
.
Cookies – Cookies\Behavior and Cookies\BehaviorPrivateBrowsing set cookie handling (e.g. "accept", "reject-foreign", etc)
. Cookies\Allow, AllowSession, Block are lists of origins (REG_MULTI_SZ) with special rules.
Extensions – Extensions\Install, Uninstall, Locked (REG_MULTI_SZ or REG_DWORD) control add-on installation/uninstallation and locking. Also newer "ExtensionSettings" JSON (REG_MULTI_SZ) defines per-extension policies; its complexity suggests enrichment-only use. ExtensionUpdate = 0x1|0x0 disables all extension updates
.
Other Policies – DisablePrivateBrowsing=0x1|0x0 removes private mode
. PasswordManagerEnabled=0x1|0x0 (false) disables the built-in password manager
. Telemetry (DisableTelemetry) and studies (DisableFirefoxStudies) appear as policies but turning them off is generally privacy-friendly (enrichment-only).
macOS Preferences (plist) – Policies are read from a plist at /Library/Preferences/org.mozilla.firefox.plist (system-wide) or user ~/Library/Preferences/org.mozilla.firefox.plist. Enterprise policies only apply if the key EnterprisePoliciesEnabled (boolean) is set true in that domain
. Policies appear as keys in the plist, possibly nested. For example, <key>DisableAppUpdate</key><true/> disables updates
. The plist format reflects the JSON structure: e.g. EnableTrackingProtection appears as a dictionary with subkeys Value, Cryptomining, etc.
. An example plist template is provided in Mozilla's repo
. Parsing requires reading the plist (possibly via defaults or a plist library). On macOS, /Library/Managed Preferences may also hold policy plists if deployed via MDM. Policy value types mirror registry types (booleans, strings, arrays).

Linux policies.json – Firefox honors a policies.json file. System-wide, this is either placed in the Firefox installation's distribution/ directory (e.g. /usr/lib/firefox/distribution/policies.json) or in /etc/firefox/policies/policies.json
. The JSON must have a top-level "policies": {...} object. Policy names and structure match the GPO names. For example:

```json
{
  "policies": {
    "AppAutoUpdate": false,
    "AppUpdatePin": "106.",
    "DisableAppUpdate": true,
    "DNSOverHTTPS": { "Enabled": false },
    "EnableTrackingProtection": { "Value": false, "Cryptomining": false, "Fingerprinting": false },
    "Cookies": { "Behavior": "accept" },
    "DisablePrivateBrowsing": true,
    "PasswordManagerEnabled": false,
    "ExtensionUpdate": false
  }
}
```

An official snippet shows this structure
. Policies absent from JSON default to no override. Parsing requires JSON parsing; errors in the file (malformed JSON) produce no effect. The file must be UTF-8.

Browser-internal (about:policies) – Firefox's internal page about:policies lists active policies and their source (Registry, plist, or JSON). This is useful for validation/debugging but is not directly consumed by the provider. It confirms effective values but is read-only in UI and not a reliable data source for Zima.

Policy Precedence & Scope – On Windows, HKLM (computer policy) applies to all users, HKCU (user policy) to the current user; if both exist, HKLM typically enforces system defaults. On Mac, only policies enabled by EnterprisePoliciesEnabled=true take effect. On Linux, only policies.json is considered (no separate user-level, unless a user has a private installation with its own distribution folder). Firefox ESR versus release differences: not all policies exist in older ESR (e.g. some tracking fields were added in v70+
). The provider should handle missing fields gracefully.

Parseability & Stability – The registry and plist keys are stable; policy names seldom change and new ones are added at version bumps. JSON keys mirror registry names exactly. Values are basic types (booleans, integers, strings, arrays). Read errors (e.g. permission denied, parse errors) should be captured. When keys are absent, provider output should reflect "policy not set" (no false trigger).

Supported OS & Requirements: Windows (any edition that supports Group Policy), macOS (10.9+ where Firefox policies work), Linux (various distros). Tools need admin privileges to read system-level keys/files (reg query or sudo).

Direct vs Enrichment: Keys like update controls, tracking, cookies, private browsing, password manager – they yield direct signals (misconfiguration or risk). Lists (extension allow/block, cookie allow/block, etc.) are enrichment only (context). Telemetry/studies flags are utility/context.

Variants & Errors:

If no policies are present (Registry key missing, no plist or JSON), no signals fire – the platform will operate with defaults.
Partial policies: e.g. a TrackingProtection value but no sub-keys for Crypto etc., treat missing sub-field as "not set".
If policy file exists but Firefox version does not support a given key, the policy is ignored (no signal).
Handle malformed policy artifacts by reporting no parse result for that piece.

## Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|--------|---------------|-----------------|----------------------|-----------------|--------------|--------------|---------------|-------|
| browser_configuration | local_tool_or_deferred | read_registry (Windows) | Windows Registry Policies (HKLM/HKCU\...Firefox\) | direct_signal_input + enrichment_only (mixed) | browser (config) | Check policy keys under registry path; if keys exist | | Windows GPO registry entries for Firefox policies (see Tool API Appendix). Many policies yield signals or context. |
| browser_configuration | local_tool_or_deferred | read_plist (macOS) | macOS Preferences /Library/Preferences/org.mozilla.firefox.plist | direct_signal_input + enrichment_only (mixed) | browser | If EnterprisePoliciesEnabled=true, read policy keys | | Mac plist domain with flattened policy keys (via defaults). Similar keys as Windows (boolean or strings). |
| browser_configuration | local_tool_or_deferred | read_file (Linux) | Linux policies.json (e.g. /etc/firefox/policies/policies.json or /usr/lib/firefox/distribution/) | direct_signal_input + enrichment_only (mixed) | browser | If JSON exists, parse policies -> keys/values | | System or installation-level JSON. Same policy names/structure. |
| browser_configuration | local_tool_or_deferred | internal (about:policies) | Firefox internal policies page | utility_only | browser | Only for validation; not used for signal triggers | | Shows effective policies; use for debugging only, not consumed by Zima. |
| browser_configuration | local_tool_or_deferred | – | Firefox installed (no policy source) | out_of_scope | | no policy store found → skip | – | If no policy mechanism detected (unmanaged device), provider emits nothing. |

Notes: The Windows registry and Linux JSON artifacts each contain both signal-producing and enrichment-only fields. Mapping logic in the module will separate triggers (e.g. update=disabled) from passive info (e.g. extension allow-lists). Gating logic may check "policy domain exists" (e.g. registry key present, or JSON file exists). The module's source in emitted signals will be browser_configuration.

## Signal Contracts, Severity, and Tags

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|--------|--------|----------|-----------------|-------------|----------|----------|-------------------------|-----------------|-------------|-------------|-------------------|-----------------|-------------------|-------------------|-----------------|-----------|-------|
| browser_configuration | browser_configuration | firefox_enterprise_policies | Windows Registry / JSON | browser_update_disabled | network_security | medium | no | None (Boolean policy) | other | true_finding | (DisableAppUpdate = 0x1) OR (AppAutoUpdate = 0x0) | DisableAppUpdate, AppAutoUpdate | – | Firefox auto-update has been disabled by enterprise policy. | documented | | Combines both policies that turn off updates. |
| browser_configuration | browser_configuration | firefox_enterprise_policies | Windows Registry / JSON | browser_update_pinned | network_security | low | no | None (string exists) | other | true_finding | AppUpdatePin exists (non-empty string) | AppUpdatePin | – | Firefox updates are pinned to version "{AppUpdatePin}" by policy. | documented | | Pinned version from policy. |
| browser_configuration | browser_configuration | firefox_enterprise_policies | Windows Registry / JSON | browser_update_url_changed | network_security | medium | no | None (string differs from default) | other | true_finding | AppUpdateURL exists (non-empty) | AppUpdateURL | – | Firefox will use custom update server {AppUpdateURL} (policy). | documented | | Assuming any custom URL is unusual (potential risk). |
| browser_configuration | browser_configuration | firefox_enterprise_policies | Windows Registry / JSON | dns_over_https_disabled | privacy | low | no | DNSOverHTTPS\Enabled = 0x0 | other | true_finding | DNSOverHTTPS.Enabled = 0x0 | DNSOverHTTPS.Enabled | – | DNS-over-HTTPS is disabled by policy, using unencrypted DNS. | documented | | Protected = false (no DOH). |
| browser_configuration | browser_configuration | firefox_enterprise_policies | Windows Registry / JSON | tracking_protection_disabled | privacy | low | no | EnableTrackingProtection\Value = 0x0 | other | true_finding | EnableTrackingProtection\Value = 0x0 | EnableTrackingProtection.Value | – | Firefox Tracking Protection is disabled by policy. | documented | | |
| browser_configuration | browser_configuration | firefox_enterprise_policies | Windows Registry / JSON | tracking_cryptomining_disabled | privacy | low | no | EnableTrackingProtection\Cryptomining = 0x0 | other | true_finding | EnableTrackingProtection\Cryptomining = 0x0 | EnableTrackingProtection.Cryptomining | – | Cryptomining protection in Tracking Protection is disabled by policy. | documented | | |
| browser_configuration | browser_configuration | firefox_enterprise_policies | Windows Registry / JSON | tracking_fingerprinting_disabled | privacy | low | no | EnableTrackingProtection\Fingerprinting = 0x0 | other | true_finding | EnableTrackingProtection\Fingerprinting = 0x0 | EnableTrackingProtection.Fingerprinting | – | Fingerprinting protection in Tracking Protection is disabled by policy. | documented | | |
| browser_configuration | browser_configuration | firefox_enterprise_policies | Windows Registry / JSON | tracking_email_disabled | privacy | low | no | EnableTrackingProtection\EmailTracking = 0x0 | other | true_finding | EnableTrackingProtection\EmailTracking = 0x0 | EnableTrackingProtection.EmailTracking | – | Email-tracking protection in Tracking Protection is disabled by policy. | documented | | |
| browser_configuration | browser_configuration | firefox_enterprise_policies | Windows Registry / JSON | cookies_third_party_allowed | privacy | low | no | Cookies\Behavior = "accept" | other | true_finding | Cookies\Behavior = "accept" | Cookies.Behavior, Cookies.BehaviorPrivateBrowsing | Cookies.Allow, Block, etc. | Cookies policy is set to "accept all" allowing all (including third-party) cookies. | documented | | Accept means no cookie blocking. |
| browser_configuration | browser_configuration | firefox_enterprise_policies | Windows Registry / JSON | private_browsing_disabled | privacy | low | no | DisablePrivateBrowsing = 0x1 | other | true_finding | DisablePrivateBrowsing = 0x1 | DisablePrivateBrowsing | – | Private Browsing mode has been disabled by policy. | documented | | |
| browser_configuration | browser_configuration | firefox_enterprise_policies | Windows Registry / JSON | password_manager_disabled | privacy/account_security | low | no | PasswordManagerEnabled = 0x0 | other | true_finding | PasswordManagerEnabled = 0x0 | PasswordManagerEnabled | – | The Firefox password manager is disabled by policy. | documented | | |
| browser_configuration | browser_configuration | firefox_enterprise_policies | Windows Registry / JSON | extension_updates_disabled | network_security | low | no | ExtensionUpdate = 0x0 | other | true_finding | ExtensionUpdate = 0x0 | ExtensionUpdate | – | Firefox extension auto-updates are disabled by policy. | documented | | |

Finding_kind: All above signals are "true_finding" (config issues), not mere context.
Entity_type: The affected entity is the browser/host configuration; we use "other" here since none of the given types match a browser.
Notes: Policies not listed (e.g. Telemetry, Studies, Pocket) produce no standalone signals (enrichment or UI only). The DisableAppUpdate vs AppAutoUpdate are combined into one signal for brevity, same with EnableTrackingProtection\Value.

## Confidence Guidance

| module | signal_type | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|--------|-------------|-------------------|-------------------------|-------------------|------------------|
| browser_configuration | browser_update_disabled | High – read from OS policy store (registry/JSON). | Policy files change only with admin action; treat as near-static until next policy push. | Confirm with Firefox UI (about:policies) or Firefox version's update status. | Verify correct interpretation of combined policies (AppAutoUpdate vs DisableAppUpdate). |
| browser_configuration | browser_update_pinned | High – string taken directly from policy storage. | Same as above. | Cross-check with Firefox "About" version string. | Map the pin value to actual version (maybe parse number). |
| browser_configuration | browser_update_url_changed | Medium – value from policy JSON/registry. | Custom URL may rarely change; static. | Compare to known Mozilla update URLs; check SSL certificate. | Identify default URL; if equal, no signal. |
| browser_configuration | dns_over_https_disabled | High – boolean policy flag. | Stays until policy change. | Can verify in Firefox DNS settings or about:networking#dns. | None significant; ensure reading correct data type. |
| browser_configuration | tracking_protection_disabled | High – boolean policy flag. | Static until policy update. | Firefox UI (Shield icon) or about:config (privacy.tracking). | None needed; ensure all sub-flags handled correctly. |
| browser_configuration | tracking_cryptomining_disabled | High – boolean policy flag. | Static. | Firefox UI ("Content Blocking") for cryptomining. | Possibly refine: only matter if main TP disabled or if pages known to mine. |
| browser_configuration | tracking_fingerprinting_disabled | High – boolean flag. | Static. | Firefox UI settings or tests for fingerprinting scripts. | None at present. |
| browser_configuration | tracking_email_disabled | High – boolean flag. | Static. | Check HTML content for email trackers, or Firefox UI. | Possibly combine with other TP flags in summaries. |
| browser_configuration | cookies_third_party_allowed | Medium – string value from policy. | Static. | Validate via about:preferences#privacy cookie settings. | Confirm default behavior if policy absent vs explicit 'accept'. |
| browser_configuration | private_browsing_disabled | High – policy flag. | Static. | Attempt entering Private mode in browser. | None. |
| browser_configuration | password_manager_disabled | High – policy flag. | Static. | Try saving a login or opening about:logins. | Clarify if relates to "Lock" state versus disable; trust direct flag. |
| browser_configuration | extension_updates_disabled | High – policy flag. | Static. | Inspect extension update preferences. | Possibly combine with extension list signals. |

All signals derive from authoritative local policy sources, so source_reliability is high. Since policies change only when an admin updates them (or OS distribution does on Linux), "freshness" is not a rapid concern but may lag if we poll infrequently. Absence of a policy (no JSON file or registry key) yields no finding; presence yields strong evidence. Corroboration: for example, one can verify Firefox's effective settings via about:policies or about:config, or check related browser behavior (update check logs, private mode availability, etc.). No dynamic staleness is expected beyond awaiting policy refresh. Calibration: test on real Windows, macOS, and Linux endpoints with and without policies to ensure our triggers only fire when intended, and tune severity if needed.

## Implementation Notes

Strongest signals: Firefox auto-update disabled (by DisableAppUpdate/AppAutoUpdate), custom update server, DNS-over-HTTPS disabled, Tracking Protection disabled (especially if whole TP off), and disabled private browsing. These directly reduce browser security/privacy.
Not for: Non-security UI tweaks (homepage URL, bookmarks, menus), or privacy-friendly settings (e.g. telemetry off). Policy presence alone is not risk; absence of protective defaults (like missing a "reject-tracker" cookie behavior policy) is not automatically flagged.
Execution cautions: Reading policies needs local access (registry, filesystem) and potentially elevated privileges. Mac requires the "org.mozilla.firefox" domain and possibly sudo for system defaults. Policy templates vary by Firefox version/branch; ensure mapper handles missing or renamed keys gracefully. Some Linux distros (e.g. Mint) disable updates by packaging, which appears as a managed update policy
.
Role: Mixed – some policies yield direct findings (misconfigurations), others serve as context. For example, presence of a custom extension allow/block list is "enrichment", whereas "DisableAppUpdate" is a direct indicator. The provider is primarily a signal source for browser configuration risk (tracking, update, privacy), with some fields best used as enrichment (e.g. lists of domains).
OS Support: Focus on recent Firefox releases/ESR: policies templates are up-to-date as of ~Firefox 140 (ESR 140). Initial implementation can target ESR 102+ where these policies mostly exist.

## Provider Summary and Structured JSON

```json
{
  "provider": "firefox_enterprise_policies",
  "provider_category": "tools",
  "provider_role": "local_tool_or_deferred",
  "module_mappings": [
    {
      "module": "browser_configuration",
      "provider_role": "local_tool_or_deferred",
      "provider_method": "read_registry",
      "endpoint_or_artifact": "HKLM\\SOFTWARE\\Policies\\Mozilla\\Firefox",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "Policy key exists and value non-default",
      "citation_refs": [],
      "notes": "Reads enforced policies from Windows registry (Firefox)."
    },
    {
      "module": "browser_configuration",
      "provider_role": "local_tool_or_deferred",
      "provider_method": "read_plist",
      "endpoint_or_artifact": "/Library/Preferences/org.mozilla.firefox.plist",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "EnterprisePoliciesEnabled=true and policy key exists",
      "citation_refs": [],
      "notes": "Reads managed plist policies on macOS (Firefox)."
    },
    {
      "module": "browser_configuration",
      "provider_role": "local_tool_or_deferred",
      "provider_method": "read_json",
      "endpoint_or_artifact": "/etc/firefox/policies/policies.json or /usr/lib/firefox/distribution/policies.json",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "Policy file present and key non-default",
      "citation_refs": [],
      "notes": "Reads JSON policy files on Linux (Firefox)."
    }
  ],
  "signal_contracts": [
    {
      "module": "browser_configuration",
      "source": "firefox_enterprise_policies",
      "provider": "firefox_enterprise_policies",
      "provider_method": "read_registry / read_plist / read_json",
      "signal_type": "browser_update_disabled",
      "category": "network_security",
      "severity": "medium",
      "severity_is_conditional": false,
      "conditional_rule": "",
      "entity_type": "other",
      "finding_kind": "true_finding",
      "trigger_condition": "(DisableAppUpdate = 0x1) OR (AppAutoUpdate = 0x0)",
      "evidence_fields": ["DisableAppUpdate", "AppAutoUpdate"],
      "enrichment_fields": [],
      "summary_template": "Firefox auto-update has been disabled by enterprise policy",
      "evidence_status": "documented",
      "citation_refs": [],
      "notes": "Combines both policies that turn off updates."
    },
    {
      "module": "browser_configuration",
      "source": "firefox_enterprise_policies",
      "provider": "firefox_enterprise_policies",
      "provider_method": "read_registry / read_plist / read_json",
      "signal_type": "browser_update_pinned",
      "category": "network_security",
      "severity": "low",
      "severity_is_conditional": false,
      "conditional_rule": "",
      "entity_type": "other",
      "finding_kind": "true_finding",
      "trigger_condition": "AppUpdatePin exists (non-empty string)",
      "evidence_fields": ["AppUpdatePin"],
      "enrichment_fields": [],
      "summary_template": "Firefox updates are pinned to version {{AppUpdatePin}} by policy",
      "evidence_status": "documented",
      "citation_refs": [],
      "notes": "Pinned version from policy."
    },
    {
      "module": "browser_configuration",
      "source": "firefox_enterprise_policies",
      "provider": "firefox_enterprise_policies",
      "provider_method": "read_registry / read_plist / read_json",
      "signal_type": "browser_update_url_changed",
      "category": "network_security",
      "severity": "medium",
      "severity_is_conditional": false,
      "conditional_rule": "",
      "entity_type": "other",
      "finding_kind": "true_finding",
      "trigger_condition": "AppUpdateURL exists (non-empty)",
      "evidence_fields": ["AppUpdateURL"],
      "enrichment_fields": [],
      "summary_template": "Firefox will use custom update server {{AppUpdateURL}} (policy)",
      "evidence_status": "documented",
      "citation_refs": [],
      "notes": "Assuming any custom URL is unusual (potential risk)."
    },
    {
      "module": "browser_configuration",
      "source": "firefox_enterprise_policies",
      "provider": "firefox_enterprise_policies",
      "provider_method": "read_registry / read_plist / read_json",
      "signal_type": "dns_over_https_disabled",
      "category": "privacy",
      "severity": "low",
      "severity_is_conditional": false,
      "conditional_rule": "",
      "entity_type": "other",
      "finding_kind": "true_finding",
      "trigger_condition": "DNSOverHTTPS.Enabled = 0x0 or false",
      "evidence_fields": ["DNSOverHTTPS.Enabled"],
      "enrichment_fields": [],
      "summary_template": "DNS-over-HTTPS is disabled by policy, using unencrypted DNS",
      "evidence_status": "documented",
      "citation_refs": [],
      "notes": "Protected = false (no DOH)."
    },
    {
      "module": "browser_configuration",
      "source": "firefox_enterprise_policies",
      "provider": "firefox_enterprise_policies",
      "provider_method": "read_registry / read_plist / read_json",
      "signal_type": "tracking_protection_disabled",
      "category": "privacy",
      "severity": "low",
      "severity_is_conditional": false,
      "conditional_rule": "",
      "entity_type": "other",
      "finding_kind": "true_finding",
      "trigger_condition": "EnableTrackingProtection.Value = 0x0 or false",
      "evidence_fields": ["EnableTrackingProtection.Value"],
      "enrichment_fields": [],
      "summary_template": "Firefox Tracking Protection is disabled by policy",
      "evidence_status": "documented",
      "citation_refs": [],
      "notes": ""
    },
    {
      "module": "browser_configuration",
      "source": "firefox_enterprise_policies",
      "provider": "firefox_enterprise_policies",
      "provider_method": "read_registry / read_plist / read_json",
      "signal_type": "tracking_cryptomining_disabled",
      "category": "privacy",
      "severity": "low",
      "severity_is_conditional": false,
      "conditional_rule": "",
      "entity_type": "other",
      "finding_kind": "true_finding",
      "trigger_condition": "EnableTrackingProtection.Cryptomining = 0x0 or false",
      "evidence_fields": ["EnableTrackingProtection.Cryptomining"],
      "enrichment_fields": [],
      "summary_template": "Cryptomining protection in Tracking Protection is disabled by policy",
      "evidence_status": "documented",
      "citation_refs": [],
      "notes": ""
    },
    {
      "module": "browser_configuration",
      "source": "firefox_enterprise_policies",
      "provider": "firefox_enterprise_policies",
      "provider_method": "read_registry / read_plist / read_json",
      "signal_type": "tracking_fingerprinting_disabled",
      "category": "privacy",
      "severity": "low",
      "severity_is_conditional": false,
      "conditional_rule": "",
      "entity_type": "other",
      "finding_kind": "true_finding",
      "trigger_condition": "EnableTrackingProtection.Fingerprinting = 0x0 or false",
      "evidence_fields": ["EnableTrackingProtection.Fingerprinting"],
      "enrichment_fields": [],
      "summary_template": "Fingerprinting protection in Tracking Protection is disabled by policy",
      "evidence_status": "documented",
      "citation_refs": [],
      "notes": ""
    },
    {
      "module": "browser_configuration",
      "source": "firefox_enterprise_policies",
      "provider": "firefox_enterprise_policies",
      "provider_method": "read_registry / read_plist / read_json",
      "signal_type": "tracking_email_disabled",
      "category": "privacy",
      "severity": "low",
      "severity_is_conditional": false,
      "conditional_rule": "",
      "entity_type": "other",
      "finding_kind": "true_finding",
      "trigger_condition": "EnableTrackingProtection.EmailTracking = 0x0 or false",
      "evidence_fields": ["EnableTrackingProtection.EmailTracking"],
      "enrichment_fields": [],
      "summary_template": "Email-tracking protection in Tracking Protection is disabled by policy",
      "evidence_status": "documented",
      "citation_refs": [],
      "notes": ""
    },
    {
      "module": "browser_configuration",
      "source": "firefox_enterprise_policies",
      "provider": "firefox_enterprise_policies",
      "provider_method": "read_registry / read_plist / read_json",
      "signal_type": "cookies_third_party_allowed",
      "category": "privacy",
      "severity": "low",
      "severity_is_conditional": false,
      "conditional_rule": "",
      "entity_type": "other",
      "finding_kind": "true_finding",
      "trigger_condition": "Cookies.Behavior = \"accept\"",
      "evidence_fields": ["Cookies.Behavior", "Cookies.BehaviorPrivateBrowsing"],
      "enrichment_fields": ["Cookies.Allow", "Cookies.Block"],
      "summary_template": "Cookies policy is set to \"accept all\" allowing all (including third-party) cookies",
      "evidence_status": "documented",
      "citation_refs": [],
      "notes": "Accept means no cookie blocking."
    },
    {
      "module": "browser_configuration",
      "source": "firefox_enterprise_policies",
      "provider": "firefox_enterprise_policies",
      "provider_method": "read_registry / read_plist / read_json",
      "signal_type": "private_browsing_disabled",
      "category": "privacy",
      "severity": "low",
      "severity_is_conditional": false,
      "conditional_rule": "",
      "entity_type": "other",
      "finding_kind": "true_finding",
      "trigger_condition": "DisablePrivateBrowsing = 0x1 or true",
      "evidence_fields": ["DisablePrivateBrowsing"],
      "enrichment_fields": [],
      "summary_template": "Private Browsing mode has been disabled by policy",
      "evidence_status": "documented",
      "citation_refs": [],
      "notes": ""
    },
    {
      "module": "browser_configuration",
      "source": "firefox_enterprise_policies",
      "provider": "firefox_enterprise_policies",
      "provider_method": "read_registry / read_plist / read_json",
      "signal_type": "password_manager_disabled",
      "category": "privacy/account_security",
      "severity": "low",
      "severity_is_conditional": false,
      "conditional_rule": "",
      "entity_type": "other",
      "finding_kind": "true_finding",
      "trigger_condition": "PasswordManagerEnabled = 0x0 or false",
      "evidence_fields": ["PasswordManagerEnabled"],
      "enrichment_fields": [],
      "summary_template": "The Firefox password manager is disabled by policy",
      "evidence_status": "documented",
      "citation_refs": [],
      "notes": ""
    },
    {
      "module": "browser_configuration",
      "source": "firefox_enterprise_policies",
      "provider": "firefox_enterprise_policies",
      "provider_method": "read_registry / read_plist / read_json",
      "signal_type": "extension_updates_disabled",
      "category": "network_security",
      "severity": "low",
      "severity_is_conditional": false,
      "conditional_rule": "",
      "entity_type": "other",
      "finding_kind": "true_finding",
      "trigger_condition": "ExtensionUpdate = 0x0 or false",
      "evidence_fields": ["ExtensionUpdate"],
      "enrichment_fields": [],
      "summary_template": "Firefox extension auto-updates are disabled by policy",
      "evidence_status": "documented",
      "citation_refs": [],
      "notes": ""
    }
  ],
  "confidence_guidance": [
    {
      "module": "browser_configuration",
      "signal_type_or_use_case": "browser_update_disabled",
      "source_reliability": "High – read from OS policy store (registry/JSON)",
      "freshness_considerations": "Policy files change only with admin action; treat as near-static until next policy push",
      "corroboration_rules": "Confirm with Firefox UI (about:policies) or Firefox version's update status",
      "calibration_todo": "Verify correct interpretation of combined policies (AppAutoUpdate vs DisableAppUpdate)"
    },
    {
      "module": "browser_configuration",
      "signal_type_or_use_case": "browser_update_pinned",
      "source_reliability": "High – string taken directly from policy storage",
      "freshness_considerations": "Same as above",
      "corroboration_rules": "Cross-check with Firefox About version string",
      "calibration_todo": "Map the pin value to actual version (maybe parse number)"
    },
    {
      "module": "browser_configuration",
      "signal_type_or_use_case": "browser_update_url_changed",
      "source_reliability": "Medium – value from policy JSON/registry",
      "freshness_considerations": "Custom URL may rarely change; static",
      "corroboration_rules": "Compare to known Mozilla update URLs; check SSL certificate",
      "calibration_todo": "Identify default URL; if equal, no signal"
    },
    {
      "module": "browser_configuration",
      "signal_type_or_use_case": "tracking_protection_disabled",
      "source_reliability": "High – boolean policy flag",
      "freshness_considerations": "Static until policy update",
      "corroboration_rules": "Firefox UI (Shield icon) or about:config (privacy.tracking)",
      "calibration_todo": "None needed; ensure all sub-flags handled correctly"
    },
    {
      "module": "browser_configuration",
      "signal_type_or_use_case": "dns_over_https_disabled",
      "source_reliability": "High – boolean policy flag",
      "freshness_considerations": "Stays until policy change",
      "corroboration_rules": "Can verify in Firefox DNS settings or about:networking#dns",
      "calibration_todo": "None significant; ensure reading correct data type"
    }
  ]
}
```
