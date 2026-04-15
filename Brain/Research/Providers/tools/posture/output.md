---
title: "output / tools / posture"
aliases: ["posture output", "posture signal registry"]
tags: [zima, research, outputs, signal-registry, tools, posture, graph_exclude]
type: provider_research_output
provider: posture
provider_category: tools
status: not_started
prompt_note: prompt.md
provider_folder: posture.md
obsidianUIMode: preview
kind: artifact
llm_include: false
code_scope: backend
---
# Posture provider deep research for Zima endpoint modules

## Evidence base and scope

This report is constrained by the fact that no Zima-internal documentation, OpenAPI specs, or repository/code for your in-house `posture` component were provided via connected sources or uploads. The only implementation-grade, publicly auditable artefacts matching the name _posture_ and the described tool shape (cross-platform posture inspection that wraps OS-native calls and emits normalised results) are the provider-maintained README, docs, and source code for the open-source `plexusone/posture` tool. 

Accordingly:

- Anything stated about **interfaces, JSON field names, enum/status strings, and OS-native calls** is grounded in provider-maintained documentation and code within that tool. 
- Anything stated about **firewall status, screen lock, SIP, Gatekeeper** support is based on the absence of those checks from the documented command surface and (where possible) codebase references; missing features are treated as **out_of_scope** for this provider as currently evidenced. 
- Where you asked for Zima-specific component behaviour (e.g., “wraps macos_native/windows_native/linux_native”), this report provides the best-match abstraction description from the public posture architecture and flags the Zima-specific mapping as **unknown**. 

If your internal `posture` diverges from the public tool, treat this as a baseline contract proposal and validation checklist; the module contracts below are designed to be portable into `modules/*/mapper.py` / `rules.py` with minimal changes once you confirm the true output schema.

## Tool surface appendix

### Interfaces and artefacts

Provider `posture` (as documented in `plexusone/posture`) exposes three primary surfaces—each capable of partial runs (e.g., encryption check only): CLI subcommands, an MCP server tool set, and a Go module API. 

**CLI artefacts (partial runs supported by subcommand selection)**

The README documents the following subcommands (examples shown with the table formatter, but JSON is the documented default output format): 

- `posture summary`
- `posture security-chip`
- `posture secureboot`
- `posture encryption`
- `posture biometrics`
- `posture cpu`
- `posture memory`
- `posture processes`

The README also documents output formats: “JSON (default)” and a rich table display format. 

**MCP server artefacts (partial runs supported by tool selection)**

The MCP server is started with `posture serve`, and the exposed tools include (among others) `get_encryption_status` and `get_security_summary`. 

**Go module artefacts (partial runs supported by function selection)**

The README documents the `inspector` package and a function list including `GetEncryptionStatus()` and `GetSecuritySummary()`, plus per-check `IsXXXSupported()` helpers. 

### Provider “what it adds” beyond raw OS commands

The tool is explicit about being read-only and non-invasive and not making network requests. 
It also adds a cross-platform normalisation layer:

- A normalised JSON schema per check (with stable json tags in structs).
- A computed “Security Summary” with an overall score and recommendations (a derived, aggregated view). 

### Security summary schema (enrichment/aggregation artefact)

The provider-maintained README includes an example JSON output for the security summary with top-level keys: `platform`, `overall_score`, `overall_status`, `tpm`, `secure_boot`, `encryption`, `biometrics`, and `recommendations`. 

The implementation in `summary.go` defines these JSON field names formally and shows summary construction, including score increments of 25 points per enabled feature and overall status buckets (`excellent`, `good`, `fair`, `needs_improvement`, `critical`). 

Because summary is an aggregation of sub-checks (and because your Zima modules are already decomposed into `disk_encryption_check`, `firewall_status`, etc.), the summary artefact is best treated as **enrichment-only** for Zima unless you intentionally add an “overall posture degraded” signal type.

## Check catalogue and OS-native implementation details

This section documents the checks relevant to your target modules and, for completeness, the posture checks that exist in the evidenced provider surface.

### Disk encryption check

#### Output schema (field names and shapes)

On all three supported OS targets (darwin/windows/linux), the encryption check is implemented with the same JSON field names:

Top-level object:

- `enabled` (bool)
- `platform` (string; e.g., `"darwin"`, `"windows"`, `"linux"`)
- `type` (string; encryption system type)
- `status` (string; provider-defined status)
- `encrypted_volumes` (list; optional)
- `details` (string; optional) 

Volume objects inside `encrypted_volumes`:

- `name` (string)
- `mount_point` (string; optional)
- `encrypted` (bool)
- `status` (string) 

#### Enumerated/observed status strings

The provider code explicitly sets (at minimum) the following status values:

- macOS (`platform="darwin"`): top-level `status` can be `enabled`, `disabled`, `encrypting`, `decrypting`, or `unknown` depending on parsed command output or errors. 
- Windows (`platform="windows"`): top-level `status` can be `enabled`, `disabled`, or `unknown`. Per-volume `status` can be `encrypted`, `encrypting`, `decrypting`, `encryption_paused`, `decryption_paused`, `protected`, or `not_encrypted`. 
- Linux (`platform="linux"`): top-level `status` becomes `enabled` if any encrypted volumes are detected, else `disabled`. Per-volume `status` includes `encrypted_active`, `configured_active`, `configured_inactive`, and `luks_device`. 

These strings are implementation-defined (not vendor-defined) and should be treated as the canonical enums for Zima mapping—for as long as you pin to the same posture version. 

#### OS-native mechanisms wrapped (and what posture infers)

macOS (FileVault)

- Primary: runs `fdesetup status` and uses string matches to map to `enabled/disabled/encrypting/decrypting`. 
- Secondary (volume evidence): calls `diskutil apfs list -plist` but does not parse the plist; it uses the presence of certain substrings to decide whether to additionally call `diskutil info /` and then checks for lines like `"FileVault:"`/`"Encrypted:"` and `"Yes"`. 

Privilege/error behaviour:

- If `fdesetup status` fails, the function does **not** return an error; it returns `status="unknown"` and a `details` string indicating it may require admin. 

Windows (BitLocker)

- Uses WMI in the `root\cimv2\Security\MicrosoftVolumeEncryption` namespace and queries `Win32_EncryptableVolume`. 
- Interprets `ProtectionStatus` (commented mapping: 0=OFF, 1=ON, 2=UNKNOWN) and uses `ConversionStatus` to derive per-volume status like `encrypted` or `encrypting`. 

Privilege/error behaviour:

- The code notes the WMI query requires running as administrator; if query fails or yields zero volumes, it returns `status="unknown"` with a “may require admin privileges” details message (again: returned as a normal result, not a thrown error). 

Linux (LUKS/dm-crypt)

- Detection path 1: enumerates `/dev/mapper`, uses `dmsetup table <name>` and checks for `"crypt"` in the table output; optionally tries to find `mount_point` via `findmnt`. 
- Detection path 2: reads `/etc/crypttab` and records configured encrypted volumes, marking them `configured_active` if present in `/dev/mapper` else `configured_inactive`. 
- Detection path 3: globs block devices like `/dev/sd*` and `/dev/nvme*` and calls `cryptsetup isLuks <dev>`; if successful, adds a `luks_device` entry. 

Privilege/error behaviour:

- Unlike macOS/Windows, most command failures simply reduce detections rather than producing `status="unknown"`. The function ultimately sets `status="disabled"` if the discovered `encrypted_volumes` list is empty, which can create **false “disabled” findings** if tooling is missing or restricted. 

### Firewall, Gatekeeper, SIP, and screen lock checks

Your first-pass severity list implies you expect checks for firewall status, screen lock, System Integrity Protection, and Gatekeeper. However, the evidenced posture provider surface does not include a firewall check or any explicit Gatekeeper/SIP/screen lock check:

- Documented CLI subcommands do not include firewall. 
- The README feature list covers platform security chip, secure boot, disk encryption, biometrics, and system metrics—not firewall, Gatekeeper, SIP, or screen lock. 
- A direct search for “firewall” within the documented README and inspector directory view yields no matches. 

If your _Zima-internal_ posture component actually includes these checks, its schema and commands are **unknown** from the available evidence, and you should not build rules off speculative field names.

For future extension planning (not current-posture behaviour), the most canonical OS-native commands for these checks are:

- SIP: `csrutil status` (Apple’s own documentation shows the command and example output). 
- Gatekeeper assessment subsystem: `spctl --status` (Apple documentation demonstrates usage). 
- macOS application firewall status: `socketfilterfw --getglobalstate` (documented in manpage mirrors; treat as third-party sourced). 
- Windows firewall management and status can be obtained via PowerShell and `netsh` tooling (Microsoft support documentation summarises command-line management). 

These references are included only as corroboration/extension inputs for Zima engineering, not as claims about the current posture provider implementation.

## Module mapping table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|disk_encryption_check|direct_signal_input|`get_encryption_status` / `inspector.GetEncryptionStatus()`|CLI: `posture encryption` (JSON default); MCP tool; Go module function|direct_signal_input|hostname|Only evaluate when output parses; if `status == "unknown"` treat result as utility/telemetry and **do not emit** a “disabled” signal||Cross-platform schema is aligned by JSON tags; OS implementations differ materially in reliability (Linux tends to “disabled” on missing tools; Windows/macOS return `unknown`).|
|firewall_status|direct_signal_input|unknown|unknown|out_of_scope|hostname|N/A (no evidenced provider coverage)||If your Zima-internal posture includes firewall checks, you must confirm schema/fields. Otherwise: create a new `posture` check or consume OS-native providers directly.|
|os_security|direct_signal_input|`get_security_summary` / `inspector.GetSecuritySummary()`|CLI: `posture summary`; MCP tool; Go module function|enrichment_only|hostname|Do not emit standalone risk signals from `overall_score` alone; only use summary to enrich downstream UI/remediation context||The summary is an aggregation of sub-checks already decomposed in Zima; keep it enrichment-only to avoid noisy/unstable “score changed” alerts.|

## Signal contract and severity rules

### Signal contract table

Only one standalone signal is justified from the evidenced posture provider surface for your target modules: **disk encryption disabled**. Firewall and OS security controls (screen lock/SIP/Gatekeeper) are not currently available as posture checks in the documented/provider-maintained artefacts. 

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|disk_encryption_check|disk_encryption_check|posture|`get_encryption_status` / `GetEncryptionStatus()`|`disk_encryption_disabled`|os_security|high|no|N/A|hostname|true_finding|`enabled == false AND status == "disabled"`|`platform`, `type`, `enabled`, `status`, `details`, `encrypted_volumes[].name`, `encrypted_volumes[].mount_point`, `encrypted_volumes[].encrypted`, `encrypted_volumes[].status`|(optional) `security_summary.overall_score`, `security_summary.overall_status`, `security_summary.recommendations[]`|`Disk encryption is disabled on {hostname} ({platform}/{type}).`|documented||**Important:** For Windows, top-level `enabled` becomes true if _any_ volume is protected; you may miss partial coverage risk unless you inspect `encrypted_volumes[]`.|

### Severity rules rationale

`disk_encryption_disabled` is assigned **high** severity because the provider’s own evidence indicates encryption is not enabled (`enabled == false` and `status == "disabled"`), which directly maps to your platform guide’s “disk encryption disabled = high”. (Your guide is the controlling severity rubric; posture’s score/status are not used for severity.) 

No conditional severity rule is applied in the contract above because the trigger is narrowly scoped to the provider’s explicit disabled state. If you later choose to account for partial encryption (e.g., Windows D: unencrypted), that would require a second signal type (such as `disk_encryption_partial`) or a conditional rule based on `encrypted_volumes[]`—but that is not part of the current required signal set and should be validated against real fleet data first. 

### Tags

For `disk_encryption_disabled`, the most defensible tags from your constrained list are:

- `misconfiguration`
- `pii_exposure` (use as _risk context_ tag only—this finding is not proof of PII exposure, but it meaningfully increases exposure impact if the device is lost or accessed offline)

## Confidence guidance

|module|signal_type_or_use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|disk_encryption_check|`disk_encryption_disabled`|High when posture can successfully query OS-native sources and returns explicit `status == "disabled"`; reliability varies by OS due to implementation: macOS and Windows return `unknown` on access failure, while Linux tends to “disabled” when no encrypted volumes are detected (which can be a false negative if required tools are missing or restricted).|Local posture is point-in-time; encryption can transition (`encrypting`, `decrypting`) and posture reflects that for macOS (and per-volume for Windows).|For any “disabled” finding on Linux, corroborate by running an OS-native confirmation path (e.g., confirm dm-crypt mappings and/or `cryptsetup isLuks`) before auto-escalating org-wide remediation. For Windows, corroborate that the **system volume** is unencrypted (if you add that enhancement) because current posture deems “enabled” if any volume is protected.|Decide whether Zima’s policy is “system volume must be encrypted” vs “all fixed volumes must be encrypted”; implement volume scoping rules accordingly. Add explicit “unknown” / “insufficient privileges” visibility as an agent-health path (not a security finding). Evaluate Linux false-negative rates caused by missing `dmsetup/findmnt/cryptsetup` and add better `unknown` reporting if needed.|
|firewall_status|No current posture coverage|Low (provider does not expose the check in documented surface)|N/A|N/A|Either (a) implement a firewall check inside posture with a documented schema, or (b) consume OS-native providers directly. Confirm the long-term contract you want: “firewall enabled boolean + mode/details” vs richer configuration state.|
|os_security|Security summary enrichment|Medium as enrichment because it is derived and compresses multiple checks into a score; use for context only, not alerting|Score/status can change when any underlying feature changes; noisy for alerting unless decomposed.|If used, corroborate by evaluating underlying raw checks (`GetEncryptionStatus`, `GetTPMStatus`, `GetSecureBootStatus`, `GetBiometricCapabilities`) before rendering remediation advice.|Define whether Zima wants a single “posture score degraded” alert type at all; default recommendation for your module design is to avoid score-based alerts in favour of control-specific signals.|

## Implementation notes and provider summary

### Mapper and rules concerns for `disk_encryption_check`

Field paths that must survive parsing:

- Top-level: `platform`, `type`, `enabled`, `status`, `details` 
- Volume list (if present): `encrypted_volumes[].name`, `encrypted_volumes[].mount_point`, `encrypted_volumes[].encrypted`, `encrypted_volumes[].status` 

Null/empty/no-hit behaviour:

- macOS/Windows: “cannot determine / cannot query” becomes `status="unknown"` with a human-readable `details` string; treat this as **utility-only** output, not as a “disabled” finding. 
- Linux: empty `encrypted_volumes` causes `status="disabled"` with details “No LUKS/dm-crypt encrypted volumes detected”; because missing commands can cause empty detection, add a “Linux verification required” note in remediation UI or improve posture itself to emit `unknown` when prerequisites are missing. 

Privilege requirements:

- Windows explicitly records “requires running as administrator” for BitLocker WMI access. 
- macOS notes `fdesetup` may require admin and will return `unknown` otherwise. 
- Linux reads system files and shells out to utilities; if non-root cannot read certain sources, you may see false “disabled” rather than `unknown` in the current implementation. 

Deduplication keys (recommended for Zima correlation/dedup):

- `{entity_type=hostname, entity_id, signal_type, evidence.type}` as a natural key; include `platform` for diagnostics but avoid making it part of the dedup key if hostnames are unique per platform anyway. Evidence fields are stable enough to support audit and allow “signal resolved” when state flips. 

What belongs where:

- Provider client layer: execute the check via CLI/MCP/Go, enforce JSON formatting, capture execution errors (exit code/stdout/stderr) even if posture returns `status="unknown"` so you can troubleshoot privilege problems. (The upstream tool claims read-only and no network requests, which is operationally friendly for an endpoint agent.) 
- Module mapper: parse JSON, preserve all evidence fields above, and optionally attach `security_summary` if you call it as a second request. 
- Module rules: emit only the narrowly scoped `disk_encryption_disabled` when the provider explicitly claims disabled. Do not interpret Linux empty detections as high confidence without corroboration until you calibrate. 

### How posture wraps OS-native providers

The provider’s architecture diagram describes a layered model: a top-level CLI/MCP server exposing “security tools,” backed by OS-specific “inspectors” for darwin/windows/linux plus a “common” layer.  This matches your notion of per-OS native providers, but the specific Zima component names (`macos_native`, `windows_native`, `linux_native`) are not visible in the public artefacts and should be treated as **unknown mapping names** until you confirm internal code.

Given your modular Zima design, posture should be the **sole entry point** for any check it implements with a stable schema (disk encryption is a strong fit), and modules should consume OS-native providers directly only when posture lacks the required control (firewall, SIP, Gatekeeper, screen lock as of the evidenced surface). 

### Provider summary

Strongest signal types (or strongest utility contributions)

The strongest signal-producing contribution to your current target module set is disk encryption state via the explicit `enabled/status/type/platform` fields and per-volume evidence. 
Additionally, posture provides a security summary with an overall score and recommendations, which is useful as contextual enrichment for UI/triage but not ideal as a standalone signal source. 

What the provider should not be used for

Do not use the provider’s `overall_score` / `overall_status` as a direct severity rubric; it is an aggregate and does not map to your calibrated severity guide. 
Do not attempt to derive firewall/Gatekeeper/SIP/screen lock findings from posture as currently evidenced; those checks are not present in the provider-maintained surface. 

Installation / privilege / platform cautions

The provider is cross-platform and supports macOS, Windows, and Linux for disk encryption (FileVault/BitLocker/LUKS). 
Privilege limitations can convert “real state” into `unknown` (macOS/Windows) or into false “disabled” (Linux) depending on implementation. 

How to treat this provider in Zima

Treat posture as **signal-producing** for disk encryption (direct_signal_input), **enrichment-only** for security summary, and **out_of_scope** for firewall status and the macOS-specific controls you listed, unless your internal posture component adds those checks with a discoverable schema.

{
  "provider": "posture",
  "provider_category": "tools",
  "provider_role": "direct_signal_input",
  "module_mappings": [
    {
      "module": "disk_encryption_check",
      "provider_method": "get_encryption_status / inspector.GetEncryptionStatus() / CLI posture encryption",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": {
        "skip_if": [
          {
            "condition": "status == \"unknown\"",
            "reason": "visibility gap / privilege issue should not be emitted as 'disabled' security finding"
          }
        ]
      },
      "notes": "Cross-platform JSON schema exists; OS implementations vary in error behaviour (macOS/Windows -> unknown; Linux may appear disabled if tools/permissions prevent detection)."
    },
    {
      "module": "firewall_status",
      "provider_method": "unknown",
      "classification": "out_of_scope",
      "entity_types": ["hostname"],
      "gating_logic": "unknown",
      "notes": "No firewall check is present in the documented posture surface; requires extension or different provider."
    },
    {
      "module": "os_security",
      "provider_method": "get_security_summary / inspector.GetSecuritySummary() / CLI posture summary",
      "classification": "enrichment_only",
      "entity_types": ["hostname"],
      "gating_logic": {
        "do_not_alert_on": [
          "overall_score",
          "overall_status"
        ]
      },
      "notes": "Use summary for contextual enrichment; emit control-specific signals elsewhere."
    }
  ],
  "signal_contracts": [
    {
      "module": "disk_encryption_check",
      "source": "disk_encryption_check",
      "provider": "posture",
      "provider_method": "get_encryption_status / inspector.GetEncryptionStatus()",
      "signal_type": "disk_encryption_disabled",
      "category": "os_security",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "enabled == false AND status == \"disabled\"",
      "severity": "high",
      "severity_is_conditional": "no",
      "conditional_rule": "N/A",
      "evidence_fields": [
        "platform",
        "type",
        "enabled",
        "status",
        "details",
        "encrypted_volumes[].name",
        "encrypted_volumes[].mount_point",
        "encrypted_volumes[].encrypted",
        "encrypted_volumes[].status"
      ],
      "enrichment_fields": [
        "security_summary.overall_score",
        "security_summary.overall_status",
        "security_summary.recommendations[]"
      ],
      "summary_template": "Disk encryption is disabled on {hostname} ({platform}/{type}).",
      "evidence_status": "documented",
      "tags": ["misconfiguration", "pii_exposure"],
      "notes": "Top-level enabled=true on Windows means at least one protected volume, not necessarily full-disk coverage."
    }
  ],
  "confidence_guidance": [
    {
      "module": "disk_encryption_check",
      "signal_type_or_use_case": "disk_encryption_disabled",
      "source_reliability": "High when explicit disabled state is returned; OS-specific implementation differences can create unknown (macOS/Windows) or false disabled (Linux).",
      "freshness_considerations": "Point-in-time; encryption may transition (encrypting/decrypting) and reflect in status fields depending on OS.",
      "corroboration_rules": "Corroborate Linux disabled findings with additional OS-native validation; consider checking system volume encryption coverage on Windows using encrypted_volumes[].",
      "calibration_todo": "Decide policy scope (system volume vs all volumes). Improve Linux unknown/error reporting to avoid false disabled when prerequisites missing."
    },
    {
      "module": "firewall_status",
      "signal_type_or_use_case": "coverage gap",
      "source_reliability": "N/A",
      "freshness_considerations": "N/A",
      "corroboration_rules": "N/A",
      "calibration_todo": "Implement firewall checks inside posture with a documented schema or use OS-native providers directly."
    },
    {
      "module": "os_security",
      "signal_type_or_use_case": "security summary enrichment",
      "source_reliability": "Medium (derived/aggregated score); not suitable as primary alert source.",
      "freshness_considerations": "Score changes whenever any underlying control changes; can create alert churn.",
      "corroboration_rules": "If used in UI, corroborate with underlying check results for remediation accuracy.",
      "calibration_todo": "Decide whether to ever emit score-based alerts; default is to avoid them."
    }
  ]
}
