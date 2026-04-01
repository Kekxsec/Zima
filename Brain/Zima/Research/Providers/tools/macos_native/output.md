---
title: "output / tools / macos_native"
aliases: ["macos_native output", "macos_native signal registry"]
tags: [zima, research, outputs, signal-registry, tools, macos_native, graph_exclude]
type: provider_research_output
provider: macos_native
provider_category: tools
status: not_started
prompt_note: prompt.md
provider_folder: macos_native.md
obsidianUIMode: preview
---
# macos_native implementation-grade research for Zima posture modules

This report treats **macos_native** as a local **os_native_interface**: it is not an alert feed; it provides **posture data** by executing built-in macOS commands (with variable text/JSON/plist outputs) and mapping them into Zima’s normalised signals. Many security-relevant controls (for example **System Integrity Protection**) can only be changed from Recovery/1TR on Apple silicon, which is itself a strong corroboration point for “this was deliberately changed by a human with physical access”. 

## Tool Surface Appendix

### `fdesetup status` — FileVault encryption state

**Exact invocation**

- `fdesetup status`
- Optional: `fdesetup status -extended -verbose` (richer output; can take longer to calculate “time remaining”). 

**Output strings (enabled/disabled)**

- Enabled baseline output is commonly exactly: `FileVault is On.` 
- Disabled baseline output is commonly exactly: `FileVault is Off.` 
- Deferred enablement state may appear as (example): `FileVault is Off. Deferred enablement appears to be active for user 'xxx'.` 
- Encryption in progress may include (example): `FileVault is On. Encryption in progress: Percent completed = XX` (and potentially more progress lines when using extended status). 

**Exit codes** The `fdesetup(8)` man page defines tool exit statuses including:

- `0` = success/no error
- `1` = “FileVault is Off.”
- `2` = “FileVault appears to be On but Busy.”
    …and additional error categories (authentication, parameter error, etc.). 

**Privilege requirements**

- The man page explicitly states `fdesetup` “must be run as root” (especially relevant for operations that unlock/configure FileVault). 
- In practice, many environments run `fdesetup status` under `sudo` for consistency and to avoid permission/visibility differences across configurations. (This is **derived from examples**, not guaranteed by Apple documentation for `status` specifically.) 

**Parsing strategy**

- Primary: **string matching** on the first line of stdout:
    - `^FileVault is On\.` → enabled
    - `^FileVault is Off\.` → disabled
- Secondary (recommended for machine logic): use `fdesetup isactive` rather than scraping `status`:
    - It’s documented to return `exit status 0` with stdout `"true"` when enabled/active, else `exit status 1` with `"false"`. 

**Compatibility + edge cases**

- APFS vs CoreStorage and “in-progress” states exist; “busy” states are explicitly represented by exit code `2`. 
- Deferred enablement (“Off but waiting to be enabled”) is a common enterprise edge case; treat as “not encrypted yet” for posture unless you intentionally model “encryption pending”. 

**Operational error conditions**

- “Busy”/transition (`exit_code == 2`) should be treated as **non-final posture** (do not emit a “disabled” signal; store as evidence/enrichment). 
- If command invocation fails (tool not present, permission denied, etc.), treat as **unknown** and avoid posture failure signals.

---

### `defaults read /Library/Preferences/com.apple.alf globalstate` — Application Firewall

**Exact invocation**

- `defaults read /Library/Preferences/com.apple.alf globalstate` 
- Some operators run with sudo: `sudo defaults read /Library/Preferences/com.apple.alf globalstate` (example-driven). 

**Return values**

- The Center for Internet Security macOS benchmark documents:
    - `1 = on for specific services`
    - `2 = on for essential services` 
- Apple Support Community responses also enumerate:
    - `0 = de-activated`
    - `1 = on for specific services`
    - `2 = on for essential services` 

Interpretation note: “on for essential services” is effectively “block all incoming except essential services” in common admin phrasing; however, treat the **value meaning exactly as documented** above. 

**Privilege requirements**

- Reading may succeed without root (CIS audit uses `defaults read` without `sudo`), but fleet scripts frequently use `sudo` to avoid permission inconsistencies. 
- Writing requires elevated privileges (implied by standard practice; not re-proven in Apple docs in this research pass). 

**Parsing strategy**

- **String-to-int parse** of stdout (`"0"`, `"1"`, `"2"`).
- Reject non-integer stdout as parse error (store raw evidence; do not emit posture signals).

**Version compatibility concerns**

- On newer macOS (notably macOS 15 “Sequoia” in admin reports), toggling via `defaults write … globalstate` may not actually enable the firewall even if the plist reflects the value; admins recommend using `socketfilterfw --setglobalstate` instead. This indicates **potential drift between preference value and effective firewall state** on modern releases. 
    - Action for Zima: treat `globalstate` as **best-effort** unless you add a corroboration step (see Implementation Notes).

**Error conditions**

- If the preference key or domain is missing, `defaults` typically emits an error like “The domain/default pair … does not exist” (illustrated elsewhere in CIS guidance for other `defaults` checks). 
- Treat missing key/domain as **unknown**, not “firewall off”.

---

### `csrutil status` — System Integrity Protection

**Exact invocation**

- `csrutil status` 

**Exact output string (enabled)**

- Apple’s archived SIP guide shows:
    `System Integrity Protection status: enabled.` 

**Exact output string (disabled)**

- The same pattern is widely observed as `… status: disabled.` (this is **inferred from field symmetry and examples**, and should be validated on your supported macOS versions). 

**Recovery mode vs normal boot behaviour**

- The official SIP guide states you must boot to Recovery OS to enable/disable SIP using `csrutil`, and you must reboot after changing it. 
- Apple’s security documentation for Apple silicon explains that changing settings that “significantly degrade security” requires entering recoveryOS, so malware cannot initiate the change—only an in-person actor can. 

**Privilege requirements**

- Checking status does not require root (the guide demonstrates running it from Terminal normally). 

**Parsing strategy**

- **Regex/string match** on stdout:
    - `System Integrity Protection status: enabled.` → SIP enabled
    - `System Integrity Protection status: disabled.` → SIP disabled
- Robustness: ignore leading/trailing whitespace; tolerate additional informational lines if any.

**Edge cases**

- SIP is a core security boundary; Apple describes it as restricting even the root user’s ability to modify protected system locations. 
- Apple silicon stores SIP policy bits in LocalPolicy fields and allows mutation only from 1TR; Apple security docs explicitly connect disabling SIP with downgrading security. 

---

### `spctl --status` — Gatekeeper master assessment state

**Exact invocation**

- `spctl --status` 

**Exact output strings**

- CIS benchmark explicitly expects output: `"assessments enabled"`. 
- When disabled, systems commonly output: `"assessments disabled"` (symmetry-based; validate on the versions you support). 

**Exit codes**

- Not documented in the CIS excerpt or the Apple materials surfaced here; treat exit code semantics as **unclear** and key primarily off stdout. 

**Privilege requirements**

- CIS runs the check with `sudo spctl --status`. It may work without sudo, but use sudo if you want consistency. 

**Output and parsing hazards**

- On some macOS versions, `spctl` may print Objective‑C runtime warnings about duplicated classes being implemented in multiple locations; this is noise for your parse and should be ignored (do not interpret as failure). 
- Some shells show `spctl: option '--master' is ambiguous` when using certain flags; your target command here (`--status`) is still supported in the usage output. 

---

### `system_profiler SPSoftwareDataType -json` — OS version, kernel, uptime, and related fields

**Exact invocation**

- `/usr/sbin/system_profiler SPSoftwareDataType -json`

**Output format**

- JSON object with top-level key `SPSoftwareDataType` (observed). 

**Observed JSON schema (fields to rely on)** A real-world example of parsed output (PowerShell `convertfrom-json`) shows keys including:

- `_name` (commonly `os_overview`)
- `os_version`
- `kernel_version`
- `uptime`
- `boot_volume`, `boot_mode`, `local_host_name`, `secure_vm`, `system_integrity`, `user_name` 

Independent tooling libraries also model these same keys (for example, mapping `os_version`, `kernel_version`, `uptime`, `system_integrity`). 

**About `system_integrity_protection_enabled`**

- In the sources found for `-json`, the key representing SIP is `system_integrity` (with values like `integrity_enabled`), rather than a boolean key named `system_integrity_protection_enabled`. Therefore, treat `system_integrity_protection_enabled` as **unknown/unverified** for `system_profiler -json` until you capture live samples across your supported macOS range. 

**Privilege requirements**

- None expected for this datatype in normal operation (examples run without sudo). 

**Parsing strategy**

- **JSON parsing**.
- Recommended mapper extraction:
    - Find the object in `SPSoftwareDataType` where `_name == "os_overview"` (as in the example), then extract `os_version`, `kernel_version`, `uptime`, and `system_integrity`. 

**Compatibility + edge cases**

- `system_profiler` supports generating incomplete reports if it times out, with a documented default timeout of 180 seconds in the man page mirror. 
- If you call this in constrained environments (Recovery, minimal shells), it may behave differently; for Zima posture collection assume normal boot.

---

### `softwareupdate -l` — pending software updates

**Exact invocation**

- `softwareupdate --list` (alias `softwareupdate -l`). 

**Output format**

- Plain text. Example structure from the man page:
    - `Software Update Tool`
    - `Finding available software`
    - `Software Update found the following new or updated software:`
    - Each update block includes `Label:` and `Title:` fields, with properties like `Version`, `Size`, `Recommended: YES`, and sometimes `Action: restart`. 

**How to distinguish security vs feature updates**

- The man page does not provide a documented “security update” flag in this output format. Therefore classification is **inferred**:
    - Treat updates whose `Title:` contains common strings like “Security Update” / “Rapid Security Response” as security-related.
    - Treat major OS upgrades (titles containing the OS name and a major/minor version) as feature upgrades.
        Because this is naming-based, implement as a heuristic and mark as calibration TODO. 

**Privilege requirements**

- The man page states admin authentication is required for all commands except `--list`. 

**Timeout and network dependency**

- `--list` depends on contacting Apple update sources and can be slow; no explicit timeout behaviour is documented in the man page snapshot available here, so treat timeout handling as **unclear** and enforce your own process timeout. 

**Parsing strategy**

- **Regex extraction**:
    - Detect “no updates” vs “updates present” (exact “no updates” string not captured in the cited man page, so treat as unknown and rely on positive detection of `Label:` blocks). 
    - For each update, capture:
        - `Label` (stable identifier for the update in this output) 
        - `Title` (human readable) 
        - `Recommended` flag implied by the leading `*` prefix in list output (documented). 

---

### `system_profiler SPApplicationsDataType -json` — installed apps inventory

**Exact invocation**

- `/usr/sbin/system_profiler SPApplicationsDataType -json`

**Output format and per-application schema** A concrete example shows that each application entry may include:

- `_name`
- `arch_kind`
- `lastModified`
- `obtained_from`
- `path`
- `signed_by` (array)
- `version` 

Some outputs also include `info` (for example, a richer “copyright/version” string). 

**Performance considerations**

- Admin inventory workflows note that application enumeration can take a long time (and discussions explicitly question its efficiency). Treat it as potentially slow and consider caching and/or lower detail levels where possible. 

**Privilege requirements**

- Not expected for basic enumeration; examples show use without sudo. 

**Parsing strategy**

- **JSON parsing** and pull a small stable subset of fields (`_name`, `version`, `path`, `obtained_from`, `signed_by`, `lastModified`).
- For Zima, treat this as **utility/inventory**, not a standalone security signal, unless you explicitly build an “unapproved software” module later.

---

### `defaults read /Library/Preferences/com.apple.SoftwareUpdate AutomaticCheckEnabled` — automatic update checks and related keys

**Exact invocation**

- `defaults read /Library/Preferences/com.apple.SoftwareUpdate AutomaticCheckEnabled`
- Related keys worth supporting together:
    - `AutomaticDownload`
    - `CriticalUpdateInstall`
    - `ConfigDataInstall` 

**Return values**

- Community and operational documentation treats these booleans as `1` (enabled) / `0` (disabled). 
- Semantics often used by Mac admin tooling:
    - `AutomaticCheckEnabled` → automatic update checking
    - `AutomaticDownload` → background download
    - `ConfigDataInstall` → install system data files
    - `CriticalUpdateInstall` → install security updates 

**Important reliability caveat**

- At least one agent vendor issue report indicates `CriticalUpdateInstall` may not be a reliable reflection of actual behaviour on some macOS configurations (for example after OS upgrades or when the setting is managed elsewhere). Treat these as **best-effort inputs** unless corroborated. 

**Modern macOS device management context**

- Apple’s deployment guidance positions **Declarative Device Management** as the “future” approach for managing Apple software updates, and documents an official “Apple Software Lookup Service” for release metadata. This means local preference keys may increasingly diverge from the effective policy state on supervised/managed Macs. 

**Parsing strategy**

- **String-to-int parse** (`0`/`1`) with robust handling for missing key/domain (treat as unknown).
- Collect all four keys in one run and build a single “auto update posture” evaluation (see signal design below).

---

### `pmset -g` — power management settings (sleep timers)

**Exact invocation**

- `pmset -g` (or `pmset -g custom` for the active profile; both are common patterns in usage). 

**Relevant fields**

- Power management timers include `sleep` and `displaysleep`, and man page mirrors document that providing a minutes value of `0` sets “never” for these idle timers. 

**Privilege requirements**

- Reading (`-g`) does not require root; modifying settings does (“pmset must be run as root in order to modify any settings”). 

**Screen lock on wake**

- `pmset` does **not** directly expose whether “Require password after sleep/screensaver” is enabled. A common admin trick (`pmset displaysleepnow`) only becomes a “lock” when the separate security setting “require a password immediately after sleep” is configured. Therefore “screen lock on wake” is **unclear** from `pmset -g` alone and should not generate a standalone signal unless you add additional macOS-native checks. 

**Parsing strategy**

- Regex parse key/value pairs from stdout; extract integers for `sleep` and `displaysleep`.

---

## Module Mapping Table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|os_security|direct_signal_input|`csrutil status`|SIP status text output|direct_signal_input|`hostname`|Only evaluate if command executes and stdout matches the expected pattern; otherwise treat as unknown and suppress signals.||SIP changes require Recovery/1TR; treat absence of output as collection failure, not “disabled”.|
|os_security|direct_signal_input|`spctl --status`|Gatekeeper master assessment state|direct_signal_input|`hostname`|Ignore objc warnings and parse only the final “assessments …” line.||Exit code behaviour is not clearly documented here; rely on stdout.|
|os_security|enrichment_only|`system_profiler SPSoftwareDataType -json`|OS software JSON blob|enrichment_only|`hostname`|Only parse JSON when it is valid; if invalid/timeout, store raw output and proceed without enrichment.||Use as context (OS version, kernel, uptime). Do not treat as primary SIP source unless you validate the `system_integrity` key across versions.|
|patch_status|direct_signal_input|`softwareupdate -l`|update list plain text|direct_signal_input|`hostname`|Only emit “update available” signals when at least one `Label:` block is detected; impose a hard timeout and treat timeouts as unknown.||Network-dependent; list output encodes “recommended” via `*` prefix.|
|patch_status|direct_signal_input|`defaults read ... com.apple.SoftwareUpdate ...`|`/Library/Preferences/com.apple.SoftwareUpdate` keys|direct_signal_input|`hostname`|Collect all relevant keys; if key missing, treat as unknown rather than disabled.||Some keys may not reliably reflect actual policy state on modern managed Macs; consider corroboration.|
|patch_status|utility_only|`system_profiler SPApplicationsDataType -json`|installed application inventory|utility_only|`hostname`|Run sparingly (scheduled/cached) due to slowness; do not block patch_status signals on this call.||Inventory only (package versions, signing chains). Keep out of standalone signals for current scope.|
|disk_encryption_check|direct_signal_input|`fdesetup status` (prefer `isactive`)|FileVault status stdout + exit code|direct_signal_input|`hostname`|Prefer `fdesetup isactive` for boolean+exit semantics; if using `status`, parse first line only. Suppress “disabled” finding when exit suggests “busy”/in progress.||FileVault “busy” state is explicitly represented by exit status `2`.|
|firewall_status|direct_signal_input|`defaults read ... com.apple.alf globalstate`|firewall globalstate integer|direct_signal_input|`hostname`|Accept only integer 0/1/2; if non-integer or missing key, treat as unknown.||macOS 15+ reports indicate plist writes may not reflect effective state; consider corroboration if accuracy is critical.|
|os_security|out_of_scope|`pmset -g`|power management sleep timers|out_of_scope|`hostname`|No standalone security signal is defensible from `pmset -g` alone for the current modules; collect optionally as context.||`pmset` does not express “require password after sleep/wake”; that setting is separate.|

## Signal Contract Table

Only rows that should be emitted as standalone signals are included.

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|disk_encryption_check|disk_encryption_check|macos_native|`fdesetup status` (prefer `isactive`)|`disk_encryption_disabled`|os_security|high|no|n/a|hostname|true_finding|**Preferred:** `fdesetup isactive` returns `exit_code == 1` and stdout == `"false"` (FileVault off). **Fallback:** `stdout` starts with `FileVault is Off.`|`command`, `args`, `exit_code`, `stdout`, `stderr`, `stdout_first_line`, `collection_timestamp`|`encryption_progress_lines` (if present), `os_version` (if available separately)|`Disk encryption is disabled (FileVault is off) on {hostname}.`|documented (for isactive semantics + exit) + inferred (for status strings)||Treat `exit_code == 2` (“busy”) as transitional → store evidence but do not emit “disabled”.|
|firewall_status|firewall_status|macos_native|`defaults read ... com.apple.alf globalstate`|`host_firewall_disabled`|network_security|high|no|n/a|hostname|true_finding|`stdout == "0"` (globalstate disabled).|`command`, `args`, `exit_code`, `stdout`, `stderr`, `globalstate_raw`|`globalstate_meaning` (0/1/2 mapping), `stealth_mode_status` (if you add it later), `os_version`|`Host firewall is disabled on {hostname}.`|derived from documented fields||If you observe macOS 15+ mismatches between plist state and effective firewall, add corroboration before emitting.|
|os_security|os_security|macos_native|`csrutil status`|`sip_disabled`|os_security|high|no|n/a|hostname|true_finding|`stdout` contains `System Integrity Protection status: disabled.`|`command`, `args`, `exit_code`, `stdout`, `stderr`, `sip_status_raw`|`sip_change_requires_recovery` (context), `local_policy_bits` (if later collected)|`System Integrity Protection (SIP) is disabled on {hostname}.`|documented (enabled output + recovery requirement) + inferred (disabled string)||SIP disablement is a strong indicator of intentional security downgrade.|
|os_security|os_security|macos_native|`spctl --status`|`gatekeeper_disabled`|os_security|medium|no|n/a|hostname|true_finding|`stdout` contains `assessments disabled` (Gatekeeper disabled).|`command`, `args`, `exit_code`, `stdout`, `stderr`|`objc_warning_lines` (if present), `assessment_state_raw`|`Gatekeeper assessments are disabled on {hostname}.`|documented (enabled string) + inferred (disabled string)||Filter out objc warnings and parse only the assessments line.|
|patch_status|patch_status|macos_native|`softwareupdate -l`|`os_update_available`|patch_management|medium|yes|If the update appears security-related (title contains “Security Update” or “Rapid Security Response”), raise to **high**; otherwise keep **medium**.|hostname|true_finding|Detect at least one update entry: stdout contains `Software Update found the following new or updated software:` **and** includes at least one `Label:` block.|`command`, `args`, `exit_code`, `stdout`, `stderr`, `raw_update_blocks` (label/title/version/size/action)|`recommended_flag` (based on `*` prefix), `restart_required` (from “Action: restart”), `os_version`|`macOS has pending software updates available on {hostname}.`|derived from documented fields (availability + recommended marking) + inferred (security classification)||The list output documents `*` (recommended) and `-` (non‑recommended). Security-vs-feature classification is naming heuristic and must be calibrated.|
|patch_status|patch_status|macos_native|`defaults read ... com.apple.SoftwareUpdate AutomaticCheckEnabled`|`auto_updates_disabled`|patch_management|medium|yes|If `AutomaticCheckEnabled == 0` **and** (`CriticalUpdateInstall == 0` or key missing/false), treat as “higher urgency” within medium (do not exceed guide without evidence).|hostname|true_finding|`AutomaticCheckEnabled == 0` (from defaults stdout). Optionally extend trigger with `AutomaticDownload == 0` to indicate broad disablement.|`command`, `args`, `exit_code`, `stdout`, `stderr`, `AutomaticCheckEnabled`, `AutomaticDownload`, `CriticalUpdateInstall`, `ConfigDataInstall`|`policy_source_hint` (managed/unmanaged if you later detect profiles), `softwareupdate_schedule` (if later added)|`Automatic macOS update checking is disabled on {hostname}.`|inferred from examples + third-party admin documentation||These keys may not perfectly reflect effective update policy on managed macOS; treat as best-effort unless corroborated.|

### Severity Rules

Severity assignments follow your calibration guide and the constraints of what the provider evidences.

- `disk_encryption_disabled` = **high** because full-disk encryption being off is a direct loss of a core data protection control and materially increases impact of device loss/theft (posture-risk, not a “pure contextual” fact). Evidence is direct from `fdesetup` state. 
- `host_firewall_disabled` = **high** because it is a direct security control being off; it increases exposure to unsolicited inbound connections and weakens host boundary protection. Evidence is the firewall globalstate value. 
- `sip_disabled` = **high** because SIP restricts even root access to protected system locations; disabling it is an explicit security downgrade that makes the system easier to compromise and harder to trust for enforcement. 
- `gatekeeper_disabled` = **medium** because it weakens application execution controls; it materially increases risk of running untrusted code, but it is not itself a direct credential exposure. Evidence is the “assessments …” state. 
- `os_update_available` = **medium** baseline because “updates available” is not always a high-risk security condition; severity becomes **conditional** if you can confidently identify a security update (naming heuristic in this pass). Evidence is `softwareupdate --list` output entries and the recommended marker semantics. 
- `auto_updates_disabled` = **medium** because it increases the likelihood of staleness and missed security patches; however the observable evidence (preference values) can be unreliable on managed Macs, so do not escalate beyond medium without corroboration from other sources. 

## Confidence Guidance

|module|signal_type_or_use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|disk_encryption_check|`disk_encryption_disabled`|High reliability: `fdesetup` is the canonical platform tool and exposes explicit exit codes for FileVault state.|Mostly stable; “busy/in progress” states must be handled to avoid false “disabled”.|If `exit_code == 2` (busy), delay signal emission and recheck later. Optionally corroborate with extended status lines when available.|Capture fleet samples of all observed `fdesetup status` variants (APFS, deferred enablement, keychain messages) and normalise parsing rules.|
|firewall_status|`host_firewall_disabled`|Medium-to-high, but may degrade on modern macOS if preference values drift from effective firewall state.|Generally current if the system updates the plist promptly; reliability concerns increase on macOS 15+.|If possible, add a corroboration command (within macos_native) that queries effective firewall state (and reconcile). If not, mark confidence lower on macOS 15+.|Build a macOS-version-aware confidence modifier: if macOS >= 15 and only `globalstate` is used, treat as “needs corroboration”.|
|os_security|`sip_disabled`|High: Apple documents SIP and its status check, and emphasises recovery-only changes for security downgrades.|Very stable; SIP status is a point-in-time check.|Corroborate by storing the full `csrutil status` stdout and (optionally) OS build/version. If SIP disabled on Apple silicon, note that change required 1TR/recovery.|Validate the exact disabled output strings across supported macOS builds; handle partial SIP states if they appear in your estate.|
|os_security|`gatekeeper_disabled`|Medium: CIS shows the expected enabled output, but exit codes and all variant outputs aren’t fully documented in the sources used here; also `spctl` can emit non-fatal warnings.|Stable; however, per-device developer workflows may disable Gatekeeper temporarily, leading to churn.|Robust parsing: ignore objc warning lines; require explicit `assessments disabled` line before emitting.|Collect real fleet samples on Big Sur→Sequoia; confirm that “assessments disabled” always appears when disabled and assess whether exit codes can be trusted.|
|patch_status|`os_update_available`|Medium: output format is documented, but classification and “no updates” messaging are not fully captured in the sources used; network errors can look like “no updates” if mis-parsed.|Highly time-sensitive and environment-dependent (update deferrals, MDM, network reachability). Apple is moving to declarative update management and an official lookup service for release metadata.|If `softwareupdate -l` times out or errors, emit no “no updates” conclusion; treat as unknown. Optionally corroborate by recording `os_version` and comparing against a managed “latest release” feed (outside macos_native).|Decide whether Zima will compute “significantly out of date” using an external release feed; if yes, move that logic to posture/correlation layer and keep macos_native purely observational.|
|patch_status|`auto_updates_disabled`|Medium-to-low: keys exist and are commonly used, but at least one report indicates they can be inaccurate reflections of effective state after upgrades/management changes.|These are “configuration posture” values; can remain stale or overridden by device management. Apple’s DDM trajectory increases the chance that local preference checks miss the true effective policy.|Where feasible, corroborate with device-management state (profiles, declarative configuration) in other providers/layers, and treat defaults-based signals as hints.|Add TODO: detect whether the Mac is managed and whether update enforcement/deferrals are applied (likely not via macos_native alone).|

## Implementation Notes

### Sudo requirements and fallback behaviour

- **Requires sudo / root for reliable posture**

    - `fdesetup` is documented to require root, and exit codes are meaningful; run via a privileged collector context when possible. 
    - Firewall state reading is frequently executed under sudo in admin scripts; reading might work without, but use sudo if your agent runs with privilege. 
- **Does not require sudo for read-only checks (expected)**

    - `csrutil status` for status checks. 
    - `softwareupdate -l` is documented to not require admin authentication (other commands do). 
    - `system_profiler … -json` for SPSoftwareDataType/SPApplicationsDataType in common usage. 

**Fallback behaviour when unprivileged**

- If `defaults read …` fails due to permissions or missing domain/key, treat as **unknown** (no signal) and preserve stderr/stdout for audit. 
- If `fdesetup` cannot run with required privileges, treat as **unknown** and emit a collection error (internal), not a posture signal.

### Output parsing strategy summary

- `fdesetup status`: string match first line; prefer `fdesetup isactive` for deterministic exit code + boolean stdout. 
- Firewall globalstate: string-to-int parse. 
- `csrutil status`: string/regex match exact substring. 
- `spctl --status`: string match `assessments enabled/disabled`; ignore objc warning prefixes. 
- `system_profiler … -json`: JSON parsing; extract specific keys observed to be stable. 
- `softwareupdate -l`: regex parse `Label:` / `Title:` blocks and the `*` recommended marker. 
- `pmset -g`: regex parse `sleep` and `displaysleep` values; do not attempt “screen lock on wake” without additional checks. 

### Handling macOS version differences

- **SIP**: On Apple silicon, SIP policy is handled via LocalPolicy/1TR; changing it requires recoveryOS/1TR. This is consistent with Apple’s security model; incorporate into evidence/enrichment for `sip_disabled`. 
- **Application Firewall**: macOS 15 (“Sequoia”) admin reports indicate writing `globalstate` in the plist may not take effect; reading may still reflect a value while the effective firewall state differs. Treat this as a major version-risk factor and consider corroboration. 
- **Software Updates**: Apple’s deployment guidance emphasises DDM and an official release lookup service; local CLI results remain valuable but should be treated as one input among others for “out of date” determinations. 
- **system_profiler JSON keys**: observed keys (`os_version`, `kernel_version`, `uptime`, etc.) exist in examples; however field names like `system_integrity_protection_enabled` are not verified in the sources for `-json`. Base mapping only on keys you observe in the wild and treat the rest as unknown. 

### Deduplication keys and raw evidence storage

For posture signals, a natural dedup key is:

- `dedup_key = (signal_type, entity_type, entity_value, “current_state”)`

Where “current_state” is the normalised state (e.g., `disabled` vs `enabled`) and entity_value is the stable host identifier your platform uses (hostname, device_id, or management UUID). Use `hostname` as the Zima `entity_type` only if you have stable hostname input; otherwise, define a stable internal “device id” and map to `hostname` only for display.

Always persist raw execution metadata per command:

- `command`, `args`, `exit_code`, `stdout`, `stderr`, `duration_ms`, `collected_at`, and (optionally) `uid/euid` by which it ran.

This is essential for auditability, especially when parsing text outputs that can vary.

### Provider client vs module mapper vs correlation layer

- **Provider client (macos_native)** should do only:

    - safe command execution
    - timeout enforcement (especially for `softwareupdate -l` and `system_profiler SPApplicationsDataType`)
    - return `{stdout, stderr, exit_code, duration}`
- **Module mapper (`modules/*/mapper.py`)** should:

    - parse outputs into a minimal normalised intermediate structure (booleans/ints and the raw strings)
    - preserve raw evidence fields exactly
- **Module rules (`modules/*/rules.py`)** should:

    - apply trigger logic and gating
    - apply severity rules per your calibration guide
- **Correlation/posture abstraction layer (“posture provider”)** should:

    - compute “significantly out of date” based on external release intelligence (if desired)
    - reconcile contradictory indicators (for example, firewall plist vs effective firewall in newer macOS)
    - handle cross-source confidence calibration and fleet-based tuning 

## Provider Summary

Strongest signal types and utility contributions

- The strongest posture signals supported directly by macos_native for your target modules are:
    - FileVault off (`fdesetup` state + exit codes). 
    - SIP disabled (`csrutil status`). 
    - Gatekeeper disabled (`spctl --status`). 
    - Firewall disabled (`com.apple.alf globalstate`). 
    - Updates available via `softwareupdate -l`, with recommended markers and per-update label/title blocks. 
- The strongest utility contribution is **inventory**:
    - OS software profile via `system_profiler SPSoftwareDataType -json`. 
    - Installed apps via `system_profiler SPApplicationsDataType -json` (slow; best-effort). 

What macos_native should not be used for

- It is not a vulnerability scanner and cannot natively enumerate CVEs; “significantly out of date” requires external release intelligence and/or device management telemetry beyond macos_native’s raw outputs. 
- `pmset -g` alone should not be used to claim “screen lock on wake is enabled/disabled”; lock enforcement is a separate configuration. 

Installation / privilege / platform cautions

- macos_native is macOS-only and relies on built-in tools. Several relevant operations (especially FileVault management) require root privileges. 
- On Apple silicon, core security setting changes require entering recoveryOS/1TR, which is relevant context for interpreting SIP changes. 

Overall provider posture classification

- For these modules, treat macos_native as **signal-producing** (direct_signal_input) for posture failures (FileVault/firewall/SIP/Gatekeeper/updates available), **enrichment** for OS context, and **utility-only** for application inventory.

{
  "provider": "macos_native",
  "provider_category": "tools",
  "provider_role": "direct_signal_input for posture checks, utility_only for inventory",
  "module_mappings": [
    {
      "module": "os_security",
      "provider_role": "direct_signal_input",
      "provider_method": "csrutil status",
      "endpoint_or_artifact": "stdout/stderr/exit_code",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "only evaluate if stdout contains 'System Integrity Protection status:'; otherwise unknown",
      "citation_refs": ["turn32search2", "turn32search0"],
      "notes": "SIP changes require recoveryOS/1TR on Apple silicon; store full stdout as evidence"
    },
    {
      "module": "os_security",
      "provider_role": "direct_signal_input",
      "provider_method": "spctl --status",
      "endpoint_or_artifact": "stdout/stderr/exit_code",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "ignore objc warnings; require explicit 'assessments enabled/disabled' line",
      "citation_refs": ["turn12view0", "turn30view0"],
      "notes": "Exit codes unclear; rely on stdout"
    },
    {
      "module": "patch_status",
      "provider_role": "direct_signal_input",
      "provider_method": "softwareupdate -l",
      "endpoint_or_artifact": "stdout/stderr/exit_code",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "require at least one update Label block; timeout => unknown",
      "citation_refs": ["turn14view1", "turn21search9"],
      "notes": "Network dependent; recommended updates prefixed with '*'"
    },
    {
      "module": "patch_status",
      "provider_role": "direct_signal_input",
      "provider_method": "defaults read /Library/Preferences/com.apple.SoftwareUpdate <key>",
      "endpoint_or_artifact": "/Library/Preferences/com.apple.SoftwareUpdate.plist keys",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "parse 0/1; missing key => unknown; consider managed-mac drift",
      "citation_refs": ["turn19search8", "turn19search1"],
      "notes": "Keys may not reflect effective policy on managed/modern macOS; treat as best-effort"
    },
    {
      "module": "disk_encryption_check",
      "provider_role": "direct_signal_input",
      "provider_method": "fdesetup status (prefer isactive)",
      "endpoint_or_artifact": "stdout/stderr/exit_code",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "prefer isactive exit_code; treat exit_code==2 as transitional, not disabled",
      "citation_refs": ["turn28view0", "turn29search19"],
      "notes": "Status output variants include deferred enablement and in-progress states"
    },
    {
      "module": "firewall_status",
      "provider_role": "direct_signal_input",
      "provider_method": "defaults read /Library/Preferences/com.apple.alf globalstate",
      "endpoint_or_artifact": "/Library/Preferences/com.apple.alf.plist globalstate",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "parse integer 0/1/2 only; otherwise unknown",
      "citation_refs": ["turn13view2", "turn11search6"],
      "notes": "macOS 15+ reports indicate defaults write may not effectively toggle firewall"
    }
  ],
  "signal_contracts": [
    {
      "module": "disk_encryption_check",
      "source": "disk_encryption_check",
      "provider": "macos_native",
      "provider_method": "fdesetup isactive/status",
      "signal_type": "disk_encryption_disabled",
      "category": "os_security",
      "severity": "high",
      "severity_is_conditional": "no",
      "conditional_rule": "n/a",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "isactive: exit_code==1 and stdout=='false'; status fallback: stdout startswith 'FileVault is Off.'",
      "evidence_fields": ["command", "args", "exit_code", "stdout", "stderr", "collected_at"],
      "enrichment_fields": ["encryption_progress_lines", "os_version"],
      "summary_template": "Disk encryption is disabled (FileVault is off) on {hostname}.",
      "evidence_status": "documented + inferred",
      "citation_refs": ["turn28view0", "turn29search19", "turn29search2"],
      "notes": "Suppress disabled finding if exit_code==2 (busy)"
    },
    {
      "module": "firewall_status",
      "source": "firewall_status",
      "provider": "macos_native",
      "provider_method": "defaults read com.apple.alf globalstate",
      "signal_type": "host_firewall_disabled",
      "category": "network_security",
      "severity": "high",
      "severity_is_conditional": "no",
      "conditional_rule": "n/a",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "stdout=='0'",
      "evidence_fields": ["command", "args", "exit_code", "stdout", "stderr", "collected_at"],
      "enrichment_fields": ["globalstate_meaning"],
      "summary_template": "Host firewall is disabled on {hostname}.",
      "evidence_status": "derived",
      "citation_refs": ["turn11search6", "turn13view2"],
      "notes": "Consider corroboration on macOS 15+"
    },
    {
      "module": "os_security",
      "source": "os_security",
      "provider": "macos_native",
      "provider_method": "csrutil status",
      "signal_type": "sip_disabled",
      "category": "os_security",
      "severity": "high",
      "severity_is_conditional": "no",
      "conditional_rule": "n/a",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "stdout contains 'System Integrity Protection status: disabled.'",
      "evidence_fields": ["command", "args", "exit_code", "stdout", "stderr", "collected_at"],
      "enrichment_fields": ["sip_change_requires_recovery_context"],
      "summary_template": "System Integrity Protection (SIP) is disabled on {hostname}.",
      "evidence_status": "documented + inferred",
      "citation_refs": ["turn32search2", "turn32search0", "turn32search6"],
      "notes": "Treat as strong intentional security downgrade indicator"
    },
    {
      "module": "os_security",
      "source": "os_security",
      "provider": "macos_native",
      "provider_method": "spctl --status",
      "signal_type": "gatekeeper_disabled",
      "category": "os_security",
      "severity": "medium",
      "severity_is_conditional": "no",
      "conditional_rule": "n/a",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "stdout contains 'assessments disabled'",
      "evidence_fields": ["command", "args", "exit_code", "stdout", "stderr", "collected_at"],
      "enrichment_fields": ["objc_warning_lines"],
      "summary_template": "Gatekeeper assessments are disabled on {hostname}.",
      "evidence_status": "documented + inferred",
      "citation_refs": ["turn12view0", "turn30view0"],
      "notes": "Ignore objc warnings; exit code behaviour unknown"
    },
    {
      "module": "patch_status",
      "source": "patch_status",
      "provider": "macos_native",
      "provider_method": "softwareupdate -l",
      "signal_type": "os_update_available",
      "category": "patch_management",
      "severity": "medium",
      "severity_is_conditional": "yes",
      "conditional_rule": "raise to high if update title indicates security/RSR; else medium",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "stdout contains 'Software Update found the following new or updated software:' and contains at least one 'Label:' block",
      "evidence_fields": ["command", "args", "exit_code", "stdout", "stderr", "collected_at"],
      "enrichment_fields": ["parsed_updates", "restart_required", "recommended_flag"],
      "summary_template": "macOS has pending software updates available on {hostname}.",
      "evidence_status": "derived + inferred",
      "citation_refs": ["turn14view1", "turn21search9"],
      "notes": "Naming-based security classification must be calibrated"
    },
    {
      "module": "patch_status",
      "source": "patch_status",
      "provider": "macos_native",
      "provider_method": "defaults read com.apple.SoftwareUpdate AutomaticCheckEnabled",
      "signal_type": "auto_updates_disabled",
      "category": "patch_management",
      "severity": "medium",
      "severity_is_conditional": "yes",
      "conditional_rule": "treat as higher urgency within medium when also not installing critical updates",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "AutomaticCheckEnabled == 0",
      "evidence_fields": ["command", "args", "exit_code", "stdout", "stderr", "collected_at", "AutomaticCheckEnabled", "AutomaticDownload", "ConfigDataInstall", "CriticalUpdateInstall"],
      "enrichment_fields": ["managed_policy_context"],
      "summary_template": "Automatic macOS update checking is disabled on {hostname}.",
      "evidence_status": "inferred",
      "citation_refs": ["turn19search8", "turn19search0", "turn19search1"],
      "notes": "Keys may be inaccurate on some hosts; corroborate where possible"
    }
  ],
  "confidence_guidance": [
    {
      "module": "disk_encryption_check",
      "signal_type_or_use_case": "disk_encryption_disabled",
      "source_reliability": "High (documented fdesetup exit codes)",
      "freshness_considerations": "Handle busy/in-progress states to avoid false negatives",
      "corroboration_rules": "If exit_code==2, recheck later; store progress lines",
      "calibration_todo": "Collect real fleet output variants and normalise parsing"
    },
    {
      "module": "firewall_status",
      "signal_type_or_use_case": "host_firewall_disabled",
      "source_reliability": "Medium-to-high (preference-based; may drift on macOS 15+)",
      "freshness_considerations": "Preference may not reflect effective state on newer macOS",
      "corroboration_rules": "Add corroboration command for effective firewall state if possible",
      "calibration_todo": "Version-aware confidence modifier for macOS 15+"
    },
    {
      "module": "os_security",
      "signal_type_or_use_case": "sip_disabled",
      "source_reliability": "High (Apple-documented status + recovery requirement)",
      "freshness_considerations": "Point-in-time stable",
      "corroboration_rules": "Store full stdout; note recovery-only change context",
      "calibration_todo": "Validate disabled output and partial SIP states across supported builds"
    },
    {
      "module": "patch_status",
      "signal_type_or_use_case": "os_update_available",
      "source_reliability": "Medium (text output; network dependent)",
      "freshness_considerations": "Highly time-sensitive; deferrals and management change visibility",
      "corroboration_rules": "Timeout/error => unknown; optional external release feed for 'out of date'",
      "calibration_todo": "Define where 'significantly out of date' logic lives (likely correlation layer)"
    }
  ]
}
