---
title: "output / tools / chromium_enterprise_policies"
aliases: ["chromium_enterprise_policies output", "chromium_enterprise_policies signal registry"]
tags: [zima, research, outputs, signal-registry, tools, chromium_enterprise_policies]
type: provider_research_output
provider: chromium_enterprise_policies
provider_category: tools
status: complete
prompt_note: prompt.md
provider_folder: chromium_enterprise_policies.md
obsidianUIMode: preview
kind: reference
llm_include: true
code_scope: backend
---

## API Surface Appendix
Windows registry (Chromium-family browsers): Enterprise policies are stored under HKLM\Software\Policies[Vendor][Browser] (and HKCU\… for user policies). For Chrome/Chromium this is typically HKLM\SOFTWARE\Policies\Google\Chrome
; for Microsoft Edge it is HKLM\SOFTWARE\Policies\Microsoft\Edge
; for Brave it is HKLM\SOFTWARE\Policies\BraveSoftware\Brave
. Policies set via Group Policy (ADMX/ADML) write mandatory keys here (machine-level); user-level (HKCU) or recommended policies may also appear. Tools should read both registry hives. Absent keys mean “not set.” Registry values are typed (DWORD, string, JSON encoded) per policy definition, so parser must handle scalars, lists (often as multi-string or JSON). Errors include access denied or missing keys. Classification: utility, yields raw policy values; individual keys may be direct_signal_input if their semantic meaning triggers a finding (see signals below), otherwise enrichment_only (e.g. user-agent strings, descriptive text).

macOS plist (Managed Preferences): On macOS, policies are configured via configuration profiles or defaults, typically written to plist domains. For Chrome: domain com.google.Chrome (often in /Library/Managed Preferences/com.google.Chrome.plist or equivalent)
. For Edge: likely com.microsoft.Edge (in /Library/Preferences/, managed profiles or MDM push). For Brave: domain com.brave.browser (e.g. ~/Library/Preferences/com.brave.browser.plist)
. Parsers must read binary or XML plist files (macOS defaults system or plutil). A policy not present means “not set.” Classification: utility. Example keys: ExtensionInstallBlocklist, BlockThirdPartyCookies, etc., as plist keys. System-level vs user-level depends on installation context. No user-interaction; error if unreadable or malformed plist.

Linux JSON policy files: Chromium-family browsers read JSON policy files in /etc/.../policies/. For Chrome: managed policies in /etc/opt/chrome/policies/managed/ (and /etc/opt/chrome/policies/recommended/ for default-override)
. Chromium builds: /etc/chromium/policies/managed/. Edge (Chromium-based) on Linux: /etc/opt/edge/policies/managed/
. Brave on Linux: /etc/brave/policies/managed/
. Each JSON file contains policy keys and values. Parser should merge all files (handling recommended vs mandatory precedence). Classification: utility. Key formats identical to registry policy names. Failure cases: JSON parse errors, missing directory (not an error, means no policies present).

Policy precedence and scope: Chrome/Edge treat “mandatory” (managed) vs “recommended” differently: mandatory policies override user settings, while recommended are defaults users can change
. Windows ADMX-driven policies (HKLM) are mandatory; HKCU or recommended JSON are overrideable. Group Policy (domain) wins over local, but provider reads local copies (registry/plist/JSON). User vs machine scope: In ADMX, computer- vs user-configuration; in JSON, files under /etc/ are machine-wide. Browser profiles are per-user, but policies in managed JSON apply to all profiles on device. Classification: All policy inputs are utility; decision logic in mappers must apply correct precedence (we do not assume user-level vs machine-level without checking both hives).

Browser-specific namespace differences: Chrome and most Chromium-based browsers use the same policy keys (e.g. BlockThirdPartyCookies, ExtensionInstallForcelist) because Brave explicitly supports Chromium policies
. Edge’s registry path differs (Microsoft\Edge) but key names are largely identical (Edge documentation confirms same keys like RestoreOnStartup, SafeBrowsingEnabled etc.). Brave adds its own prefixed policies (e.g. BraveRewardsDisabled, TorDisabled)
, but these are out-of-scope for browser_configuration.

Relevant policy families (keys):

Extension management: e.g. ExtensionInstallForcelist, ExtensionInstallBlocklist, ExtensionInstallAllowlist (deprecated)
, ExtensionAllowedTypes, ExtensionInstallSources, BlockExternalExtensions (Edge/Brave may use same keys). These appear as list or string values.
Cookie/site data: e.g. BlockThirdPartyCookies (boolean)
, CookiesAllowedForUrls, CookiesBlockedForUrls (string-list of patterns)
, DefaultCookiesSetting (enum 1/2/4)
.
Privacy/Tracking: e.g. SafeBrowsingEnabled (boolean)
, MetricsReportingEnabled (boolean)
, PasswordManagerEnabled, PasswordManagerAllowShowPasswords, AutoFillEnabled
, other telemetry or sync policies (SigninAllowed disables Chrome sign-in)
.
Sign-in/Sync: e.g. SyncDisabled, SigninAllowed
, PasswordProtectionWarningTrigger (for password leak warnings) – these are secondary, likely enrichment_only for browser_configuration.
Out-of-scope policies: Browser-updates (AutoUpdateCheckPeriod, etc.), browser-UI tweaks (e.g. ShowHomeButton
), bookmark management, default search config (unless clearly security-related), captive portal login URL (network scope), etc. These do not directly signal misconfiguration risks and would not emit standalone signals in browser_configuration.
Artifact stability: Policy keys in ADMX/JSON are stable, but deprecated legacy keys (e.g. Whitelist vs Allowlist, Blacklist vs Blocklist
) must be normalized. We focus on current (Allowlist/Blocklist) and note if encountering old keys. Extensions of policy JSON (Chrome policies for testing) are uncommon. Brave-specific keys (Tor, VPN, Sync URL) are unstable for our browser_configuration module, so we treat them out_of_scope.

Result variants:

Policies present and parseable: parse values, emit data for mapper.
No policies present: output empty/None, no direct signals.
Partial policy presence: e.g. list-valued policies with some entries – treat non-empty only.
Browser installed but policy source absent: equivalent to “no policies”.
Policy unsupported by browser: e.g. an Edge-only policy on Chrome – ignore key.
Errors: Permission denied (skip or error-log), malformed JSON (skip file). Mappers should gracefully handle parse issues by skipping invalid entries.
Implementation schema details:

Browser/vendor identification: Inspect known registry domains (Google\Chrome, Microsoft\Edge, BraveSoftware\Brave) and JSON paths to infer browser. Normalize key names across vendors (e.g. Brave uses same key names internally, so provider can output browser_name field).
Value types: Boolean, integer (enum), string, list-of-strings. E.g. BlockThirdPartyCookies: boolean; ExtensionInstallForcelist: list of “id;url” strings
; DefaultCookiesSetting: integer enum 1/2/4
; CookiesAllowedForUrls: list of URL pattern strings
.
Mandatory vs recommended: We do not mark difference in data, but mapper should treat missing keys as “not set” (therefore default user behavior).
Identity fields: Extension policies use extension ID (32-chars) and update URL (often the Chrome Web Store update URL). Cookies policies use URL patterns (strings).
Evidence: Raw policy values (e.g. "BlockThirdPartyCookies": false) are saved.
Unused text: Policy captions/descriptions from ADMX are not data fields.
Sources: Official Chromium policy docs and help guides
 for storage details.

## Module Mapping Table
module	provider_role	provider_method	endpoint_or_artifact	classification	entity_types	gating_logic	citation_refs	notes
browser_configuration	local_tool_or_deferred	read_registry	Windows registry policies path (HKLM\...\Policies\...\Chrome/Edge/Brave)	direct_signal_input	hostname	If policy key exists and value indicates non-default (e.g. ExtensionInstallForcelist non-empty)
Parses all extension, cookie, privacy keys from registry; delivers raw values for mapper.
browser_configuration	local_tool_or_deferred	read_plist	macOS plist policies (~/Library/Preferences/com.*.plist)	direct_signal_input	hostname	As above for registry keys, but from plist files
Similar to registry: collect keys from Chrome/Edge/Brave plist domains.
browser_configuration	local_tool_or_deferred	read_json	Linux JSON policies (`/etc/opt/chrome	edge/brave/policies/managed/*.json`)	direct_signal_input	hostname	As above, if JSON file present, parse keys
browser_configuration	local_tool_or_deferred	aggregate_policies	All combined policy sources	utility_only	hostname	After collecting registry/plist/JSON, aggregate into unified policy dict
Provider outputs unified policy set for the machine.
browser_configuration	local_tool_or_deferred	-	Extension policy keys (Forcelist, Blocklist, Allowlist, AllowedTypes, InstallSources, BlockExternalExtensions)	direct_signal_input	hostname	Value present and non-empty (e.g. list not empty)
Used to generate extension-related signals (force-install etc).
browser_configuration	local_tool_or_deferred	-	Cookie policy keys (BlockThirdPartyCookies, CookiesAllowedForUrls, etc.)	mixed (see signals)	hostname	BlockThirdPartyCookies set explicitly to false triggers, lists simply recorded
Used to generate third-party cookie signals or contextual enrichment.
browser_configuration	local_tool_or_deferred	-	Privacy/telemetry keys (SafeBrowsingEnabled, MetricsReportingEnabled, SigninAllowed, PasswordManagerEnabled…)	mixed (see signals)	hostname	SafeBrowsingEnabled=false triggers, others typically just context
SafeBrowsing disabled yields signal; metrics/sign-in mostly enrichment.

Notes: The read_registry/read_plist/read_json entries represent the primary retrieval of raw policy values (utility). The grouped “extension keys,” “cookie keys,” etc., indicate how mapper logic will treat those fields for signals (some direct, some enrichment). Classification: we label source artifacts as direct_signal_input when their values can produce standalone true_finding signals (per section C), or utility_only for raw aggregation. Entity type “hostname” is used because policies apply to the device/browser instance.

## Signal Contracts, Severity, and Tags
module	source	provider	provider_method	signal_type	category	severity	severity_is_conditional	conditional_rule	entity_type	finding_kind	trigger_condition	evidence_fields	enrichment_fields	summary_template	evidence_status	citation_refs	notes
browser_configuration	chromium_enterprise_policies	chromium_enterprise_policies	aggregate_policies	extension_force_installed	browser_security (config)	low	no	–	account	true_finding	ExtensionInstallForcelist key exists and list contains entries	ExtensionInstallForcelist (list of strings)	(none)	Browser is configured to silently install extension {{value}}	documented
One signal per listed extension (ID and URL). Entity_type “account” is an approximation; could be “application”.
browser_configuration	chromium_enterprise_policies	chromium_enterprise_policies	aggregate_policies	safe_browsing_disabled	privacy	high	no	–	hostname	true_finding	SafeBrowsingEnabled == false	SafeBrowsingEnabled	(none)	Safe Browsing is disabled by policy	documented
Disabling safe browsing removes anti-phishing/malware protection.
browser_configuration	chromium_enterprise_policies	chromium_enterprise_policies	aggregate_policies	third_party_cookies_allowed	privacy	medium	no	–	hostname	true_finding	BlockThirdPartyCookies == false	BlockThirdPartyCookies	(none)	Third-party cookies are allowed by policy	documented
Allowed 3P cookies increase tracking risk; policy presence is direct evidence.

Notes: We do not emit signals for merely present policies that do not indicate insecure configuration. For example, a non-empty blocklist or allowlist without more context is not signaled. Only the above cases (forced-install extension, safe browsing disabled, 3P cookies allowed) are treated as standalone true_finding. All other policy-driven data (e.g. metrics enabled/disabled, sign-in disabled, cookie URL allowlists) remain contextual_enrichment and are not listed here.

## Confidence Guidance
module	signal_type/use_case	source_reliability	freshness_considerations	corroboration_rules	calibration_todo
browser_configuration	extension_force_installed	High: policies in registry/JSON are authoritative (admin-set)
.	Policy values persist until changed; infrequent. Verified at runtime via chrome://policy.	Check installed extension list or browser_extensions signals for consistency.	Compare frequency of force-list vs actual installed to refine confidence.
browser_configuration	safe_browsing_disabled	High: local policy read is reliable
.	Persistent until changed; effective immediately on policy load.	Validate via browser settings UI or browser://version flags, if available.	Monitor if enterprise policies always coincide with actual safe-browsing state.
browser_configuration	third_party_cookies_allowed	High: direct policy flag
.	Policy may be overridden by higher policy (domain-level). Confirm actual effect via browser UI or behavior.	Check browser_settings (if any) or content blocking telemetry.	Ensure 3P cookie allowance equates to risk in practice (e.g. instrument site tests).

Notes: Local policy sources are highly reliable (device management). Freshness is “static” until an admin changes policy; no streaming updates are expected unless policies are re-applied. Corroboration may involve the browser’s own settings pages or configuration introspection APIs. Confidence starts high but should be calibrated against real-world data (e.g. some “allowed 3P cookies” policies might not be abused, adjust severity or confidence accordingly).

## Implementation Notes
Strongest signals: Forced extension install entries and disabling of key security features (Safe Browsing, 3rd-party cookies blocking) yield the strongest findings. Extension force-installs may indicate tightly controlled environments (or potentially malicious pre-installed tools). Safe Browsing off and 3P cookies allowed are config misconfiguration signals.
What not to use for: This provider should not generate alerts for every present policy. Many policies simply enforce corporate defaults (e.g. HomePage location, default search) that are not security issues. Do not treat presence of an enforced homepage or default search as a finding.
Execution and support cautions: Runs locally with minimal privileges (reading HKLM/HKCU requires admin). Registry/plist/JSON parsing must handle access denied gracefully. On Windows, 32-bit vs 64-bit registry views should be consistent. Mac plists might be in binary format. If browser not present, policy stores may still exist. Unsupported keys (policy names present in registry that the current browser version does not use) should be ignored.
Signal vs enrichment: Generally, consider this provider mixed: certain policies (see signals) produce findings; others merely enrich context. Treat policy settings as configuration evidence, not directly as threats. Only report when a policy explicitly weakens security (e.g. disabling protections). Otherwise, list policy values as evidence fields or tags for context.
## Provider Summary and Structured JSON

```json
{
  "provider": "chromium_enterprise_policies",
  "provider_category": "tools",
  "provider_role": "local_tool_or_deferred",
  "module_mappings": [
    {
      "module": "browser_configuration",
      "provider_role": "local_tool_or_deferred",
      "provider_method": "read_registry",
      "endpoint_or_artifact": "HKLM\\Software\\Policies\\[Vendor]\\[Browser]",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "Policy key exists and value non-default",
      "citation_refs": ["【2†L63-L70】", "【43†L201-L204】"],
      "notes": "Reads enforced policies from Windows registry (Chrome, Edge, Brave)."
    },
    {
      "module": "browser_configuration",
      "provider_role": "local_tool_or_deferred",
      "provider_method": "read_plist",
      "endpoint_or_artifact": "~/Library/Preferences/com.*.plist",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "Policy key exists and value non-default",
      "citation_refs": ["【50†L1-L4】", "【3†L48-L51】"],
      "notes": "Reads managed plist policies on macOS (Chrome, Edge, Brave)."
    },
    {
      "module": "browser_configuration",
      "provider_role": "local_tool_or_deferred",
      "provider_method": "read_json",
      "endpoint_or_artifact": "/etc/opt/*/policies/managed/*.json",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "Policy file present and key non-default",
      "citation_refs": ["【3†L52-L60】", "【49†L91-L99】"],
      "notes": "Reads JSON policy files on Linux (Chrome, Edge, Brave)."
    }
  ],
  "signal_contracts": [
    {
      "module": "browser_configuration",
      "source": "chromium_enterprise_policies",
      "provider": "chromium_enterprise_policies",
      "provider_method": "aggregate_policies",
      "signal_type": "extension_force_installed",
      "category": "browser_security",
      "severity": "low",
      "severity_is_conditional": "no",
      "conditional_rule": "",
      "entity_type": "account",
      "finding_kind": "true_finding",
      "trigger_condition": "`ExtensionInstallForcelist` present and contains entries",
      "evidence_fields": ["ExtensionInstallForcelist"],
      "enrichment_fields": [],
      "summary_template": "Browser is configured to force-install extension {{value}}",
      "evidence_status": "documented",
      "citation_refs": ["【29†L1585-L1613】"],
      "notes": "One finding per extension ID; extension IDs serve as the 'value' placeholder."
    },
    {
      "module": "browser_configuration",
      "source": "chromium_enterprise_policies",
      "provider": "chromium_enterprise_policies",
      "provider_method": "aggregate_policies",
      "signal_type": "safe_browsing_disabled",
      "category": "privacy",
      "severity": "high",
      "severity_is_conditional": "no",
      "conditional_rule": "",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "`SafeBrowsingEnabled == false`",
      "evidence_fields": ["SafeBrowsingEnabled"],
      "enrichment_fields": [],
      "summary_template": "Safe Browsing protection is disabled by policy",
      "evidence_status": "documented",
      "citation_refs": ["【54†L704-L712】"],
      "notes": ""
    },
    {
      "module": "browser_configuration",
      "source": "chromium_enterprise_policies",
      "provider": "chromium_enterprise_policies",
      "provider_method": "aggregate_policies",
      "signal_type": "third_party_cookies_allowed",
      "category": "privacy",
      "severity": "medium",
      "severity_is_conditional": "no",
      "conditional_rule": "",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "`BlockThirdPartyCookies == false`",
      "evidence_fields": ["BlockThirdPartyCookies"],
      "enrichment_fields": [],
      "summary_template": "Third-party cookies are allowed by policy",
      "evidence_status": "documented",
      "citation_refs": ["【31†L1819-L1827】"],
      "notes": ""
    }
  ],
  "confidence_guidance": [
    {
      "module": "browser_configuration",
      "signal_type_or_use_case": "extension_force_installed",
      "source_reliability": "High (direct registry/JSON read)【29†L1585-L1613】",
      "freshness_considerations": "Persistence until admin changes; reflects current policy.",
      "corroboration_rules": "Cross-check installed extensions or browser cloud management reports.",
      "calibration_todo": "Validate that forced-extension IDs correspond to expected enterprise apps."
    },
    {
      "module": "browser_configuration",
      "signal_type_or_use_case": "safe_browsing_disabled",
      "source_reliability": "High (policy read)【54†L704-L712】",
      "freshness_considerations": "Static; changes only when policy updated. Verified on policy load.",
      "corroboration_rules": "Browser’s chrome://settings/ or chrome://policy can confirm this state.",
      "calibration_todo": "Monitor how often admins disable Safe Browsing in practice."
    },
    {
      "module": "browser_configuration",
      "signal_type_or_use_case": "third_party_cookies_allowed",
      "source_reliability": "High (policy read)【31†L1819-L1827】",
      "freshness_considerations": "Static until admin changes. Policy immediately affects behavior.",
      "corroboration_rules": "Use browser UI or content tests to confirm third-party cookie behavior.",
      "calibration_todo": "Assess risk of 3P cookie allowance in different enterprise contexts."
    }
  ]
}
```
