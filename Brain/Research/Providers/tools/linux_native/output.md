---
title: "output / tools / linux_native"
aliases: ["linux_native output", "linux_native signal registry"]
tags: [zima, research, outputs, signal-registry, tools, linux_native, graph_exclude]
type: provider_research_output
provider: linux_native
provider_category: tools
status: not_started
prompt_note: prompt.md
provider_folder: linux_native.md
obsidianUIMode: preview
kind: artifact
llm_include: false
code_scope: backend
---
# linux_native provider integration for Zima

## Research scope and provider model

The **linux_native** provider is a **local OS-native interface**: it executes distro-native commands and reads local configuration/state files to produce posture and inventory observations. Its outputs are therefore **high-fidelity but highly environment-dependent** (distro family, init system, installed tooling, privileges, and host hardening choices). 

Key design implications for Zima:

The provider does **not** have “endpoints” in the API sense; its “surface area” is the set of **CLI commands** and **files** Zima reads. For scripting, both `lsblk` and `findmnt` explicitly warn that **default output is subject to change**, so Zima should always request specific columns and prefer machine-readable formats (`--json` / `--pairs`) when available. 

Distro-family branching should be based on `/etc/os-release` fields `ID` and (especially) `ID_LIKE`, where `ID_LIKE` is explicitly intended as the fallback signal for “packaging and programming interfaces” compatibility. 

The expected module relationship is:

linux_native = raw collector (commands/files)
posture provider = abstraction layer (higher-level posture concepts mapped from linux_native observations)

This matches the division implied by the command/file nature of the provider and the need to normalise wildly different distro behaviours before producing durable signals. 

## Tool surface appendix

This appendix is organised by **capability** and then by **command/artifact**, with per-distro notes where relevant. For every item, “Trigger status” indicates whether the signal logic is **documented**, **derived from documented fields**, **inferred from examples**, or **unclear**.

### Distro detection and normalisation boundary

**Artifact: `/etc/os-release` (fallback `/usr/lib/os-release`)**

Invocation:

- Read `/etc/os-release` if present; otherwise read `/usr/lib/os-release` (and do **not** merge). 

Format/parsing:

- Newline-separated `KEY=VALUE` assignments; comments start with `#`; no shell expansion; quoting rules apply. 
- Keys needed for Zima branching:
    - `ID` (lowercase OS identifier) 
    - `ID_LIKE` (space-separated “related” IDs; intended for scripts when `ID` is not recognised) 
    - `VERSION_ID`, `PRETTY_NAME` for enrichment and reporting 

Privilege: unprivileged read is typically sufficient (file is meant to be available early in boot). 

Edge cases:

- Rolling releases may omit `VERSION_ID`; consumers must not rely on it always being present. 

Mapper note (recommended normalised fields):

- `os_release.id`, `os_release.id_like[]`, `os_release.version_id`, `os_release.pretty_name`

Trigger status: **documented** (file format + semantics). 

### Disk encryption

Zima objective: determine if the **root filesystem** (`/`) sits on an encrypted volume (LUKS / dm-crypt). The safest path is: identify root mount source, then trace underlying block stack for a `crypto_LUKS` layer or an active `crypt` target mapping.

**Command: `findmnt` (root mount source-of-truth)**

Suggested invocation (all distros):

- `findmnt -J -o SOURCE,TARGET,FSTYPE,OPTIONS -T /`

Relevant output:

- `-T, --target path` resolves the filesystem for a path and walks upward if the path is not itself a mountpoint. 
- `-o, --output` defines output columns; required for stable script parsing because default output is subject to change. 
- `-J, --json` JSON output. 

Privilege: generally unprivileged, since it reads kernel mount tables (e.g., `/proc/self/mountinfo`) by default. 

Edge cases:

- `SOURCE` may be a device path, LABEL/UUID form, or something like `overlay`/`tmpfs` depending on runtime context; treat such cases as “encryption status unclear” rather than forcing a false negative. 

Trigger status: **documented** for the inputs you rely on (`SOURCE`, `TARGET`, `FSTYPE`, JSON mode). 

**Command: `lsblk -f` (filesystem + block relationship view)**

Core documentation constraints:

- `lsblk` warns default output is subject to change; scripts should always set `--output`. 
- `-f, --fs` is equivalent to requesting filesystem columns including `NAME`, `FSTYPE`, and mountpoint information (Ubuntu manpage shows `MOUNTPOINT`; newer man7 version highlights `MOUNTPOINTS` for multi-mount). 
- `-J, --json` exists and is recommended for machine processing when paired with explicit columns. 
- `MOUNTPOINTS` exists specifically because block device ↔ filesystem mount relationships are not one-to-one; `MOUNTPOINTS` may be multi-line. 

LUKS detection string:

- Vendor guidance shows `lsblk -f` displays `FSTYPE` of **`crypto_LUKS`** for the encrypted device layer after setting up LUKS. 

Suggested invocation for Zima (stable parsing):

- `lsblk --json --output NAME,TYPE,FSTYPE,MOUNTPOINTS,UUID,PKNAME --tree`
    - Rationale: explicit columns + JSON + tree to retain parent/child relationships. 

Privilege:

- If `lsblk` cannot read udev metadata (or is compiled without udev support), it may need to read filesystem signatures directly from block devices, and then **root permissions are necessary**. 

Edge cases:

- Root filesystem may be on LVM-on-LUKS or Btrfs subvolumes; you should not assume the `/` mount’s `FSTYPE` itself will be `crypto_LUKS` (it is often `ext4`/`xfs`/`btrfs`). The detection requires tracing to parents/holders. The need for `MOUNTPOINTS` and tree structure is explicitly called out by `lsblk`. 

Trigger status:

- “`crypto_LUKS` in FSTYPE indicates LUKS layer” is **inferred from vendor example documentation** (not a manpage guarantee). 
- “Use explicit columns / JSON for stable scripts” is **documented**. 

**Command: `cryptsetup status <name>` (active mapping properties)**

What it returns (evidence fields available):

- Red Hat documentation shows `cryptsetup status` prints:
    - Mapping active line (`/dev/mapper/<name> is active...`)
    - `type` (e.g., `LUKS2`)
    - `cipher`
    - `keysize`
    - `key location`
    - `device` and sometimes `sector size`, `offset`, `size`, `mode` 

Suggested use in Zima:

- Only call `cryptsetup status` when you already identified a relevant `/dev/mapper/<name>` to inspect (e.g., via tracing the root mount source or via `dmsetup ls --target crypt`). 

Privilege:

- Not explicitly stated in the referenced docs; in practice, mapping inspection frequently requires elevated permissions on hardened hosts. Treat permission failure as a collection limitation, not “unencrypted”. (Privilege requirement: **unclear** in primary docs.) 

Trigger status: output field names are **inferred from examples** (vendor docs), not specified as a strict schema. 

**Command: `dmsetup ls --target crypt` and `dmsetup table --target crypt` (device-mapper truth)**

Capabilities:

- `dmsetup ls --target target_type` lists devices that have at least one target of the specified type. 
- `dmsetup table --target target_type` prints the device-mapper table; for `crypt` targets, real encryption keys are suppressed unless `--showkeys` is used. 

When to prefer over `lsblk` for encryption detection:

- Prefer `dmsetup` when:
    - You need a definitive yes/no that a mapping is a `crypt` target (device-mapper layer), independent of filesystem probing.
    - `lsblk` output is incomplete due to udev/sig-probing limitations or privileges. 

Privilege:

- Not explicitly stated in the man page sections captured; practically, dmsetup queries are typically privileged. Treat privilege requirement as **unclear** and handle failures gracefully. 

Trigger status: `--target` behaviour and table semantics are **documented**. 

### Firewall status

Zima objective: determine if a host firewall is active/configured using distro-preferred tooling first, then fall back to netfilter raw inspection.

**Debian/Ubuntu primary: `ufw`**

Documented behaviour that matters for Zima:

- `ufw status` shows firewall status and rules; `status verbose` adds extra information. 
- `ufw status` is only “basic”; it does not show rules from `/etc/ufw` rules files. For complete state, `ufw show raw` shows tables using `iptables -n -L -v -x -t <table>` (and `ip6tables` similarly). 

Output strings (“Status: active/inactive”):

- Not present in the `ufw(8)` man page text captured here; these strings are commonly observed in `ufw status` output examples and operational guides, so treat string matching as **inferred from examples** rather than manpage-guaranteed. (Implementation should accept variations.) 

Privilege:

- `ufw` operations that alter state require elevated privileges; simple `status` may be unprivileged on some systems but should be assumed to potentially require sudo in hardened environments (privilege requirement for `status`: **unclear**). 

**RHEL/Fedora primary: `firewall-cmd` (firewalld)**

Documented behaviours:

- `firewall-cmd --state` checks whether firewalld is running and prints the state to STDOUT; it returns exit code 0 if active, otherwise non-zero error codes (including `NOT_RUNNING`). 
- Observed output strings include `running` and `not running` (project documentation and wiki examples). 
- `firewall-cmd --list-all` lists everything added/enabled for the (default or specified) zone/policy. 

Privilege:

- Firewalld management is generally privileged; treat permission failures as “status unknown” rather than “not running” unless `--state` definitively indicates non-running. (Privilege: partially documented via behaviour, not a strict requirement statement.) 

**Generic fallback: nftables + iptables**

nftables (preferred modern raw inspection):

- `nft list ruleset` prints the entire ruleset; output is designed to be reusable as input to `nft -f` (iptables-save equivalent). 
- `nft -j` provides JSON output; schema references `libnftables-json(5)`. 
- Important semantic warning: flushing the ruleset results in an empty ruleset where “no packet filtering will happen anymore” and the kernel accepts packets—useful as a conceptual baseline for “empty ruleset == not filtering”. 

iptables (legacy / compatibility):

- `iptables-save` is explicitly described as dumping tables in an “easily parseable format”, making it better for scripting than parsing `iptables -L` output. 

### OS version and kernel

**`uname -r` kernel release string**

- GNU coreutils documentation describes `uname` as printing “system information” including `kernel-release`, and lists `kernel-release` among standard fields (the `-r`/`--kernel-release` selection). 

For Zima:

- Treat `uname -r` as “running kernel release string”; do not assume it matches upstream kernel.org numbering because distro kernels append build metadata. (Comparisons should be distro-aware.) 

“How to compare against latest available kernel” (implementation guidance):

- This is **not directly standardised** by a single Linux interface. The robust approach for Zima is to compare:
    - running kernel (`uname -r`)
    - versus **available kernel updates in the distro package manager** (APT/DNF/pacman)
        This makes the comparison align with what the host can actually install (as opposed to upstream kernel.org releases). (This strategy is a Zima design choice; “latest kernel” definition is inherently environment-specific.) 

### Updates and patch status

**Debian/Ubuntu: APT**

Upgradable packages:

- `apt list --upgradable` output format is not specified in the sources gathered here as a stable schema; community guidance often parses package name as the substring before the first `/` and skips the first header line. Treat this as **inferred from examples** and build parsers defensively. 

Security-focused preview:

- Ubuntu documents that `unattended-upgrades` performs the equivalent of `apt update` + `apt upgrade`, controlled via `/etc/apt/apt.conf.d/20auto-upgrades` keys:
    - `APT::Periodic::Update-Package-Lists`
    - `APT::Periodic::Unattended-Upgrade`
        where `0` disables and `1` runs daily. 
- Ubuntu further documents that `apt-daily.timer` and `apt-daily-upgrade.timer` trigger these actions via `/usr/lib/apt/apt.systemd.daily`. 
- Example logs in Ubuntu docs show `--dry-run` behaviour (no real actions) and include lines like “Packages that will be upgraded:” which can be parsed to determine what security-origin updates would apply under the current unattended-upgrades policy. 

**RHEL/Fedora: DNF**

Updates available:

- `dnf check-update` is documented to exit with:
    - `100` when updates are available
    - `0` when none are available
    - `1` on error 

Security updates available:

- Red Hat documents listing “available security updates not installed” using:
    - `dnf updateinfo list updates security`
        and shows advisory-like output lines with package NEVRAs. 

**Arch: pacman**

Upgradable packages:

- pacman query filter `-u, --upgrades` restricts output to packages that are out of date; it works best when sync DB is refreshed. 
- `-q, --quiet` reduces output (e.g., for bare query, only package names rather than names+versions). 

### Auto-updates

**Debian/Ubuntu: unattended-upgrades**

- Ubuntu explicitly identifies:
    - `/etc/apt/apt.conf.d/20auto-upgrades` as the enable/period control
    - `/etc/apt/apt.conf.d/50unattended-upgrades` as behaviour/options
    - default daily runs, and logs under `/var/log/unattended-upgrades` 

**RHEL/Fedora: dnf-automatic**

- DNF documentation: if no config path provided, `/etc/dnf/automatic.conf` is used; and the systemd timer `dnf-automatic.timer` (and variants) run the tool. 
- RHEL documents enabling timer units and names `dnf-automatic-download.timer`, `dnf-automatic-install.timer`, `dnf-automatic-notifyonly.timer`, `dnf-automatic.timer`. 

**Service enablement detection: `systemctl is-enabled`**

- systemd documents `systemctl is-enabled` output values and exit codes (e.g., `enabled`, `disabled`, `masked`, `not-found`). 

### Installed software inventory

This surface is primarily **utility-only** for your stated build intent.

**Debian/Ubuntu**

- `dpkg-query -W` supports a custom format string (example: `${Package}\t${Version}\n`) allowing stable parsing vs `dpkg -l`’s columnar output (format-string support is documented by dpkg-query manpages; exact variable names are part of dpkg-query’s contract). 

**RHEL/Fedora**

- rpm supports query formatting via `--queryformat` (rpm’s queryformat capability is documented; however, the exact format string you choose is yours). 

**Arch**

- `pacman -Q` operates on the local package database; use `-q` if you need a clean names-only list. 

### SSH configuration

**Artifact: `/etc/ssh/sshd_config` plus included drop-ins**

File format (critical for “effective config” determination):

- `sshd_config` is keyword-argument pairs, one per line; **first obtained value is used** unless noted; lines beginning with `#` and empty lines are comments. 
- `Include` supports multiple paths and globs expanded and processed in lexical order; can appear inside `Match` blocks. 
- `Match` blocks override global settings under satisfied criteria; if a keyword appears in multiple satisfied Match blocks, only the first instance applies. 

Directives needed by your target logic:

- `PermitRootLogin` accepted values are `yes`, `prohibit-password`, `forced-commands-only`, or `no`; default is `prohibit-password`. 
- `PasswordAuthentication` default is `yes`. 
- `PubkeyAuthentication` default is `yes`. 

Trigger status: **documented** for parsing rules and directive semantics. 

## Module mapping table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|os_security|direct_signal_input|sshd_config_read|`/etc/ssh/sshd_config` + `Include` targets|direct_signal_input|hostname|Parse `sshd_config` as key-value lines; ignore `#` comments; expand `Include` globs lexicographically; apply “first value wins” and then apply `Match` overrides for effective evaluation.||Prefer computing an “effective” view per directive, but retain raw lines and include-resolution for audit/debug.|
|os_security|utility_only|os_release_read|`/etc/os-release` (fallback `/usr/lib/os-release`)|utility_only|hostname|Use `ID` and `ID_LIKE` to branch behaviour and label enrichment.||Not a signal by itself; enables correct distro branching (especially for package/firewall tooling).|
|patch_status|direct_signal_input|dnf_check_update|`dnf check-update`|direct_signal_input|hostname|Only for RHEL/Fedora-like (`ID_LIKE` contains `rhel`/`fedora`): interpret exit code `100` as updates available.||Exit codes are stable and script-friendly; output content is unstructured but can be stored as evidence.|
|patch_status|direct_signal_input|dnf_updateinfo_security|`dnf updateinfo list updates security`|direct_signal_input|hostname|Only if repo metadata supports advisories: use non-empty output as “security updates pending”.||Advisory output gives stronger evidence than generic updates.|
|patch_status|direct_signal_input|apt_upgradable_list|`apt list --upgradable`|direct_signal_input|hostname|Only for Debian-like: parse defensively; treat as “updates pending” if at least one package entry is present after header.||Output format is not guaranteed in the sources here; treat parser as best-effort, not strict.|
|patch_status|direct_signal_input|unattended_upgrades_dry_run|`unattended-upgrades --dry-run` (if present)|direct_signal_input|hostname|If available, treat listed “Packages that will be upgraded” under current policy as “security/allowed-origin updates pending”.||Favoured for security-update visibility because it reflects configured origins and policy.|
|patch_status|enrichment_only|apt_auto_upgrades_config|`/etc/apt/apt.conf.d/20auto-upgrades`|direct_signal_input|hostname|Parse `APT::Periodic::Update-Package-Lists` and `APT::Periodic::Unattended-Upgrade`: 0 disables, 1 means daily, N means every N days.||Used to emit `automatic_updates_disabled` when values are 0 (see signal table).|
|patch_status|direct_signal_input|dnf_automatic_config + systemctl|`/etc/dnf/automatic.conf`; `systemctl is-enabled dnf-automatic*.timer`|direct_signal_input|hostname|For RHEL/Fedora-like, read config path and check timer enablement state via `systemctl is-enabled`.||Many deployments use timer variants; treat any enabled install/download timer as “auto-updates enabled”.|
|patch_status|direct_signal_input|pacman_upgrades|`pacman -Qu` (or `pacman -Quq`)|direct_signal_input|hostname|For Arch-like, treat non-empty output as pending updates; use `-q` for stable names-only.||Arch has no default auto-update; patch_status can still report pending updates.|
|disk_encryption_check|direct_signal_input|root_mount_source|`findmnt -J -o SOURCE,TARGET,FSTYPE,OPTIONS -T /`|direct_signal_input|hostname|Identify root mount source (`SOURCE`) for `/`; if root is overlay/tmpfs/etc, mark encryption status as unknown.||This is the anchor for “root sits on encrypted volume” evaluation.|
|disk_encryption_check|direct_signal_input|lsblk_block_stack|`lsblk --json --output NAME,TYPE,FSTYPE,MOUNTPOINTS,UUID,PKNAME --tree` (or `lsblk -f`)|direct_signal_input|hostname|Trace from root mount device down to parents: presence of `FSTYPE=crypto_LUKS` indicates LUKS layer; use tree/parent fields and `MOUNTPOINTS` to handle multi-mount.||Beware privilege/udev constraints: root may be required in some environments.|
|disk_encryption_check|enrichment_only|dmsetup_crypt_mappings|`dmsetup ls --target crypt` and optionally `dmsetup table --target crypt`|enrichment_only|hostname|Use to corroborate that the relevant mapper device is a `crypt` target; do not treat failure as “unencrypted”.||Stronger than filesystem probing; keys are suppressed by default for crypt targets.|
|disk_encryption_check|enrichment_only|cryptsetup_status_mapping|`cryptsetup status <name>`|enrichment_only|hostname|If mapper name identified, parse `type/cipher/keysize/device` fields for evidence.||Output is example-driven; treat as best-effort text parse, not strict schema.|
|firewall_status|direct_signal_input|ufw_status|`ufw status` / `ufw status verbose`|direct_signal_input|hostname|If `ufw` exists: treat “Status: active” as firewall active; “Status: inactive” as not active; parse verbose default policies when available.||Manpage documents status concept but not exact “Status:” strings, so string match logic must be tolerant.|
|firewall_status|direct_signal_input|firewall_cmd_state|`firewall-cmd --state` and `firewall-cmd --list-all`|direct_signal_input|hostname|If firewalld tooling exists: `--state` prints running/not running; treat non-running as firewall inactive; capture `--list-all` output for evidence.||`--list-all` output is structured text; store raw for audit.|
|firewall_status|direct_signal_input|nft_ruleset_or_iptables_save|`nft -j list ruleset` (preferred) else `iptables-save`|direct_signal_input|hostname|If no ufw/firewalld: treat empty ruleset (no tables/chains) as no filtering; otherwise classify as “configured”.||nft output can be JSON; iptables-save is “easily parseable” and better than `iptables -L` parsing.|

## Signal contract table

Only standalone signals that should actually be emitted are included. All signals use `entity_type=hostname` because these are **host posture** findings.

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|disk_encryption_check|disk_encryption_check|linux_native|lsblk_block_stack + root_mount_source|root_filesystem_unencrypted|os_security|high|yes|If root source cannot be mapped to a block device stack (e.g., overlay), do not emit; instead record “unknown”.|hostname|true_finding|Using `findmnt -T /` get `SOURCE` for `/`. Trace the corresponding device in `lsblk` tree: emit if **no ancestor device has `FSTYPE` equal to `crypto_LUKS`** (and no dm-crypt mapping can be corroborated).|`findmnt: SOURCE,FSTYPE,OPTIONS for /`; `lsblk columns: NAME,TYPE,FSTYPE,MOUNTPOINTS,PKNAME,UUID` for traced path; raw stdout/stderr|`dmsetup ls --target crypt` output; `cryptsetup status <name>` fields `type,cipher,keysize,device` if available|“Root filesystem on {hostname} is not backed by LUKS/dm-crypt encryption.”|derived||`crypto_LUKS` string is vendor-example-based; treat as robust but still environment-dependent.|
|firewall_status|firewall_status|linux_native|ufw_status|host_firewall_inactive|network_security|high|yes|If ufw exists, use ufw as authority; only fall back to nft/iptables if ufw not installed.|hostname|true_finding|Emit when ufw status output indicates inactive (string match tolerant), or when ufw is installed but disabled (no boot enablement is a separate enrichment concern).|raw `ufw status` stdout; raw `ufw status verbose` stdout; command exit code|If needed, store `ufw show raw` output for full rules insight.|“Host firewall on {hostname} is not active (ufw inactive).”|inferred||Exact “Status:” string is not specified in manpage; treat as example-driven parsing.|
|firewall_status|firewall_status|linux_native|firewall_cmd_state|host_firewall_inactive|network_security|high|yes|If firewalld tooling exists, prefer its own `--state` output; only fall back to nft/iptables when firewalld is not present.|hostname|true_finding|Emit when `firewall-cmd --state` prints `not running` and/or returns non-zero (NOT_RUNNING), and firewalld is therefore not active.|`firewall-cmd --state` stdout + exit code; `firewall-cmd --list-all` stdout for evidence|`firewall-cmd --get-active-zones` could be added as enrichment if needed (optional).|“Host firewall on {hostname} is not active (firewalld not running).”|documented||Prefer exit-code-based determination where possible to avoid localisation/string issues.|
|firewall_status|firewall_status|linux_native|nft_ruleset_or_iptables_save|host_firewall_unconfigured|network_security|high|yes|Only run if neither ufw nor firewalld is present; interpret “empty ruleset” conservatively as unconfigured.|hostname|true_finding|Emit when `nft list ruleset` yields an effectively empty ruleset (no tables/chains/rules), or `iptables-save` shows only default ACCEPT policies with no added rules (heuristic).|raw `nft -j list ruleset` JSON (preferred) or raw `nft list ruleset`; raw `iptables-save` output|Store which fallback path was used; include stderr on failure.|“Host firewall on {hostname} appears unconfigured (no nftables/iptables ruleset).”|derived||nftables manpage semantics support interpreting empty ruleset as “no filtering”, but iptables-save emptiness is heuristic.|
|os_security|os_security|linux_native|sshd_config_read|ssh_root_login_permitted|account_security|high|yes|Severity high when `PermitRootLogin yes`; reduce to medium when `prohibit-password` or `forced-commands-only`.|hostname|true_finding|Parse effective sshd config: emit when `PermitRootLogin` resolves to `yes`, `prohibit-password`, or `forced-commands-only` (anything except `no`).|Effective `PermitRootLogin` value; raw lines that set it (file + line refs in evidence); include-resolution list|Also store `PasswordAuthentication` and whether `Match` blocks affect root logins.|“SSH server on {hostname} permits direct root login (PermitRootLogin={value}).”|documented||This is a pure config-driven posture signal; does not assert exposure to the internet.|
|os_security|os_security|linux_native|sshd_config_read|ssh_password_authentication_enabled|account_security|medium|yes|If combined with `PermitRootLogin yes`, treat as high-risk compound posture (separate correlation layer).|hostname|true_finding|Emit when effective `PasswordAuthentication` resolves to `yes`.|Effective `PasswordAuthentication`; raw lines setting it; include-resolution list|`PubkeyAuthentication` value for context.|“SSH server on {hostname} allows password authentication (PasswordAuthentication=yes).”|documented||Consider suppressing if host is intentionally isolated; best handled via policy layer rather than provider logic.|
|patch_status|patch_status|linux_native|apt_auto_upgrades_config|automatic_updates_disabled|os_security|medium|yes|On Ubuntu/Debian: if either periodic value is 0, treat as disabled; if both are non-zero, do not emit.|hostname|true_finding|Emit when `/etc/apt/apt.conf.d/20auto-upgrades` has `APT::Periodic::Update-Package-Lists "0";` OR `APT::Periodic::Unattended-Upgrade "0";`.|Parsed values + raw file contents (or specific matched lines)|Enrich with timer state `apt-daily.timer` / `apt-daily-upgrade.timer` if collected.|“Automatic APT updates on {hostname} are disabled (20auto-upgrades).”|documented||Ubuntu docs provide explicit control semantics for these values.|
|patch_status|patch_status|linux_native|dnf_automatic_config + systemctl|automatic_updates_disabled|os_security|medium|yes|On RHEL/Fedora: if all `dnf-automatic*.timer` units are not enabled (`disabled`/`not-found`), treat as disabled.|hostname|true_finding|Emit when `systemctl is-enabled dnf-automatic.timer` and the install/download variants are not enabled (`enabled`/`enabled-runtime`), or are `not-found`.|`systemctl is-enabled` outputs + exit codes; timer unit names checked|`/etc/dnf/automatic.conf` presence and key settings (enrichment).|“Automatic DNF updates on {hostname} are not enabled (dnf-automatic timers).”|derived||Exact timer choice varies; treat any enabled variant as “auto update present”.|
|patch_status|patch_status|linux_native|dnf_updateinfo_security|security_updates_pending|os_security|high|no|unknown|hostname|true_finding|Emit when `dnf updateinfo list updates security` returns at least one advisory/package entry (non-empty output).|Raw stdout + exit code; optionally parsed list of advisory IDs and packages|Correlate with `dnf check-update` for total updates pending.|“Security updates are available on {hostname} (DNF advisories pending).”|documented||Stronger claim than “updates pending” because it is security-advisory scoped.|
|patch_status|patch_status|linux_native|unattended_upgrades_dry_run|security_updates_pending|os_security|high|yes|Only emit if unattended-upgrades is installed and configured; otherwise fall back to generic pending updates.|hostname|true_finding|Emit when unattended-upgrades dry-run output indicates packages would be upgraded under allowed origins (parse “Packages that will be upgraded:” style log lines).|Raw dry-run stdout/stderr; exit code|Store allowed origins section if present.|“Security/allowed-origin updates are pending on {hostname} (unattended-upgrades dry-run).”|inferred||Output is log-like, not an API schema; parsing must be tolerant.|
|patch_status|patch_status|linux_native|dnf_check_update / apt_upgradable_list / pacman_upgrades|system_updates_pending|os_security|medium|yes|If security-scoped signal is available (dnf updateinfo / unattended dry-run), optionally downgrade or suppress this generic signal to avoid duplication.|hostname|true_finding|Emit when: DNF `check-update` exit code is 100; OR APT upgradable list has entries; OR pacman upgrades output non-empty.|Command stdout + exit code; optionally parsed package name list|Include OS release identifiers and tool path used.|“System updates are pending on {hostname}.”|documented / inferred (depends)||DNF exit code rule is documented; APT and pacman parsing is more output-dependent.|

## Severity and confidence guidance

### Severity rules

The severity assignments follow your calibration guide and your first-pass posture expectations:

Disk encryption missing on root is **high** because it materially increases impact of physical compromise and offline disk access; it matches your provided first-pass severity. 

Firewall inactive/unconfigured is **high** because it is a direct network hardening control being absent, matching your first-pass severity “firewall not active = high”. The provider evidence distinguishes “service not running” (`firewall-cmd --state`) from “no netfilter ruleset” (nft/iptables). 

Root SSH permitted is **high** when `PermitRootLogin yes` because it knowingly enables direct remote superuser login; the config semantics and accepted values are explicitly documented. The severity is conditional because `prohibit-password` is less severe than `yes` (still allows root but not via password). 

PasswordAuthentication enabled is **medium** because it increases brute-force and credential-guessing exposure but is not itself credential exposure; severity is conditional when combined with `PermitRootLogin yes` (compound posture). 

Automatic updates disabled is **medium** per your first-pass expectation; the provider evidence is explicit config values (APT periodic) and explicit timer enablement (`systemctl is-enabled`). 

Security updates pending is **high** because it indicates known security advisories/patches not yet applied (DNF security advisories; unattended-upgrades policy preview), aligning with “kernel significantly out of date = high” posture logic even though the provider is not itself proving exploitation. 

### Confidence guidance table

|module|signal_type_or_use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|disk_encryption_check|root_filesystem_unencrypted|High when root mount is a normal block device and both `findmnt` and `lsblk` can be read with full context; lower if privilege/udev limitations prevent stack tracing.|Disk encryption state is relatively static, but at runtime mapper devices can change (e.g., rescue environments). `lsblk` warns it can run before udev has complete info.|Corroborate `lsblk` result with `dmsetup ls --target crypt` and/or `cryptsetup status` when possible.|Add a policy for “unknown” outcomes (overlay root, containers, permission denied) so you don’t emit false “unencrypted”.|
|firewall_status|host_firewall_inactive / unconfigured|High for `firewall-cmd --state` because it is the daemon’s own status API with exit semantics; medium for ufw due to string-match parsing; medium for nft/iptables heuristics.|Firewall state changes quickly; treat observations as point-in-time.|Corroborate service state (ufw/firewalld) with raw ruleset evidence (`firewall-cmd --list-all`, `nft list ruleset`, `iptables-save`).|Calibrate “empty ruleset” heuristics to reduce false positives on minimal baseline firewall configs (especially iptables defaults).|
|os_security|ssh_root_login_permitted|High because it is direct config evidence with well-defined permitted values; complexity comes from `Include` + `Match` evaluation.|Config changes are relatively static; but can be updated frequently by config management.|Corroborate by storing resolved effective value and raw file fragments that set it; optionally verify with sshd runtime introspection in a future enhancement (outside current scope).|Implement and test a correct `Match` evaluation model; decide if Zima emits “global config” findings when Match blocks partially override.|
|patch_status|security_updates_pending|High on RHEL/Fedora when based on `dnf updateinfo ... security` because it enumerates security advisories; medium on Debian/Ubuntu when inferred from unattended-upgrades dry-run logs.|Patch availability changes constantly; results are stale quickly. DNF check-update output is point-in-time; apt lists depend on prior repo refresh (not guaranteed here).|Corroborate by capturing tool exit codes (DNF 100) and storing raw output with timestamps; optionally run repo metadata refresh in provider client (policy decision).|Define when Zima should consider “pending updates” actionable (e.g., age threshold since last check) and whether to differentiate security vs non-security more strongly on Debian-like systems.|
|patch_status|automatic_updates_disabled|High when based on explicit config keys (APT periodic) or explicit timer enablement status (`systemctl is-enabled` output table + exit codes).|Config is relatively static; timers can be toggled.|Corroborate config-based disablement with timer status, since Ubuntu uses timers to trigger actions.|Decide whether Arch should emit this signal (default “no auto-updates” is common) or treat as policy-driven only.|

Suggested tags (2–5) per signal type (from your allowed list):

- root_filesystem_unencrypted: `["misconfiguration"]`
- host_firewall_inactive: `["misconfiguration", "open_port"]` (open_port as “risk of open exposure”, not literal scan evidence)
- host_firewall_unconfigured: `["misconfiguration", "open_port"]`
- ssh_root_login_permitted: `["misconfiguration"]`
- ssh_password_authentication_enabled: `["misconfiguration"]`
- automatic_updates_disabled: `["misconfiguration"]`
- security_updates_pending: `["misconfiguration"]`
- system_updates_pending: `["misconfiguration"]`

## Implementation notes and provider summary

### Implementation notes for `modules/*/mapper.py` and `modules/*/rules.py`

Distro detection strategy:

- Parse `/etc/os-release`:
    - Use `ID` as first choice.
    - If `ID` unrecognised, use `ID_LIKE` as documented fallback for scripts and build tooling. 
- Recommended branching rules:
    - Debian-like if `ID == "debian"` OR `"debian"` in `ID_LIKE`.
    - RHEL/Fedora-like if `"rhel"` or `"fedora"` in `ID`/`ID_LIKE`. 
    - Arch-like if `"arch"` in `ID`/`ID_LIKE`. 
- Persist `os_release.*` into evidence/enrichment so downstream correlation can understand what toolchain was used. 

Handling missing commands gracefully (recommended fallback chain for firewall):

- If `ufw` available → use `ufw status` / `ufw status verbose`. 
- Else if `firewall-cmd` available → use `firewall-cmd --state`, `--list-all`. 
- Else → use raw netfilter inspection:
    - Prefer `nft -j list ruleset` (JSON) when `nft` exists. 
    - Else use `iptables-save`. 

Sudo/privilege requirements (design guidance):

- Treat privilege as “best-effort escalation” rather than hard-failing modules:
    - `lsblk` may require root when udev metadata is unavailable and block probing is needed. 
    - `dmsetup`, `nft`, `iptables-save`, and `cryptsetup status` may fail without elevated rights on hardened systems (explicit privilege requirements are not fully documented in the cited sources; handle permission failure as “unknown/insufficient access”).
- In mapper design, capture:
    - `exit_code`
    - `stderr`
    - whether the command was executed with sudo
    - command path/version when easily available
        so the rules layer can suppress false negatives.

Parsing strategies (regex / structured parsing):

- Prefer **JSON output** when supported:
    - `lsblk --json` with explicit `--output` and tree to retain hierarchy. 
    - `findmnt -J` with explicit `-o` columns. 
    - `nft -j` for JSON ruleset. 
- When only text is available, parse using anchored patterns:
    - For `sshd_config`: ignore comment lines (`#`), parse `keyword argument` pairs, apply “first value wins” and `Include`/`Match` semantics. 
    - For `dnf check-update`: treat exit code `100` as authoritative, avoid parsing the list to decide “updates exist”. 
    - For `firewall-cmd --state`: prefer exit code + single-word output matching (`running`/`not running`). 
    - For APT: treat `apt list --upgradable` parsing as best-effort and store raw output; rely on unattended-upgrades dry-run for security-scoped insight where possible. 

Deduplication keys (practical defaults):

- Host posture signals: `dedup_key = (hostname, signal_type)`
- Add a “state discriminator” when it materially changes the meaning:
    - For ssh_root_login_permitted: include effective `PermitRootLogin` value.
    - For firewall signals: include selected firewall tool (`ufw` vs `firewalld` vs `nft/iptables`) and state (`running` vs `not running`) to prevent flapping dedup issues.

What belongs where:

- Provider client (linux_native):
    - Command execution, timeouts, PATH resolution, sudo strategy, capturing stdout/stderr/exit codes.
    - Basic distro detection and tool availability checks.
- Module mapper:
    - Parse command/file outputs into structured intermediate objects (device stacks, effective ssh config, updates lists).
- Module rules:
    - Emit signals based on those structured intermediate objects using the trigger conditions in the signal table.
- Correlation layer:
    - Compound logic (e.g., `PasswordAuthentication=yes` + `PermitRootLogin=yes` escalations; firewall inactive + open SSH port from a different module).

### Provider summary

Strongest signal contributions:

- Reliable **host posture** checks where the OS is the ground truth: disk encryption presence on the root stack (`lsblk` + `findmnt`), firewall daemon/ruleset state (`firewall-cmd`, `ufw`, `nft`), and SSH daemon hardening posture (`sshd_config`). 

What linux_native should not be used for:

- It should not be treated as a **threat intelligence** provider (no external adversary context).
- It should not be used to assert **internet exposure** directly (e.g., “root SSH exposed to public internet”) without additional network perimeter visibility; it only indicates local configuration. 

Installation / privilege / platform cautions:

- Highly distro-specific; tooling (`ufw` vs `firewalld` vs nftables/iptables) and update mechanisms differ materially.
- Command outputs are often not stable unless you explicitly request columns/structured output; both `lsblk` and `findmnt` warn about default-output instability. 
- Privilege issues can cause false negatives if not handled as “unknown” rather than “secure”. `lsblk` may require root on some systems to read filesystem types. 

Global classification recommendation:

- For the target modules listed, treat linux_native as **direct_signal_input** (posture checks) with a secondary **utility_only** role for inventory lists.

{
  "provider": "linux_native",
  "provider_category": "tools",
  "provider_role": "direct_signal_input for posture checks; utility_only for inventory",
  "module_mappings": [
    {
      "module": "os_security",
      "provider_role": "direct_signal_input",
      "provider_method": "sshd_config_read",
      "endpoint_or_artifact": "/etc/ssh/sshd_config (+Include targets)",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "Parse sshd_config ignoring # comments; expand Include globs; apply first-value-wins and Match override rules.",
      "citation_refs": ["turn13view0", "turn9view4", "turn10view2", "turn11view0"],
      "notes": "Store both effective directives and raw resolution trace for audit."
    },
    {
      "module": "patch_status",
      "provider_role": "direct_signal_input",
      "provider_method": "dnf_check_update",
      "endpoint_or_artifact": "dnf check-update",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "RHEL/Fedora-like only; exit code 100 => updates pending.",
      "citation_refs": ["turn8view5", "turn14view0"],
      "notes": "Prefer exit-code logic over parsing output."
    },
    {
      "module": "disk_encryption_check",
      "provider_role": "direct_signal_input",
      "provider_method": "root_mount_source + lsblk_block_stack",
      "endpoint_or_artifact": "findmnt -J ... -T /; lsblk --json --output ... --tree",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "Anchor on root SOURCE; traverse to detect crypto_LUKS/dm-crypt ancestry.",
      "citation_refs": ["turn39view2", "turn9view0", "turn8view0", "turn40search1"],
      "notes": "Treat permission failures as unknown, not unencrypted."
    },
    {
      "module": "firewall_status",
      "provider_role": "direct_signal_input",
      "provider_method": "ufw_status/firewall_cmd_state/nft_ruleset_or_iptables_save",
      "endpoint_or_artifact": "ufw status; firewall-cmd --state; nft -j list ruleset; iptables-save",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "Prefer distro-native firewall tooling, then fallback to raw netfilter inspection.",
      "citation_refs": ["turn33view0", "turn29view0", "turn9view5", "turn7search1"],
      "notes": "Use tolerant parsing for ufw status strings."
    }
  ],
  "signal_contracts": [
    {
      "module": "disk_encryption_check",
      "source": "disk_encryption_check",
      "provider": "linux_native",
      "provider_method": "findmnt + lsblk (+optional dmsetup/cryptsetup)",
      "signal_type": "root_filesystem_unencrypted",
      "category": "os_security",
      "severity": "high",
      "severity_is_conditional": "yes",
      "conditional_rule": "Do not emit if root source is not a real block device stack (overlay/tmpfs/etc); record unknown instead.",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "No traced ancestor block device has FSTYPE == crypto_LUKS for the root filesystem path.",
      "evidence_fields": ["findmnt SOURCE/FSTYPE/OPTIONS", "lsblk NAME/TYPE/FSTYPE/MOUNTPOINTS/PKNAME/UUID", "raw stdout/stderr"],
      "enrichment_fields": ["dmsetup ls --target crypt", "cryptsetup status fields when available"],
      "summary_template": "Root filesystem on {hostname} is not backed by LUKS/dm-crypt encryption.",
      "evidence_status": "derived",
      "citation_refs": ["turn39view2", "turn9view0", "turn40search1"],
      "notes": "crypto_LUKS detection string is vendor-example-based; treat as robust but environment-dependent."
    },
    {
      "module": "firewall_status",
      "source": "firewall_status",
      "provider": "linux_native",
      "provider_method": "firewall-cmd --state OR ufw status OR nft/iptables fallback",
      "signal_type": "host_firewall_inactive",
      "category": "network_security",
      "severity": "high",
      "severity_is_conditional": "yes",
      "conditional_rule": "Prefer authoritative tool state (ufw/firewalld) when present; fallback only if tooling absent.",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "firewall-cmd --state indicates NOT_RUNNING/not running OR ufw output indicates inactive OR empty nftables/iptables ruleset heuristic.",
      "evidence_fields": ["tool stdout", "exit codes", "raw ruleset snapshots"],
      "enrichment_fields": ["firewall-cmd --list-all", "ufw status verbose", "ufw show raw"],
      "summary_template": "Host firewall on {hostname} is not active.",
      "evidence_status": "documented/derived",
      "citation_refs": ["turn29view0", "turn31view0", "turn33view0", "turn9view5", "turn7search1"],
      "notes": "nftables emptiness semantics are clearer than iptables heuristics."
    },
    {
      "module": "os_security",
      "source": "os_security",
      "provider": "linux_native",
      "provider_method": "sshd_config_read",
      "signal_type": "ssh_root_login_permitted",
      "category": "account_security",
      "severity": "high",
      "severity_is_conditional": "yes",
      "conditional_rule": "High when PermitRootLogin=yes; medium when prohibit-password or forced-commands-only.",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "Effective PermitRootLogin != no",
      "evidence_fields": ["effective PermitRootLogin", "raw config lines + include resolution"],
      "enrichment_fields": ["PasswordAuthentication", "Match block context"],
      "summary_template": "SSH permits root login on {hostname} (PermitRootLogin={value}).",
      "evidence_status": "documented",
      "citation_refs": ["turn13view0", "turn11view0", "turn9view4"],
      "notes": "Does not assert internet exposure; only local config posture."
    },
    {
      "module": "patch_status",
      "source": "patch_status",
      "provider": "linux_native",
      "provider_method": "dnf updateinfo OR unattended-upgrades dry-run",
      "signal_type": "security_updates_pending",
      "category": "os_security",
      "severity": "high",
      "severity_is_conditional": "yes",
      "conditional_rule": "Only emit from security-scoped mechanisms (dnf updateinfo security or unattended-upgrades policy preview).",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "Non-empty security advisory/update listing.",
      "evidence_fields": ["raw stdout", "exit code", "parsed advisory/package list if possible"],
      "enrichment_fields": ["generic updates pending signals as separate outputs"],
      "summary_template": "Security updates are available on {hostname}.",
      "evidence_status": "documented/inferred",
      "citation_refs": ["turn19view0", "turn18view0"],
      "notes": "Debian-like security parsing is log-based, not a strict schema."
    }
  ],
  "confidence_guidance": [
    {
      "module": "disk_encryption_check",
      "signal_type_or_use_case": "root_filesystem_unencrypted",
      "source_reliability": "High when root mount is a real block stack and lsblk has full visibility; lower on permission/udev limitations.",
      "freshness_considerations": "Mostly static but runtime contexts (containers/overlay roots) can change the meaning of SOURCE.",
      "corroboration_rules": "Corroborate lsblk ancestry with dmsetup crypt targets and cryptsetup status when possible.",
      "calibration_todo": "Define strict unknown-handling rules to prevent false negatives."
    },
    {
      "module": "firewall_status",
      "signal_type_or_use_case": "host_firewall_inactive",
      "source_reliability": "High for firewall-cmd --state; medium for ufw string parsing; medium for iptables/nft heuristics.",
      "freshness_considerations": "Firewall status can change quickly; treat as point-in-time.",
      "corroboration_rules": "Store both daemon state and full ruleset snapshot where feasible.",
      "calibration_todo": "Tune empty-ruleset heuristics to avoid false positives on minimal baselines."
    },
    {
      "module": "os_security",
      "signal_type_or_use_case": "ssh_root_login_permitted",
      "source_reliability": "High; derived from documented sshd_config semantics.",
      "freshness_considerations": "Config changes whenever managed; capture file timestamps and include resolution.",
      "corroboration_rules": "Preserve effective value plus raw lines to support audits.",
      "calibration_todo": "Implement Match evaluation and decide on policy for partial overrides."
    }
  ]
}
