---
title: "output / tools / osquery"
aliases: ["osquery output", "osquery signal registry"]
tags: [zima, research, outputs, signal-registry, tools, osquery, graph_exclude]
type: provider_research_output
provider: osquery
provider_category: tools
status: not_started
prompt_note: prompt.md
provider_folder: osquery.md
obsidianUIMode: preview
---


# A. Tool/API Surface Appendix

**os_version (os_security, patch_status)** – Core system table (all OS) providing OS name, version, build, platform, architecture. Fields: `name`, `version`, `major`, `minor`, `patch`, `build`, `platform`, `platform_like`, `codename`, `arch` (always present), plus `extra` on macOS and `install_date`, `revision` on Windows. No auth needed. Output: one row. Use: staleness comparison.

**disk_encryption (os_security)** – Linux/macOS (not Windows) table reporting per-disk encryption. Fields: `name`, `uuid`, `encrypted` (INT 1/0), `type`, `encryption_status` (“encrypted”/“not encrypted”/“undefined”). On macOS, extra fields: `filevault_status` (“on”/“off”/“unknown”), `uid`, `user_uuid`. Always present on supported platform. Use: disk encryption status. Trigger: if `encryption_status!="encrypted"` or `encrypted=0`.

**bitlocker_info (os_security)** – Windows-only table. Fields: `device_id`, `drive_letter`, `conversion_status`, `protection_status`, `encryption_method`, `version`, `percentage_encrypted`, `lock_status`. Use: BitLocker state. Trigger: if `percentage_encrypted < 100` or `protection_status=0` etc. (Require Admin on Windows).

**alf (os_security)** – macOS-only (pre-Sequoia) Application Layer Firewall status. Fields: `global_state` (0=disabled, 1=enabled, 2=block all) and flags (`allow_signed_enabled`, `logging_enabled`, `stealth_enabled`, etc.). Use: if `global_state=0` → firewall disabled. (Requires root reading /Library/Preferences).

**iptables (os_security)** – Linux-only table of firewall rules. Fields include `chain`, `policy` (e.g. “ACCEPT”/“DROP”), `protocol`, `target`, ports/IPs, etc. No direct “enabled” flag. Use: if chain=`INPUT` and policy=`ACCEPT` (no filtering) → firewall disabled (inferred). Root required.

**windows_firewall_rules (os_security)** – Windows-only table of firewall rules. Fields: `name`, `enabled` (INT), `direction`, `action` (“Allow”/“Block”), `profile_*` (domain/private/public flags), etc. Use: complex; standalone signals not trivial. Likely enrichment only (list of rules).

**system_info (os_security)** – Core (all OS) system hardware and identity. Fields: `hostname`, `uuid`, CPU (cores, brand), `physical_memory`, vendor/model/serial, etc. Always one row. Use: enrichment (device identity).

**screenlock (os_security)** – macOS-only current user’s screen lock. Fields: `enabled` (INT 1=locked after sleep/screen, 0=not) and `grace_period` (seconds). Trigger: if `enabled=0` (no lock). (Requires user logged in context).

**sip_config (os_security)** – macOS-only SIP status. Fields: `config_flag` (e.g. “sip”) and `enabled` (INT 1/0). Trigger: if row for `config_flag='sip'` has `enabled=0` (SIP disabled). (Admin privilege).

**gatekeeper (os_security)** – macOS-only Gatekeeper status. Fields: `assessments_enabled` (INT 1/0), `dev_id_enabled` (1/0). Trigger: if `assessments_enabled=0` (Gatekeeper off).

**secureboot (os_security)** – Multi-OS table. Fields: `secure_boot` (INT; 1 if enabled) on Windows/Linux/Mac; plus macOS-specific `description`, `secure_mode` (0/1/2), etc. Trigger: if `secure_boot=0` (disabled). (Requires UEFI access).

**windows_updates** – _Fleet_ table (non-core) listing available updates (WMI). Out-of-scope (non-core, not used).

**windows_optional_features** – Windows core table of installed OS features. Fields: `name`, `state` (1=Enabled,2=Disabled,3=Absent). Used mainly for OS inventory, not patch gaps. Likely enrichment/unused for patch status.

**apt_sources (patch_status)** – Linux table (APT repos). Fields: `name`, `base_uri`, `components`, `release`, `maintainer`, etc. Enrichment only (repository context). No signals.

**deb_packages (patch_status/software_vuln)** – Linux (Debian) package inventory. Fields: `name`, `version`, `source`, `status`, etc. Utility (for vulnerability scanning; not direct signals).

**rpm_packages (software_vuln)** – Linux (RPM) package inventory. Fields: `name`, `version`, `release`, `arch`, etc. Utility.

**homebrew_packages (patch_status/software_vuln)** – macOS Homebrew inventory. Fields: `name`, `version`, `type` (‘formula’/‘cask’), `auto_updates`, etc. Utility.

**programs (software_vuln)** – Windows installed programs. Fields: `name`, `version`, `publisher`, `install_location`, etc. Utility.

**apps (software_vuln)** – macOS applications. Fields: `bundle_name`, `bundle_version`, `bundle_identifier`, `path`, `last_opened_time`, etc. Utility.

**chrome_extensions (extension_risk)** – Multi-OS (macOS/Win/Linux) Chrome/Chromium extension inventory. Fields: `browser_type`, `identifier` (ID), `name`, `version`, `permissions`, `path`, `state` (enabled=“1”), etc. Enrichment (lists installed extensions). Note: covers Chrome-based browsers including Edge/Brave.

**firefox_addons (extension_risk)** – Multi-OS. (Documentation sparse.) Fields likely include `uid`, `name`, `identifier` (ID), `version`, `permissions`, etc (Fleet schemas suggest similar to Chrome). Enrichment only.

**safari_extensions (extension_risk)** – macOS-only Safari extensions. Fields: `identifier`, `name`, `version`, `bundle_version`, `sdk`, etc. Enrichment.

**chrome_extension_content_scripts (browser_configuration)** – Multi-OS (Chrome/Chromium). Fields: `browser_type`, `identifier` (extension ID), `match` (URL pattern), `script` (content script code or path), `path`, `profile_path`, etc. Enrichment (content script URLs/patterns per extension).

_No other browser policy tables are present in osquery._

**Platform availability summary:** Many tables are OS-specific. For each above, availability is noted (macOS only, Windows only, Linux only, or multi-OS). Several tables (e.g., firewall, encryption, SIP) require elevated privileges or Full-Disk Access (macOS) to read.

# B. Module Mapping Table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|os_security|direct_signal|os_version|`os_version` table|direct_signal_input|device|Always returns row (no gating)||Used to check OS freshness (patch_status).|
|os_security|direct_signal|disk_encryption|`disk_encryption` table|direct_signal_input|device|Only if `encryption_status!="encrypted"` or `encrypted=0`||Linux/macOS only; root required.|
|os_security|direct_signal|bitlocker_info|`bitlocker_info` table|direct_signal_input|device|Only if `percentage_encrypted < 100` or `protection_status=0`||Windows only; Admin privileges required.|
|os_security|direct_signal|alf|`alf` table|direct_signal_input|device|Only if `global_state=0`||macOS only (pre-15).|
|os_security|enrichment_only|iptables|`iptables` table|enrichment_only|device|None (table lists all rules).||Linux only; root required.|
|os_security|enrichment_only|windows_firewall_rules|`windows_firewall_rules` table|enrichment_only|device|None (lists all rules).||Windows only.|
|os_security|enrichment_only|system_info|`system_info` table|utility_only|device|None.||All OS; always returns one row.|
|os_security|direct_signal|screenlock|`screenlock` table|direct_signal_input|device|Only if `enabled=0`||macOS only (current user context).|
|os_security|direct_signal|sip_config|`sip_config` table|direct_signal_input|device|Only if `config_flag='sip' AND enabled=0`||macOS only; Admin privileges required.|
|os_security|direct_signal|gatekeeper|`gatekeeper` table|direct_signal_input|device|Only if `assessments_enabled=0`||macOS only.|
|os_security|direct_signal|secureboot|`secureboot` table|direct_signal_input|device|Only if `secure_boot=0`||Linux/Windows/macOS.|
|patch_status|enrichment_only|os_version|`os_version` table|utility_only|device|None (one row).||Used to compute OS staleness (patch logic).|
|patch_status|out_of_scope|windows_updates|(fleet) `windows_updates` table|out_of_scope|device|N/A.||Non-core; skip.|
|patch_status|enrichment_only|apt_sources|`apt_sources` table|utility_only|device|None.||Linux only.|
|patch_status|utility_only|deb_packages|`deb_packages` table|utility_only|device|None. (inventory)||Linux only.|
|patch_status|utility_only|homebrew_packages|`homebrew_packages` table|utility_only|device|None.||macOS only.|
|software_vuln|utility_only|programs|`programs` table|utility_only|device|None.||Windows only.|
|software_vuln|utility_only|apps|`apps` table|utility_only|device|None.||macOS only.|
|software_vuln|utility_only|deb_packages|`deb_packages` table|utility_only|device|None.||Linux only.|
|software_vuln|utility_only|rpm_packages|`rpm_packages` table|utility_only|device|None.||Linux only.|
|software_vuln|utility_only|homebrew_packages|`homebrew_packages` table|utility_only|device|None.||macOS only.|
|extension_risk|enrichment_only|chrome_extensions|`chrome_extensions` table|enrichment_only|device|None.||Multi-OS (Chrome/Edge/etc.).|
|extension_risk|enrichment_only|firefox_addons|`firefox_addons` table|enrichment_only|device|None.|_undocumented_|Multi-OS (Firefox).|
|extension_risk|enrichment_only|safari_extensions|`safari_extensions` table|enrichment_only|device|Requires Full Disk Access (osquery)||macOS only.|
|browser_config|enrichment_only|chrome_extension_content_scripts|`chrome_extension_content_scripts` table|enrichment_only|device|Requires JOIN with `users`.||Multi-OS (Chrome/Chromium).|

# C. Signal Contract Table

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|os_security|os_security|osquery|disk_encryption|disk_encryption_disabled|device_security|high|no|`encrypted=0 OR encryption_status!="encrypted"` (Linux/macOS)|device|true_finding|`disk_encryption.encryption_status != "encrypted"` (or `encrypted=0`)|`name`, `uuid`, `encryption_status`, `filevault_status` (if present)|`type`, `encryption_method`, `percentage_encrypted`|Disk **<device name>** is **unencrypted** (no full-disk encryption enabled).|documented||Only Linux/macOS. Windows uses BitLocker (separate signal).|
|os_security|os_security|osquery|bitlocker_info|disk_encryption_disabled|device_security|high|no|`percentage_encrypted < 100 OR protection_status=0`|device|true_finding|`bitlocker_info.percentage_encrypted < 100` or `bitlocker_info.protection_status = 0`|All fields of this table (for evidence)|`encryption_method`, `conversion_status`, `drive_letter`|BitLocker encryption incomplete/disabled on **<drive_letter>** (Windows).|documented||Windows only; rename consolidated signal type “disk_encryption_disabled”.|
|os_security|os_security|osquery|alf|firewall_disabled|device_security|high|no|`global_state = 0`|device|true_finding|`alf.global_state = 0`|All `alf.*` fields|`allow_signed_enabled`, `logging_enabled`, `stealth_enabled`|macOS firewall **OFF** on host.|documented||macOS only (ALF deprecated on 15+).|
|os_security|os_security|osquery|iptables|firewall_disabled|device_security|high|yes|`iptables.chain = "INPUT" AND iptables.policy = "ACCEPT"`|device|true_finding|`iptables.chain = "INPUT" AND iptables.policy = "ACCEPT"`|All `iptables.*` fields|`target`, `protocol`, `src_ip`, `dst_ip`|Linux firewall default ACCEPT (no filtering).|derived||Requires logic: if no DROP policy on INPUT chain.|
|os_security|os_security|osquery|screenlock|screenlock_disabled|device_security|medium|no|`enabled = 0`|device|true_finding|`screenlock.enabled = 0`|`enabled`, `grace_period`||Screen lock **disabled** on macOS host.|documented||macOS only.|
|os_security|osquery_agent|osquery|sip_config|sip_disabled|device_security|high|no|`config_flag="sip" AND enabled = 0`|device|true_finding|`sip_config.config_flag="sip" AND sip_config.enabled = 0`|`config_flag`, `enabled`|`enabled_nvram`|System Integrity Protection (**SIP**) is **disabled**.|documented||macOS only.|
|os_security|osquery_agent|osquery|gatekeeper|gatekeeper_disabled|device_security|high|no|`assessments_enabled = 0`|device|true_finding|`gatekeeper.assessments_enabled = 0`|`assessments_enabled`, `dev_id_enabled`||macOS Gatekeeper is **disabled**.|documented||macOS only.|
|os_security|osquery_agent|osquery|secureboot|secure_boot_disabled|device_security|high|no|`secure_boot = 0`|device|true_finding|`secureboot.secure_boot = 0`|`secure_boot`, `setup_mode`||Secure Boot is **disabled**.|documented||Windows/Linux/macOS (macOS Intel with modern EFI).|
|patch_status|zima_patch_module|osquery|os_version|os_out_of_date|device_security|high|yes|_OS version more than X behind latest_ (not in provider)|device|true_finding|_Compare `os_version` vs latest known (external logic)_|`name`, `version`, `major`, `minor`, `patch`, `build`||OS **<name>** is **outdated** (current: <version>).|documented||Patch logic threshold defined in module; severity conditional.|
|–|–|–|–|–|–|–|–|–|–|–|–|–|–|–|–|–|No other standalone signals (all others utility/enrichment).|

# D. Confidence Guidance

|module|signal_type/use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|os_security|disk_encryption_disabled|High (direct OS query)|Always current when queried; static until change.|Compare Windows BitLocker (provider) to confirm (via BitLocker APIs)|Validate mapping of `encryption_status` to risk.|
|os_security|firewall_disabled|Medium-High (from OS state)|Reflects current firewall rules; may change with updates.|Could combine alf+iptables+windows rules; external firewall state checks.|Define Linux default chain logic precisely.|
|os_security|screenlock_disabled|Medium (user setting)|Changing with user prefs; may need periodic check.|Cross-check with login policies.|Confirm severity (Maybe medium vs high).|
|os_security|sip_disabled|High (OS config)|Rarely changes; static until admin toggles.|Gatekeeper status may correlate (should also be disabled if SIP off).|None.|
|os_security|gatekeeper_disabled|High (OS config)|Static until user changes; periodic checks fine.|SIP status correlation.|None.|
|os_security|secure_boot_disabled|High (firmware setting)|Static per boot; only changes on reboot of config.|Compare `setup_mode` (should be 0 if secure_boot=0).|Validate secure_mode mapping if present.|
|patch_status|os_out_of_date|High (OS version read from system)|Requires latest version data for comparison; update thresholds regularly.|Compare with vendor update APIs or patch reports.|Define X-month old cutoff.|
|software_vuln|inventory data|High (package DB)|Becomes stale as software updates; requires periodic re-scan.|Use for vulnerability scans (external).|N/A (utility only).|
|extension_risk|extension inventory|High (file system query)|User installs/uninstalls may occur anytime; run periodically.|Check lists of known bad IDs (external DB).|Identify any missing fields (e.g. Firefox specifics).|
|browser_config|content_scripts inventory|High (config files)|Likely static per install; re-run after browser update.|Inspect loaded scripts; correlate with domain lists.|N/A (enrichment).|

# E. Provider Summary

1. **Strongest signals:** Disk encryption disabled, firewall disabled, screen lock disabled, SIP/Gatekeeper disabled, Secure Boot disabled – all high-impact device posture findings.
2. **Not for:** CVE detection (no built-in vulnerability scoring), or standalone threats (no alerts, just data). Do _not_ treat raw inventory as signals without context.
3. **Privilege cautions:** Many tables require admin/root (e.g. firewall rules, encryption status, `/Library/Preferences`, etc.), and macOS tables like `safari_extensions` require Full-Disk Access.
4. **Role:** osquery is primarily a **utility/inventory** collector. It provides raw configuration facts. Zima modules decide what is “risky”. Generally use osquery outputs for **enrichment** (software lists, extension lists) and occasional **direct signals** for clear misconfigurations (e.g. no encryption, no firewall). No rate limits (local agent).

{
  "provider": "osquery",
  "provider_category": "tools",
  "provider_role": "utility_only",
  "module_mappings": [
    {"module":"os_security","provider_role":"direct_signal","provider_method":"disk_encryption","endpoint_or_artifact":"disk_encryption table","classification":"direct_signal_input","entity_types":["device"],"gating_logic":"encryption_status fields present","citation_refs":"【13†L319-L327】","notes":"Linux/macOS only. Requires root."},
    {"module":"os_security","provider_role":"direct_signal","provider_method":"bitlocker_info","endpoint_or_artifact":"bitlocker_info table","classification":"direct_signal_input","entity_types":["device"],"gating_logic":"BitLocker fields present","citation_refs":"【1†L8-L13】","notes":"Windows only. Requires Admin."},
    {"module":"os_security","provider_role":"direct_signal","provider_method":"alf","endpoint_or_artifact":"alf table","classification":"direct_signal_input","entity_types":["device"],"gating_logic":"alf.global_state present","citation_refs":"【21†L95-L101】","notes":"macOS only (pre-15)."},
    {"module":"os_security","provider_role":"enrichment_only","provider_method":"iptables","endpoint_or_artifact":"iptables table","classification":"enrichment_only","entity_types":["device"],"gating_logic":"iptables table present","citation_refs":"【32†L103-L110】","notes":"Linux only. Root required."},
    {"module":"os_security","provider_role":"enrichment_only","provider_method":"windows_firewall_rules","endpoint_or_artifact":"windows_firewall_rules table","classification":"enrichment_only","entity_types":["device"],"gating_logic":"table present","citation_refs":"【31†L91-L100】","notes":"Windows only."},
    {"module":"os_security","provider_role":"utility_only","provider_method":"system_info","endpoint_or_artifact":"system_info table","classification":"enrichment_only","entity_types":["device"],"gating_logic":"table present","citation_refs":"【48†L315-L324】","notes":"All OS. Always one row."},
    {"module":"os_security","provider_role":"direct_signal","provider_method":"screenlock","endpoint_or_artifact":"screenlock table","classification":"direct_signal_input","entity_types":["device"],"gating_logic":"screenlock.enabled present","citation_refs":"【36†L277-L284】","notes":"macOS only (current user context)."},
    {"module":"os_security","provider_role":"direct_signal","provider_method":"sip_config","endpoint_or_artifact":"sip_config table","classification":"direct_signal_input","entity_types":["device"],"gating_logic":"row with config_flag = 'sip'","citation_refs":"【38†L93-L96】","notes":"macOS only."},
    {"module":"os_security","provider_role":"direct_signal","provider_method":"gatekeeper","endpoint_or_artifact":"gatekeeper table","classification":"direct_signal_input","entity_types":["device"],"gating_logic":"gatekeeper.assessments_enabled present","citation_refs":"【42†L285-L293】","notes":"macOS only."},
    {"module":"os_security","provider_role":"direct_signal","provider_method":"secureboot","endpoint_or_artifact":"secureboot table","classification":"direct_signal_input","entity_types":["device"],"gating_logic":"secureboot.secure_boot present","citation_refs":"【44†L103-L110】","notes":"Windows/Linux/macOS."},
    {"module":"patch_status","provider_role":"utility_only","provider_method":"os_version","endpoint_or_artifact":"os_version table","classification":"utility_only","entity_types":["device"],"gating_logic":"table present","citation_refs":"【19†L319-L327】","notes":"All OS."},
    {"module":"patch_status","provider_role":"utility_only","provider_method":"apt_sources","endpoint_or_artifact":"apt_sources table","classification":"utility_only","entity_types":["device"],"gating_logic":"table present","citation_refs":"【54†L91-L100】","notes":"Linux only."},
    {"module":"patch_status","provider_role":"utility_only","provider_method":"deb_packages","endpoint_or_artifact":"deb_packages table","classification":"utility_only","entity_types":["device"],"gating_logic":"table present","citation_refs":"【58†L310-L319】","notes":"Linux only."},
    {"module":"patch_status","provider_role":"utility_only","provider_method":"homebrew_packages","endpoint_or_artifact":"homebrew_packages table","classification":"utility_only","entity_types":["device"],"gating_logic":"table present","citation_refs":"【60†L91-L99】","notes":"macOS only."},
    {"module":"software_vulnerability","provider_role":"utility_only","provider_method":"programs","endpoint_or_artifact":"programs table","classification":"utility_only","entity_types":["device"],"gating_logic":"table present","citation_refs":"【64†L304-L312】","notes":"Windows only."},
    {"module":"software_vulnerability","provider_role":"utility_only","provider_method":"apps","endpoint_or_artifact":"apps table","classification":"utility_only","entity_types":["device"],"gating_logic":"table present","citation_refs":"【66†L89-L98】","notes":"macOS only."},
    {"module":"software_vulnerability","provider_role":"utility_only","provider_method":"deb_packages","endpoint_or_artifact":"deb_packages table","classification":"utility_only","entity_types":["device"],"gating_logic":"table present","citation_refs":"【58†L310-L319】","notes":"Linux only."},
    {"module":"software_vulnerability","provider_role":"utility_only","provider_method":"rpm_packages","endpoint_or_artifact":"rpm_packages table","classification":"utility_only","entity_types":["device"],"gating_logic":"table present","citation_refs":"【70†L302-L311】","notes":"Linux only."},
    {"module":"software_vulnerability","provider_role":"utility_only","provider_method":"homebrew_packages","endpoint_or_artifact":"homebrew_packages table","classification":"utility_only","entity_types":["device"],"gating_logic":"table present","citation_refs":"【60†L91-L99】","notes":"macOS only."},
    {"module":"extension_risk","provider_role":"enrichment_only","provider_method":"chrome_extensions","endpoint_or_artifact":"chrome_extensions table","classification":"enrichment_only","entity_types":["device"],"gating_logic":"table present","citation_refs":"【74†L342-L350】【74†L387-L395】","notes":"Multi-OS (Chrome/Edge/Brave etc.)."},
    {"module":"extension_risk","provider_role":"enrichment_only","provider_method":"firefox_addons","endpoint_or_artifact":"firefox_addons table","classification":"enrichment_only","entity_types":["device"],"gating_logic":"table present","citation_refs":"Fleet schema","notes":"Multi-OS (Firefox)."},
    {"module":"extension_risk","provider_role":"enrichment_only","provider_method":"safari_extensions","endpoint_or_artifact":"safari_extensions table","classification":"enrichment_only","entity_types":["device"],"gating_logic":"table present","citation_refs":"【79†L93-L102】","notes":"macOS only."},
    {"module":"browser_configuration","provider_role":"enrichment_only","provider_method":"chrome_extension_content_scripts","endpoint_or_artifact":"chrome_extension_content_scripts table","classification":"enrichment_only","entity_types":["device"],"gating_logic":"table present","citation_refs":"【80†L89-L100】","notes":"Multi-OS."}
  ],
  "signal_contracts": [
    {"module":"os_security","source":"os_security","provider":"osquery","provider_method":"disk_encryption","signal_type":"disk_encryption_disabled","category":"device_security","severity":"high","severity_is_conditional":"no","conditional_rule":"","entity_type":"device","finding_kind":"true_finding","trigger_condition":"encryption_status != \"encrypted\" OR encrypted = 0","evidence_fields":["name","uuid","encryption_status","filevault_status"],"enrichment_fields":["type","encryption_method","percentage_encrypted"],"summary_template":"Disk **{name}** is **unencrypted**","evidence_status":"documented","citation_refs":"【13†L319-L327】","notes":""},
    {"module":"os_security","source":"os_security","provider":"osquery","provider_method":"bitlocker_info","signal_type":"disk_encryption_disabled","category":"device_security","severity":"high","severity_is_conditional":"no","conditional_rule":"","entity_type":"device","finding_kind":"true_finding","trigger_condition":"percentage_encrypted < 100 OR protection_status = 0","evidence_fields":["device_id","drive_letter","percentage_encrypted","protection_status"],"enrichment_fields":["encryption_method","conversion_status","version"],"summary_template":"BitLocker on drive {drive_letter} is **not fully encrypted**","evidence_status":"documented","citation_refs":"【1†L8-L13】","notes":""},
    {"module":"os_security","source":"os_security","provider":"osquery","provider_method":"alf","signal_type":"firewall_disabled","category":"device_security","severity":"high","severity_is_conditional":"no","conditional_rule":"","entity_type":"device","finding_kind":"true_finding","trigger_condition":"global_state = 0","evidence_fields":["global_state","logging_enabled","stealth_enabled"],"enrichment_fields":["allow_signed_enabled","logging_option","version"],"summary_template":"macOS Application Layer Firewall is **off**","evidence_status":"documented","citation_refs":"【21†L95-L101】","notes":""},
    {"module":"os_security","source":"os_security","provider":"osquery","provider_method":"screenlock","signal_type":"screenlock_disabled","category":"device_security","severity":"medium","severity_is_conditional":"no","conditional_rule":"","entity_type":"device","finding_kind":"true_finding","trigger_condition":"enabled = 0","evidence_fields":["enabled","grace_period"],"enrichment_fields":[],"summary_template":"Screen lock is **disabled** (no password on wake)","evidence_status":"documented","citation_refs":"【36†L277-L284】","notes":""},
    {"module":"os_security","source":"osquery_agent","provider":"osquery","provider_method":"sip_config","signal_type":"sip_disabled","category":"device_security","severity":"high","severity_is_conditional":"no","conditional_rule":"","entity_type":"device","finding_kind":"true_finding","trigger_condition":"config_flag = 'sip' AND enabled = 0","evidence_fields":["config_flag","enabled","enabled_nvram"],"enrichment_fields":[],"summary_template":"System Integrity Protection (**SIP**) is **disabled**","evidence_status":"documented","citation_refs":"【38†L93-L96】","notes":""},
    {"module":"os_security","source":"osquery_agent","provider":"osquery","provider_method":"gatekeeper","signal_type":"gatekeeper_disabled","category":"device_security","severity":"high","severity_is_conditional":"no","conditional_rule":"","entity_type":"device","finding_kind":"true_finding","trigger_condition":"assessments_enabled = 0","evidence_fields":["assessments_enabled","dev_id_enabled"],"enrichment_fields":[],"summary_template":"Gatekeeper is **disabled** (allows all apps)","evidence_status":"documented","citation_refs":"【42†L285-L293】","notes":""},
    {"module":"os_security","source":"osquery_agent","provider":"osquery","provider_method":"secureboot","signal_type":"secure_boot_disabled","category":"device_security","severity":"high","severity_is_conditional":"no","conditional_rule":"","entity_type":"device","finding_kind":"true_finding","trigger_condition":"secure_boot = 0","evidence_fields":["secure_boot","setup_mode"],"enrichment_fields":[],"summary_template":"Secure Boot is **disabled**","evidence_status":"documented","citation_refs":"【44†L103-L110】","notes":""},
    {"module":"patch_status","source":"zima_patch_module","provider":"osquery","provider_method":"os_version","signal_type":"os_out_of_date","category":"device_security","severity":"high","severity_is_conditional":"yes","conditional_rule":"If OS major version < latest major OR patch lag > X months","entity_type":"device","finding_kind":"true_finding","trigger_condition":"<OS vs known latest (external)>","evidence_fields":["name","version","build"],"enrichment_fields":["major","minor","codename"],"summary_template":"OS **{name}** is outdated (current: {version})","evidence_status":"documented","citation_refs":"【19†L321-L330】","notes":""}
  ],
  "confidence_guidance": [
    {"module":"os_security","signal_type_or_use_case":"disk_encryption_disabled","source_reliability":"High (OS-reported)","freshness_considerations":"Reflects current encryption status; changes on reformat or enable BitLocker/FileVault","corroboration_rules":"Verify with BitLocker CLI or FileVault status commands","calibration_todo":"Confirm all `encryption_status` values map correctly to risk"},
    {"module":"os_security","signal_type_or_use_case":"firewall_disabled","source_reliability":"Medium (OS firewall state)","freshness_considerations":"Changes when firewall config changes; periodic check needed","corroboration_rules":"Cross-check with OS firewall service status","calibration_todo":"Refine Linux rule/policy logic"},
    {"module":"os_security","signal_type_or_use_case":"screenlock_disabled","source_reliability":"Medium","freshness_considerations":"User can enable/disable anytime; schedule checks","corroboration_rules":"Confirm via policy or UI setting","calibration_todo":"Assess severity vs policy standards"},
    {"module":"os_security","signal_type_or_use_case":"sip_disabled","source_reliability":"High","freshness_considerations":"Static until admin toggles; low update frequency","corroboration_rules":"Should correlate with `gatekeeper` being off","calibration_todo":""},
    {"module":"os_security","signal_type_or_use_case":"gatekeeper_disabled","source_reliability":"High","freshness_considerations":"As above, static","corroboration_rules":"Cross-check SIP; known pattern if gatekeeper off, SIP often off","calibration_todo":""},
    {"module":"os_security","signal_type_or_use_case":"secure_boot_disabled","source_reliability":"High","freshness_considerations":"Firmware setting, static per boot","corroboration_rules":"Check `setup_mode` should be 1 if secure boot disabled","calibration_todo":""},
    {"module":"patch_status","signal_type_or_use_case":"os_out_of_date","source_reliability":"High","freshness_considerations":"Must compare to known current version; stale if not updated","corroboration_rules":"Integrate vendor OS update APIs","calibration_todo":"Set precise lag thresholds"},
    {"module":"software_vulnerability","signal_type_or_use_case":"package_inventory","source_reliability":"High","freshness_considerations":"Inventory stale until re-run; update schedule needed","corroboration_rules":"Use with CVE databases","calibration_todo":"Ensure parsing correct for all package managers"},
    {"module":"extension_risk","signal_type_or_use_case":"extension_inventory","source_reliability":"High","freshness_considerations":"User can add/remove extensions at any time","corroboration_rules":"Check known malicious ID lists","calibration_todo":"Catalog popular `optional_permissions` usage"}
  ]
}
