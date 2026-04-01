---
title: "output / tools / windows_native"
aliases: ["windows_native output", "windows_native signal registry"]
tags: [zima, research, outputs, signal-registry, tools, windows_native, graph_exclude]
type: provider_research_output
provider: windows_native
provider_category: tools
status: not_started
prompt_note: prompt.md
provider_folder: windows_native.md
obsidianUIMode: preview
---


# windows_native provider research for Zima module implementation

## Tool Surface Appendix

### Get-BitLockerVolume for encryption state

**What it is**
`Get-BitLockerVolume` is a PowerShell cmdlet (BitLocker module) that returns a `BitLockerVolume` object representing volumes that BitLocker Drive Encryption can protect, including key properties such as volume type, mount point, encryption status, and protection status. 

**Exact invocation (local)**

- All volumes:
    - `Get-BitLockerVolume` 
- Specific volume:
    - `Get-BitLockerVolume -MountPoint "C:"` 
- “Full object” view (useful for mapping):
    - `Get-BitLockerVolume -MountPoint C | Format-List` 

**Primary output properties and types (as exposed by the cmdlet)**
The cmdlet documentation and examples explicitly show the following properties in the returned object (or its default view): 

- `MountPoint` (string; e.g., `C:`) 
- `VolumeType` (string; documented as “Data” or “Operating System” in the help text and shown in output) 
- `VolumeStatus` (string; example values shown include `FullyEncrypted`, `FullyDecrypted`, `EncryptionInProgress`) 
- `ProtectionStatus` (string; example values shown include `On` / `Off`) 
- `EncryptionPercentage` (number/integer as rendered; example shows `100` and `0`) 
- (Often useful for evidence) `EncryptionMethod` (string; e.g., `XtsAes128`) 
- (Often useful for evidence) `KeyProtector` (collection; shown with values like `{RecoveryPassword, Tpm}`) 

**Enum/value constraints (documented vs observed)**

- `ProtectionStatus`: observed values `On` and `Off` in the official examples. 
- `VolumeStatus`: observed values `FullyEncrypted`, `FullyDecrypted`, `EncryptionInProgress` in the official examples. 
- The prompt’s additional `DecryptionInProgress` value is **not** shown in the cmdlet documentation excerpt retrieved here; treat additional values as **unknown until observed in real output** (mapper should be tolerant to unexpected strings). 

**Admin/elevation requirements**

- Microsoft documentation is explicit that **to turn on, turn off, or change configurations of BitLocker** on OS and fixed data drives, membership in the local Administrators group is required. 
- The cmdlet documentation does not explicitly state “must be elevated to query status”, but operational guidance frames status checks as an administrative activity and BitLocker management is generally privilege-sensitive. For Zima, treat BitLocker posture checks as **“requires elevation for reliable access”** and implement graceful fallback (see “Implementation Notes”). 

**Windows compatibility notes**

- On Windows Server, BitLocker is **not installed by default** and must be installed (requires admin privileges). 
- For Windows client editions (Home vs Pro/Enterprise), the cmdlet reference we used does not enumerate edition availability. Because environment support varies, Zima should detect capability at runtime via `Get-Command Get-BitLockerVolume` and/or module import failure instead of assuming edition. 

**Error conditions / edge cases**

- Cmdlet not found / module missing: likely when BitLocker tooling is absent or not installed (notably on some systems; Windows Server requires feature installation). 
- Volumes with `ProtectionStatus = Off` while a `KeyProtector` exists (example shows `KeyProtector` values even when `ProtectionStatus` is `Off`); for signal logic, prioritise `ProtectionStatus` and `VolumeStatus` over the presence of a protector list. 
- Multiple volumes returned; Zima must decide whether to emit per-volume findings or a single aggregated host finding. The provider returns one object per volume. 

**Performance considerations**

- Query is typically fast compared to MSI/WMI inventory; still, prefer selecting only needed properties before serialisation to JSON to reduce payload size. (PowerShell objects serialise to JSON fields; methods are removed.) 

---

### Get-NetFirewallProfile for firewall configuration by profile

**What it is**
`Get-NetFirewallProfile` is a NetSecurity module cmdlet that displays per-profile Windows Firewall with Advanced Security configuration for Domain, Private, and Public profiles. 

**Exact invocation (local)**

- All profiles (common):
    - `Get-NetFirewallProfile` (defaults vary by policy store; cmdlet supports an `-All` switch) 
- Explicit:
    - `Get-NetFirewallProfile -All` 
- Specific profile:
    - `Get-NetFirewallProfile -Name Public` 
- If you want the active effective policy:
    - `Get-NetFirewallProfile -PolicyStore ActiveStore` 

**Output object schema (authoritative backing class)**
The underlying WMI provider class `MSFT_NetFirewallProfile` (namespace `Root\StandardCimv2`) defines the core fields Zima cares about: 

- `Name` (string) 
- `Enabled` (uint16) 
- `DefaultInboundAction` (uint16) 
- `DefaultOutboundAction` (uint16) 

**Important nuance for mapping**

- Many PowerShell views present `Enabled` as `True/False` and default actions as `Block/Allow`, but the WMI definition is `uint16`. Zima should therefore treat the cmdlet output as “either already-normalised (bool/string) or raw numeric” and implement a robust mapper that accepts both representations. 
- Official firewall command-line examples show `Set-NetFirewallProfile` uses `-Enabled True/False` and default action parameters with values like `Block` and `Allow`, establishing the semantic intent of those fields. 

**Admin/elevation requirements**

- Not explicitly stated as required for read-only profile retrieval in the cmdlet reference. Treat as **typically non-elevated readable**, but do not assume (harden against access denied). 

**Windows compatibility notes**

- The backing class lists minimum supported client as Windows 8 and minimum supported server as Windows Server 2012. 
- Microsoft’s firewall command-line guidance applies to Windows 10/11 and Windows Server 2016+ and expects three profiles (Domain/Private/Public). 

**Error conditions / edge cases**

- Multiple profiles “may be in effect” on interfaces; Zima should still evaluate state for each profile object independently (Domain/Private/Public). 
- Policy store variations (ActiveStore vs PersistentStore) can change interpretation of “effective” state; for posture, ActiveStore is typically the right target. 

**Performance considerations**

- Fast, local query. Prefer selecting minimal properties for JSON serialisation (Name/Enabled/DefaultInboundAction/DefaultOutboundAction + optional logging fields if you want). 

---

### Get-MpComputerStatus for Microsoft Defender Antivirus status

**What it is**
`Get-MpComputerStatus` is a Defender module cmdlet that returns the status of antimalware software installed on the computer. 

**Exact invocation**

- Local:
    - `Get-MpComputerStatus` 

**Output properties relevant to Zima posture**
The official example output includes (among many others) the specific properties you listed, with the following semantics: 

- `RealTimeProtectionEnabled` (boolean in output) 
- `AntivirusEnabled` (boolean) 
- `AntispywareEnabled` (boolean) 
- `AntivirusSignatureLastUpdated` (datetime string) 
- `AntivirusSignatureAge` (number of days; shown as integer) 
- `QuickScanAge`, `FullScanAge` (integers; example shows `4294967295` for `FullScanAge`, which should be treated as a sentinel/edge case rather than a normal “days” value) 
- Additional fields likely valuable as evidence: `AMServiceEnabled`, engine/product versions, and signature versions. 

**Admin/elevation requirements**

- Microsoft’s Defender guidance for using these cmdlets states “open PowerShell as an administrator” to use the cmdlets. 
- In practice, some fields are readable non-elevated, but Zima should treat the posture collector as “best effort elevated” with fallback behaviour (see “Implementation Notes”). 

**Windows compatibility notes**

- If Microsoft Defender Antivirus is not present/active (for example, replaced by third‑party AV), the Defender module/cmdlet may be unavailable; handle this as “check not applicable/unknown” rather than “Defender disabled”. (This is not fully specified in the cmdlet reference; treat as an operational edge case.) 

**Performance considerations**

- Local query is fast. Keep output minimal to reduce serialisation overhead. 

---

### Get-CimInstance Win32_OperatingSystem for OS identification and build

**What it is**
`Get-CimInstance` is the modern/supported PowerShell cmdlet to query CIM/WMI instances; `Get-WmiObject` is explicitly “superseded by Get-CimInstance” starting in PowerShell 3.0. 
`Win32_OperatingSystem` is the WMI class representing the Windows-based OS installed on a computer. 

**Exact invocation**

- Minimal, local:
    - `Get-CimInstance -ClassName Win32_OperatingSystem` 
- Property-focused (recommended for Zima mapping):
    - `Get-CimInstance -ClassName Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, LastBootUpTime, OSArchitecture` 

**Output properties (from the Win32_OperatingSystem class)**
The class documentation defines available properties; for Zima’s requested subset: 

- `Caption` (string; human-readable OS name) 
- `Version` (string; OS version string) 
- `BuildNumber` (string; build number) 
- `LastBootUpTime` (datetime) 
- `OSArchitecture` (string; architecture) 

**Mapping Version/BuildNumber to Windows marketing names (Windows 10 vs Windows 11)**

- Microsoft documentation for Configuration Manager explicitly notes that Windows 11 reports OS properties as `10.0` (identical to Windows 10) and recommends distinguishing Windows 11 by **Operating System Build** `10.0.22000` or later. 
- Microsoft “release information” pages list major-version feature releases and their base OS build numbers (for example, Windows 11 version 23H2 is OS build 22631). 

**Implementation-grade approach for Zima mapping**

1. Prefer `Caption` when it explicitly includes “Windows 11” / “Windows 10” (string match). 
2. If `Caption` is ambiguous, use `BuildNumber` thresholding per Microsoft guidance:
    - if `BuildNumber >= 22000`, treat as Windows 11 family; else Windows 10 family. 
3. For “feature version line” mapping (e.g., 23H2/24H2/25H2), treat base build numbers as a coarse indicator but note that `BuildNumber` lacks the full “minor build” shown in update history (e.g., 22631.6060). Use OS release health sources as lookup, not hard-coded constants. 

**Admin/elevation requirements**

- Local WMI queries usually work non-elevated, but remote CIM/WMI access can require admin membership on the remote endpoint; Microsoft’s WMI/CIM guidance explicitly notes that for remote CIM cmdlets, the account must be in the local Administrators group on the remote computer. 

---

### Get-HotFix and Win32_QuickFixEngineering for installed hotfixes

**What it is**
`Get-HotFix` returns hotfixes installed on local or remote computers, and explicitly uses the `Win32_QuickFixEngineering` WMI class. 

**Exact invocation**

- Local list:
    - `Get-HotFix` 
- Most recent hotfix (example from docs):
    - `(Get-HotFix | Sort-Object -Property InstalledOn)[-1]` 
- Alternative (same backend):
    - `Get-CimInstance -ClassName Win32_QuickFixEngineering` (since `Get-HotFix` uses that class) 

**Output properties (documented in Get-HotFix examples)**
The official example table includes: 

- `HotFixID` (string; looks like `KB#######`) 
- `InstalledOn` (datetime) 
- `Description` (string; e.g., “Security Update”) 
- `InstalledBy` (string; e.g., `NT AUTHORITY\SYSTEM`) 
- `Source` (string; computer name in example output) 

**Limitations (important for module design)**

- The provider source of truth is the WMI `Win32_QuickFixEngineering` class. In practice and per Microsoft guidance, QuickFixEngineering is a “hotfix” oriented view and does not represent every update category (for example, application updates). In Zima, treat `Get-HotFix` as “OS hotfix inventory”, not a full Windows Update compliance feed. 

**Remote behaviour / permissions**

- `Get-HotFix` includes `-ComputerName` and “doesn’t rely on Windows PowerShell remoting” per the docs. This matters for fleet collection methods. 

---

### Registry UAC settings under HKLM policies

**What it is**
Microsoft documents that UAC-related registry keys live under: `HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System`. 
Your prompt targets:

- `EnableLUA`
- `ConsentPromptBehaviorAdmin`
- `ConsentPromptBehaviorUser`

**Exact PowerShell invocation**

- Read all relevant values in one call:
    - `Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name EnableLUA,ConsentPromptBehaviorAdmin,ConsentPromptBehaviorUser` 

**Key/value definitions (authoritative)**

- `ConsentPromptBehaviorAdmin` (REG_DWORD) value meanings are standardised in Microsoft’s Group Policy Security Baseline open specification (MS-GPSB). 
- `ConsentPromptBehaviorUser` (REG_DWORD) is also standardised in MS-GPSB. 
- Microsoft’s UAC settings documentation also provides a registry mapping table and confirms these keys/paths. 

**Enum/value constraints (documented)**

- `ConsentPromptBehaviorAdmin` values 0–5 with defined semantics. 
- `ConsentPromptBehaviorUser` values 0–1 with defined semantics. 
- `EnableLUA` is defined in MS-GPSB as a registry value under the same key path; (use MS-GPSB `EnableLUA` for authoritative definition). 

**Admin/elevation requirements**

- Reading HKLM generally works non-elevated for most keys, but environments may harden registry access. Treat failures as “unknown”. 

---

### Get-Package and registry uninstall enumeration for installed software inventory

**Why this matters for Zima**
Software inventory is a **utility output** feeding the `software_vulnerability` module. It should not, by itself, be treated as a standalone signal unless the module correlates it to known risk conditions.

**Do not use Win32_Product**

- `Win32_Product` is explicitly a Windows Installer (MSI)–scoped inventory class (“provided the software was installed by using Windows Installer”). 
- Microsoft guidance warns against using `Win32_Product` in certain inventory contexts; it is widely treated as slow/risky for fleet inventory. The Microsoft Tech Community article “How to NOT Use Win32_Product in Group Policy Filtering” is the closest Microsoft-authored warning source retrieved here. 

**Get-Package (PackageManagement)**

- `Get-Package` returns packages installed with PackageManagement and includes columns `Name`, `Version`, `Source`, and `ProviderName` in its examples. 
- PackageManagement is documented as a unified interface for software discovery/installation/inventory tasks. 

**Exact invocation**

- `Get-Package` 
- Restrict to a provider:
    - `Get-Package -ProviderName PowerShellGet -AllVersions` (example pattern) 
- Enumerate providers to understand coverage:
    - `Get-PackageProvider -ListAvailable` 

**Key limitation**
Because `Get-Package` is scoped to PackageManagement-installed packages, it is **not guaranteed to return all installed desktop applications**. This is explicit in the cmdlet description. 

**Registry uninstall enumeration (recommended for broad “ARP-style” inventory)**

- Microsoft’s PowerShell guidance for “Working with software installations” recommends querying the Uninstall registry key and explicitly notes there is **no guaranteed way** to find every application, but it is possible to find programs listed in Add/Remove Programs under `HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Uninstall`. 
- Windows Installer documentation describes values written under that Uninstall key, including `DisplayName` and `DisplayVersion`. 

**Exact PowerShell invocation (registry approach)**

- 64-bit uninstall:
    - `Get-ItemProperty "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*" | Select-Object DisplayName, DisplayVersion, Publisher, InstallDate` 
- (Common additional surface) 32-bit uninstall on 64-bit OS (Wow6432Node) is not explicitly documented in the core MSI Uninstall key article, but is operationally common; if you implement it, label as “inferred” and test.

---

### Get-WindowsOptionalFeature -Online for optional features inventory

**What it is**
`Get-WindowsOptionalFeature` is part of DISM PowerShell tooling, used to query Windows optional features (online/offline images). 

**Exact invocation**

- Online OS:
    - `Get-WindowsOptionalFeature -Online` 

**Output properties of interest**
Your target fields are consistent with DISM tooling output conventions; the cmdlet is documented to expose optional features and their states. For Zima, treat these as:

- `FeatureName` (string)
- `State` (string; e.g., Enabled/Disabled) 

**Admin/elevation and compatibility**
The retrieved references here do not explicitly state elevation requirements for the query operation; treat as **unclear** and implement “best effort” execution with fallback to “unknown” if blocked. 

---

## Module Mapping Table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|disk_encryption_check|direct_signal_input|Get-BitLockerVolume|PowerShell cmdlet `Get-BitLockerVolume` returning `BitLockerVolume` objects|direct_signal_input|hostname|If `Get-Command Get-BitLockerVolume` fails OR cmdlet errors, treat as “unsupported/unknown” and do not emit encryption findings. If succeeds, evaluate per returned volume object.||Use `ProtectionStatus` and `VolumeStatus` as primary truth. Multiple volumes returned.|
|firewall_status|direct_signal_input|Get-NetFirewallProfile|PowerShell cmdlet `Get-NetFirewallProfile` (NetSecurity) / backing WMI class `MSFT_NetFirewallProfile`|direct_signal_input|hostname|Query ActiveStore when possible; evaluate Domain/Private/Public separately; if any profile retrieval fails, mark unknown and avoid partial false “disabled” unless you have explicit results.||Backing class fields are uint16; cmdlet output may normalise to bool/string—mapper must accept both.|
|os_security|direct_signal_input|Get-MpComputerStatus|PowerShell cmdlet `Get-MpComputerStatus` returning Defender status|direct_signal_input|hostname|If cmdlet/module unavailable, do not emit “Defender disabled” (could be third-party AV); treat as “not applicable/unknown for this provider”. If available, evaluate key protection booleans and signature staleness.||Consider running elevated for consistent access per Microsoft guidance.|
|os_security|direct_signal_input|Registry read (UAC)|`HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System` values `EnableLUA`, `ConsentPromptBehaviorAdmin`, `ConsentPromptBehaviorUser`|direct_signal_input|hostname|If registry path unreadable, treat as unknown. If `EnableLUA = 0`, emit UAC-disabled finding. Optionally interpret prompt behaviour values for weaker-than-baseline configuration.||Values are REG_DWORD enums per MS-GPSB; persist numeric + interpreted label in evidence.|
|patch_status|direct_signal_input|Get-CimInstance Win32_OperatingSystem|WMI/CIM class `Win32_OperatingSystem` via `Get-CimInstance`|direct_signal_input|hostname|Always collect. Use `Caption` + `BuildNumber` to classify OS family; for Windows 11 vs 10, use build threshold guidance.||`BuildNumber` is coarse; do not treat it as patch-level compliance.|
|patch_status|direct_signal_input|Get-HotFix|PowerShell cmdlet `Get-HotFix` (Win32_QuickFixEngineering)|direct_signal_input|hostname|Use to compute “last hotfix date” and capture installed KB IDs; do not claim comprehensive update compliance from this surface alone.||`Get-HotFix` uses WMI and doesn’t rely on PS remoting for `-ComputerName`.|
|software_vulnerability|utility_only|Get-Package|PackageManagement cmdlet `Get-Package`|utility_only|hostname|Use as one inventory input only; do not emit vulnerability findings without an external vulnerability mapping step.||`Get-Package` only lists packages installed with PackageManagement.|
|software_vulnerability|utility_only|Registry uninstall enumeration|`HKLM\...\Uninstall\*` (`DisplayName`, `DisplayVersion`, etc.)|utility_only|hostname|Enumerate uninstall keys and normalise name/version for matching; treat as “best effort” inventory, not perfect ground truth.||This is the preferred broad inventory surface in Microsoft’s own PowerShell guidance.|

## Signal Contract Table

Only rows below are recommended as **standalone signals** emitted by target modules from windows_native posture outputs. Inventory-only outputs (e.g., software lists) are intentionally excluded.

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|disk_encryption_check|disk_encryption_check|windows_native|Get-BitLockerVolume|disk_encryption_disabled|endpoint_security|high|yes|Escalate to high specifically when `VolumeType` is `OperatingSystem`; keep high by default per your calibration if any protected volume is unprotected.|hostname|true_finding|For any returned volume object: `ProtectionStatus -eq "Off" OR VolumeStatus -eq "FullyDecrypted"`|`MountPoint`, `VolumeType`, `VolumeStatus`, `ProtectionStatus`, `EncryptionPercentage`, `EncryptionMethod`, `KeyProtector`|`CapacityGB`, `MetadataVersion`, `LockStatus` (if present)|`Disk encryption is not enabled or not protecting volume {MountPoint} ({VolumeType}).`|documented (fields) / inferred (policy meaning)||The cmdlet examples show `ProtectionStatus` On/Off and `VolumeStatus` including `FullyDecrypted`.|
|disk_encryption_check|disk_encryption_check|windows_native|Get-BitLockerVolume|disk_encryption_in_progress|endpoint_security|medium|no|n/a|hostname|true_finding|For any returned volume object: `VolumeStatus -eq "EncryptionInProgress" OR EncryptionPercentage -lt 100`|`MountPoint`, `VolumeType`, `VolumeStatus`, `EncryptionPercentage`, `ProtectionStatus`|`EncryptionMethod`, `KeyProtector`|`Disk encryption is in progress on volume {MountPoint} ({EncryptionPercentage}%).`|inferred from examples only||The `EncryptionInProgress` value appears in official example output; treat other in-progress strings as unknown until observed.|
|firewall_status|firewall_status|windows_native|Get-NetFirewallProfile|windows_firewall_profile_disabled|network_security|high|yes|High if any of Domain/Private/Public is disabled; include which profile(s) in evidence.|hostname|true_finding|For any profile object: `Enabled == False` (or underlying `Enabled` uint16 indicates disabled)|`Name`, `Enabled`, `DefaultInboundAction`, `DefaultOutboundAction`|`PolicyStore` (if queried), logging fields if captured (`LogFileName`, `LogAllowed`, `LogBlocked`)|`Windows Firewall profile {Name} is disabled.`|documented||Schema is authoritative from `MSFT_NetFirewallProfile`. Values may be uint16 or normalised.|
|firewall_status|firewall_status|windows_native|Get-NetFirewallProfile|windows_firewall_default_inbound_not_blocking|network_security|medium|yes|If inbound default is not “Block” for Public profile, treat as higher concern than for Domain/Private.|hostname|true_finding|For any profile object: `DefaultInboundAction != Block` (normalised) OR underlying value not equal to “block” semantic|`Name`, `DefaultInboundAction`, `DefaultOutboundAction`, `Enabled`|`AllowInboundRules`, `AllowLocalFirewallRules`, `AllowLocalIPsecRules`|`Windows Firewall profile {Name} is not configured to block inbound traffic by default.`|derived||Parameter docs and official firewall guidance define `Block/Allow` semantics; output normalisation is environment-dependent.|
|os_security|os_security|windows_native|Get-MpComputerStatus|defender_real_time_protection_disabled|endpoint_security|high|no|n/a|hostname|true_finding|`RealTimeProtectionEnabled -eq False`|`RealTimeProtectionEnabled`, `AntivirusEnabled`, `AntispywareEnabled`, `AMServiceEnabled`, `AMProductVersion`, `AMEngineVersion`|`ComputerState`, `AMRunningMode`|`Microsoft Defender real-time protection is disabled.`|documented||Microsoft guidance instructs using PowerShell (admin) to evaluate Defender status.|
|os_security|os_security|windows_native|Get-MpComputerStatus|defender_antivirus_disabled|endpoint_security|high|yes|If `AntivirusEnabled = False` but cmdlet works, treat as high; if cmdlet missing/unavailable, treat as unknown (do not emit).|hostname|true_finding|`AntivirusEnabled -eq False OR AMServiceEnabled -eq False`|`AntivirusEnabled`, `AMServiceEnabled`, `RealTimeProtectionEnabled`, signature versions/last updated fields|`AntispywareEnabled`, scan age fields|`Microsoft Defender Antivirus is not enabled or the service is not running.`|documented (fields) / derived (interpretation)||Keep a strict gate: only emit if you successfully retrieved `Get-MpComputerStatus`.|
|os_security|os_security|windows_native|Get-MpComputerStatus|defender_signatures_stale|endpoint_security|medium|yes|Escalate toward high if `AntivirusSignatureAge` exceeds a configured max-age by a large margin (calibration).|hostname|true_finding|`AntivirusSignatureAge -gt {max_signature_age_days}`|`AntivirusSignatureAge`, `AntivirusSignatureLastUpdated`, `AntivirusSignatureVersion`|engine/product versions|`Microsoft Defender signatures are out of date (age: {AntivirusSignatureAge} days).`|derived||Threshold must be configurable; the cmdlet provides `AntivirusSignatureAge` and `...LastUpdated`.|
|os_security|os_security|windows_native|Registry UAC keys|uac_disabled|endpoint_security|medium|no|n/a|hostname|true_finding|`EnableLUA -eq 0`|`EnableLUA`, `ConsentPromptBehaviorAdmin`, `ConsentPromptBehaviorUser`|other UAC-related keys if captured|`User Account Control (UAC) is disabled (EnableLUA=0).`|documented||Registry path and key are documented; value mapping for other prompt keys is also standardised.|
|os_security|os_security|windows_native|Registry UAC keys|uac_admin_elevation_without_prompting|endpoint_security|medium|no|n/a|hostname|true_finding|`ConsentPromptBehaviorAdmin -eq 0x00000000`|`ConsentPromptBehaviorAdmin`, `EnableLUA`|`PromptOnSecureDesktop` (if later included)|`UAC elevation for administrators is configured as “elevate without prompting”.`|documented||MS-GPSB defines `ConsentPromptBehaviorAdmin=0` as “elevate without prompting.”|
|patch_status|patch_status|windows_native|Win32_OperatingSystem|os_out_of_support|endpoint_security|high|yes|High when OS family/version is out of support; your rule source must be updated as Microsoft servicing milestones change.|hostname|true_finding|If OS is Windows 10 (by caption/build mapping) **and** current date is after Windows 10 end of support (2025-10-14), emit.|`Caption`, `Version`, `BuildNumber`, `OSArchitecture`|`LastBootUpTime`|`Operating system is out of support: {Caption} (build {BuildNumber}).`|derived||Windows 10 end of support is explicitly stated in Microsoft release information.|
|patch_status|patch_status|windows_native|Get-HotFix|os_hotfix_stale|endpoint_security|medium|yes|Escalate if last hotfix is older than a configurable window (e.g., 60–90 days) on internet-connected endpoints; keep medium where update cadence is managed separately.|hostname|true_finding|Let `last_hotfix = max(InstalledOn)`; trigger if `now - last_hotfix > {max_hotfix_age_days}`|`HotFixID`, `InstalledOn`, `Description`, `InstalledBy` (for the most recent hotfix) plus `last_hotfix` computed|full hotfix list (optional)|`Latest installed OS hotfix is stale (last installed on {last_hotfix}).`|derived||`Get-HotFix` is a QuickFixEngineering view; use as a “staleness heuristic”, not compliance proof.|

## Confidence Guidance

|module|signal_type_or_use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|disk_encryption_check|disk_encryption_disabled / in_progress|High reliability for local BitLocker state when cmdlet is available; fields are direct OS instrumentation.|State can change during encryption/decryption; treat “in progress” as transient and consider re-check timing.|Corroborate with `manage-bde.exe -status` where available for troubleshooting (BitLocker ops guide lists it as a status tool).|Decide volume scoping (OS-only vs all). Decide how to handle systems where BitLocker tooling is absent (detect vs assume).|
|firewall_status|windows_firewall_profile_disabled / default inbound not blocking|High reliability if you treat `MSFT_NetFirewallProfile` as source-of-truth and collect from ActiveStore.|Policy changes can be pushed via GPO/MDM; prefer ActiveStore querying to represent effective state “now”.|Corroborate by checking the same state via `Set-NetFirewallProfile` semantics for Block/Allow (for interpretation) and/or netsh for troubleshooting.|Define mapping for uint16 enums to bool/string across environments; add telemetry for “unexpected numeric”.|
|os_security|defender_* signals|Medium-to-high when cmdlet is available; fields are direct Defender telemetry.|Signature age is inherently time-based; rely on `AntivirusSignatureAge` and `...LastUpdated`.|Corroborate with Defender UI/operational logs where available; avoid treating “cmdlet missing” as “Defender off” (third-party AV case).|Choose default `{max_signature_age_days}` per environment and tune from fleet distributions; handle sentinel scan ages like `4294967295`.|
|os_security|uac_* signals|High reliability; keys and enums are standardised in Microsoft docs/spec.|Changes require policy refresh and may require reboot for full effect; treat as configuration state, not event.|Corroborate with local security policy/GPO baselines where present; keep evidence of raw DWORD values.|Decide which UAC “weaker settings” warrant signals vs enrichment (e.g., admin prompt level). Keep severity aligned to your guide.|
|patch_status|os_out_of_support|High reliability when driven from Microsoft servicing milestone sources; must be kept current.|Servicing policies change (new Windows 11 releases); maintain periodic refresh of mapping data from Microsoft release health.|Corroborate with enterprise lifecycle policy (LTSC/IoT/ESU distinctions) before enforcement decisions.|Build an internal “servicing lookup” table keyed by OS family/build; add LTSC handling.|
|patch_status|os_hotfix_stale heuristic|Medium reliability: it is a heuristic that depends on QuickFixEngineering coverage.|“InstalledOn” may not reflect all update channels; treat as weak signal without corroboration.|Corroborate with Windows Update compliance sources (outside this provider scope) where possible.|Pick `{max_hotfix_age_days}` based on fleet cadence; consider suppressions for offline/air-gapped or maintenance windows.|
|software_vulnerability|inventory feeding correlation|Medium reliability: registry uninstall is best-effort; PackageManagement is incomplete by definition.|Versions change frequently; inventory should be timestamped and refreshed; do not cache too long without re-collection.|Corroborate package identity using multiple fields (DisplayName, Publisher, install location when available) to avoid false matches.|Normalise name/version strings; define match strategies and confidence scoring downstream (outside provider scope).|

## Implementation Notes

### Privilege and elevation strategy

- Several posture surfaces are “administrative by nature” even when reads may sometimes succeed without elevation (BitLocker management and Defender evaluation guidance explicitly call for admin PowerShell). 
- Zima should support **dual-mode collection**:
    - **Elevated mode** (preferred): maximises access and consistency for BitLocker/Defender and registry-based checks. 
    - **Non-elevated mode** (fallback): run what you can; if key cmdlets/keys fail, treat results as unknown and do not emit “disabled” findings unless you have explicit evidence fields indicating disabled.
- For remote CIM/WMI operations, Microsoft explicitly notes the account must be in local Administrators on the remote computer. 

### PowerShell execution policy handling

- PowerShell execution policy is a “safety feature” controlling script execution; it is configurable by scope and can be controlled by Group Policy. 
- For one-session overrides, Microsoft documentation notes that you can set an execution policy for a new session using the `ExecutionPolicy` parameter of `pwsh.exe`, affecting only that session and child sessions (stored in `$Env:PSExecutionPolicyPreference`, not persisted). 
- In Zima’s Windows-native collector model, using a per-process execution-policy override (rather than changing machine policy via `Set-ExecutionPolicy`) avoids requiring elevation for policy writes and avoids altering system configuration. `Set-ExecutionPolicy` default scope is `LocalMachine` and requires “Run as Administrator” to change LocalMachine. 

### Output parsing and serialization strategy

- PowerShell “accepts and returns .NET objects, rather than text,” which changes how Zima should collect data. 
- For a Python provider client, the most robust pattern is:
    1. Run PowerShell commands producing objects.
    2. Pipe to `Select-Object` for a stable schema.
    3. Convert to JSON via `ConvertTo-Json` with an explicit `-Depth` sufficient for nested properties. 
- `ConvertTo-Json` converts object properties to JSON fields and removes methods. 

### Field survival and null/empty behaviour

- Treat “empty result set” differently from “command failure”:
    - Empty set for inventory (e.g., `Get-Package`) is plausible and should not throw signals. 
    - Cmdlet missing (e.g., Defender/BitLocker tooling) should be represented as `unknown` capability; do not misclassify as disabled. 
- For Defender scan ages, values like `4294967295` appear in the official example output and should not be treated as literal “days”; preserve raw and interpret cautiously. 

### Deduplication and natural identifiers

- Disk encryption findings: dedup key should include `{hostname, mount_point, volume_type}` because output is per volume. 
- Firewall findings: dedup key should include `{hostname, profile_name}` because schema is per profile. 
- UAC findings: dedup key `{hostname, key_name}`; store raw DWORD in evidence for audit. 
- Hotfix staleness: dedup key `{hostname}` plus last hotfix ID/date. 

### Provider client vs mapper vs correlation

- Provider client (windows_native): should only execute local commands, capture raw objects, and serialise consistently. It should not decide severities or interpret servicing policy. 
- Module mapper (`modules/*/mapper.py`): should normalise field names and types (e.g., convert uint16 to boolean for firewall; parse/normalise dates; tolerate missing properties). 
- Module rules (`modules/*/rules.py`): should implement the trigger conditions in the signal table, using configuration thresholds for time-based checks (signature age, hotfix age) and treating external “servicing lookup tables” as data dependencies for `patch_status`. 

### Relationship to posture provider abstraction layer

windows_native should be treated as the **raw data plane** (OS-native interfaces: PowerShell, WMI/CIM, registry); any “posture provider” should sit above it as an abstraction that:

- chooses appropriate command surfaces by OS version/role,
- handles elevation orchestration,
- and deduplicates host-level posture snapshots before module rule evaluation. 

## Provider Summary

### Strongest signal types and utility contributions

- High-signal posture findings where the OS itself is the authority:
    - Disk encryption state via `Get-BitLockerVolume` (`ProtectionStatus`, `VolumeStatus`, `EncryptionPercentage`). 
    - Windows Firewall profile state via `Get-NetFirewallProfile` / `MSFT_NetFirewallProfile` (`Enabled`, default actions). 
    - Defender status via `Get-MpComputerStatus` (`RealTimeProtectionEnabled`, `AntivirusEnabled`, signature age). 
    - UAC configuration via registry keys standardised in Microsoft docs/specs. 

### What the provider should not be used for

- Full software inventory via `Win32_Product` (avoid; MSI-only and problematic for fleet inventory). 
- Full Windows Update compliance determination using only `Get-HotFix` / `Win32_QuickFixEngineering` (use as heuristic/inventory only). 

### Installation, privilege, and platform cautions

- Windows-only; relies on PowerShell/WMI registry. 
- BitLocker on Windows Server requires feature installation and admin privileges. 
- Defender cmdlets are intended to be run from elevated PowerShell in Microsoft guidance. 
- Remote CIM access can require admin membership on the remote endpoint. 

### How to treat this provider in Zima

Treat windows_native as **signal-producing for posture checks** (disk encryption, firewall, Defender, UAC, OS support posture) and **utility-only for inventory** (software lists, optional features) that require correlation to become findings.


{
  "provider": "windows_native",
  "provider_category": "tools",
  "provider_role": {
    "posture_checks": "direct_signal_input",
    "inventory": "utility_only"
  },
  "module_mappings": [
    {
      "module": "disk_encryption_check",
      "provider_method": "Get-BitLockerVolume",
      "endpoint_or_artifact": "PowerShell BitLocker module cmdlet",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "Require cmdlet availability (Get-Command). If unavailable or errors, set status unknown and emit no encryption findings.",
      "notes": "Evaluate per returned volume; prioritise ProtectionStatus/VolumeStatus."
    },
    {
      "module": "firewall_status",
      "provider_method": "Get-NetFirewallProfile",
      "endpoint_or_artifact": "PowerShell NetSecurity cmdlet / WMI MSFT_NetFirewallProfile",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "Query ActiveStore if possible; evaluate Domain/Private/Public. Handle uint16-vs-bool representation; if missing data, treat as unknown.",
      "notes": "Backed by Root\\StandardCimv2 MSFT_NetFirewallProfile."
    },
    {
      "module": "os_security",
      "provider_method": "Get-MpComputerStatus",
      "endpoint_or_artifact": "PowerShell Defender module cmdlet",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "If cmdlet unavailable, do not infer Defender disabled; treat as unknown/not-applicable for this provider.",
      "notes": "Signature-age staleness uses configurable thresholds."
    },
    {
      "module": "os_security",
      "provider_method": "registry_read_uac",
      "endpoint_or_artifact": "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "If keys unreadable, unknown. If EnableLUA=0 emit uac_disabled; optionally emit weaker-prompt findings from ConsentPromptBehavior*.",
      "notes": "Registry enums documented in MS-GPSB."
    },
    {
      "module": "patch_status",
      "provider_method": "Get-CimInstance Win32_OperatingSystem",
      "endpoint_or_artifact": "WMI/CIM Win32_OperatingSystem",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "Always collect. Determine Windows 10 vs 11 using Caption then BuildNumber threshold. Use external servicing tables for support status.",
      "notes": "BuildNumber is coarse; do not treat as patch-level."
    },
    {
      "module": "patch_status",
      "provider_method": "Get-HotFix",
      "endpoint_or_artifact": "Win32_QuickFixEngineering via Get-HotFix",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "Compute last_hotfix date; use as staleness heuristic only (configurable max_hotfix_age_days).",
      "notes": "Not comprehensive Windows Update coverage."
    },
    {
      "module": "software_vulnerability",
      "provider_method": "Get-Package",
      "endpoint_or_artifact": "PackageManagement Get-Package",
      "classification": "utility_only",
      "entity_types": ["hostname"],
      "gating_logic": "Do not emit vulnerability findings without correlation to vulnerability intelligence/mapping.",
      "notes": "Get-Package is incomplete by definition."
    },
    {
      "module": "software_vulnerability",
      "provider_method": "registry_uninstall_enumeration",
      "endpoint_or_artifact": "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",
      "classification": "utility_only",
      "entity_types": ["hostname"],
      "gating_logic": "Best-effort enumerate apps listed in Add/Remove Programs; normalise DisplayName/DisplayVersion for matching.",
      "notes": "Preferred broad-installed-software surface in Microsoft PowerShell guidance."
    }
  ],
  "signal_contracts": [
    {
      "module": "disk_encryption_check",
      "source": "disk_encryption_check",
      "provider": "windows_native",
      "provider_method": "Get-BitLockerVolume",
      "signal_type": "disk_encryption_disabled",
      "category": "endpoint_security",
      "severity": "high",
      "severity_is_conditional": "yes",
      "conditional_rule": "Escalate scope/priority when VolumeType is OperatingSystem.",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "ProtectionStatus == \"Off\" OR VolumeStatus == \"FullyDecrypted\"",
      "evidence_fields": ["MountPoint", "VolumeType", "VolumeStatus", "ProtectionStatus", "EncryptionPercentage", "EncryptionMethod", "KeyProtector"],
      "enrichment_fields": ["CapacityGB", "MetadataVersion", "LockStatus"],
      "summary_template": "Disk encryption is not enabled or not protecting volume {MountPoint} ({VolumeType}).",
      "evidence_status": "documented"
    },
    {
      "module": "firewall_status",
      "source": "firewall_status",
      "provider": "windows_native",
      "provider_method": "Get-NetFirewallProfile",
      "signal_type": "windows_firewall_profile_disabled",
      "category": "network_security",
      "severity": "high",
      "severity_is_conditional": "yes",
      "conditional_rule": "High if any of Domain/Private/Public profiles are disabled.",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "Enabled == False (or equivalent disabled value)",
      "evidence_fields": ["Name", "Enabled", "DefaultInboundAction", "DefaultOutboundAction"],
      "enrichment_fields": ["LogFileName", "LogAllowed", "LogBlocked"],
      "summary_template": "Windows Firewall profile {Name} is disabled.",
      "evidence_status": "documented"
    },
    {
      "module": "os_security",
      "source": "os_security",
      "provider": "windows_native",
      "provider_method": "Get-MpComputerStatus",
      "signal_type": "defender_real_time_protection_disabled",
      "category": "endpoint_security",
      "severity": "high",
      "severity_is_conditional": "no",
      "conditional_rule": "unknown",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "RealTimeProtectionEnabled == False",
      "evidence_fields": ["RealTimeProtectionEnabled", "AntivirusEnabled", "AntispywareEnabled", "AMServiceEnabled", "AntivirusSignatureAge", "AntivirusSignatureLastUpdated"],
      "enrichment_fields": ["AMProductVersion", "AMEngineVersion", "ComputerState"],
      "summary_template": "Microsoft Defender real-time protection is disabled.",
      "evidence_status": "documented"
    },
    {
      "module": "os_security",
      "source": "os_security",
      "provider": "windows_native",
      "provider_method": "registry_read_uac",
      "signal_type": "uac_disabled",
      "category": "endpoint_security",
      "severity": "medium",
      "severity_is_conditional": "no",
      "conditional_rule": "unknown",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "EnableLUA == 0",
      "evidence_fields": ["EnableLUA", "ConsentPromptBehaviorAdmin", "ConsentPromptBehaviorUser"],
      "enrichment_fields": [],
      "summary_template": "User Account Control (UAC) is disabled (EnableLUA=0).",
      "evidence_status": "documented"
    },
    {
      "module": "patch_status",
      "source": "patch_status",
      "provider": "windows_native",
      "provider_method": "Get-CimInstance Win32_OperatingSystem",
      "signal_type": "os_out_of_support",
      "category": "endpoint_security",
      "severity": "high",
      "severity_is_conditional": "yes",
      "conditional_rule": "Emit when servicing milestone indicates OS family/version is out of support (requires maintained lookup).",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "Derived from (Caption, BuildNumber) matched against Microsoft servicing milestones",
      "evidence_fields": ["Caption", "Version", "BuildNumber", "OSArchitecture"],
      "enrichment_fields": ["LastBootUpTime"],
      "summary_template": "Operating system is out of support: {Caption} (build {BuildNumber}).",
      "evidence_status": "derived"
    }
  ],
  "confidence_guidance": [
    {
      "module": "disk_encryption_check",
      "signal_type_or_use_case": "disk_encryption_disabled",
      "source_reliability": "High when cmdlet available; OS-reported state.",
      "freshness_considerations": "Encryption/decryption can be transient; re-check after a delay if in progress.",
      "corroboration_rules": "Optionally corroborate with manage-bde status for troubleshooting.",
      "calibration_todo": "Define volume scoping and unsupported-system handling."
    },
    {
      "module": "firewall_status",
      "signal_type_or_use_case": "windows_firewall_profile_disabled",
      "source_reliability": "High; backed by MSFT_NetFirewallProfile provider.",
      "freshness_considerations": "Prefer ActiveStore to reflect effective policy now.",
      "corroboration_rules": "Cross-check with netsh for troubleshooting; store raw values.",
      "calibration_todo": "Normalise uint16/bool representations consistently."
    },
    {
      "module": "os_security",
      "signal_type_or_use_case": "defender_* posture",
      "source_reliability": "Medium-to-high when cmdlet available; avoid negative inference when cmdlet missing.",
      "freshness_considerations": "Signature age is time-based; enforce configurable thresholds.",
      "corroboration_rules": "Corroborate with endpoint security baselines where available.",
      "calibration_todo": "Tune signature-age thresholds and handle sentinel scan ages."
    },
    {
      "module": "patch_status",
      "signal_type_or_use_case": "os_out_of_support",
      "source_reliability": "High if servicing data is maintained from Microsoft release health sources.",
      "freshness_considerations": "Servicing milestones change; refresh lookup periodically.",
      "corroboration_rules": "Account for LTSC/IoT/ESU distinctions where applicable.",
      "calibration_todo": "Implement and test servicing lookup keyed by build/family."
    }
  ]
}
