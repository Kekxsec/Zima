---
title: "output / tools / lynis"
aliases: ["lynis output", "lynis signal registry"]
tags: [zima, research, outputs, signal-registry, tools, lynis, graph_exclude]
type: provider_research_output
provider: lynis
provider_category: tools
status: not_started
prompt_note: prompt.md
provider_folder: lynis.md
obsidianUIMode: preview
---


# Lynis Tool/API Surface

Lynis is an agentless host audit tool invoked via CLI. The primary invocation is:

- **`lynis audit system`** – performs a full host audit on the local system. Supports optional flags (e.g. `--pentest` for non-root scans, `--quiet`, `--cronjob`, `--profile`, `--report-file`, etc.).
- **`lynis show`** – displays static information (e.g. version, profiles, host IDs). Not typically used for signal generation.
- **`lynis check-update`** (or `update`) – checks/upgrades the Lynis tool itself; _not_ relevant for host signals.
- **Logging/Reports**: Lynis writes _all_ technical details to a log (default `/var/log/lynis.log`). Warnings and suggestions are output on screen and collected in a single report file (default `/var/log/lynis-report.dat`). The report is a structured text file: each finding is recorded in lines like `Section: [SECTION_NAME]`, `Option/value: <key>=<value>`. For example:

    yaml

    Copy

    ```
    Remarks: # PKGS-7330
    Section: ports and packages
    Option/value: vulnerable_package[]=openssl-1.0.2-1
    Option/value: vulnerable_package_count=3
    ```

- **Test Identifiers**: Each check has a unique ID (e.g. `PKGS-7330`, `PKGS-7388`) shown in logs and used in report remarks. Sections (e.g. “ports and packages”) group related checks.
- **Hardening Index**: At the end of each scan, Lynis prints a _hardening index_ percentage (0–100) to screen. This is a summary score (not exported to the report file).
- **Warnings/Suggestions vs Findings**: Lynis differentiates _findings_ (e.g. vulnerable packages) from _suggestions_. For example, when vulnerabilities are found, it uses `ReportWarning` plus `vulnerable_package[]` entries. Many tests output only a suggestion (via `ReportSuggestion`) if a tool is missing or a non-critical issue is found. Only concrete evidence is in report fields.
- **Privileges**: Many tests require root privileges. Running as non-root will skip or mark tests as incomplete (some tests add an `SKIPTEST` flag). The user should _at least_ be root or use `--pentest` mode for best coverage. If run without root, missing findings should be treated as “scan incomplete.”
- **OS Support**: Lynis supports Linux, macOS, and BSDs (some tests skip if not applicable). Tests target various package managers (dpkg, rpm/yum, pacman, pkg, ports, etc.) and OS-specific features.
- **Exit Codes**: As per the Lynis man page, Lynis exits with 0 (normal), 1 (fatal error), 64 (bad params), 65 (incorrect data), 66 (file not found), and 78 if warnings are found and `error-on-warnings=yes`. (By default, warnings do not trigger nonzero exit.)

**Output Artifacts and Fields (from `lynis-report.dat`)**: Key parseable fields include:

- `package_manager[]` – which package manager was detected (e.g. `dpkg`, `zypper`, `pkg`), recorded for each test that finds a manager.
- `installed_packages` (integer) – count of installed packages found (e.g. by `dpkg -l` or `zypper`).
- `installed_kernel_packages` – count of installed kernel packages (RPM/Debian).
- `upgrade_available[]` – one or more package names for which newer versions are available (e.g. FreeBSD ports or Mac ports). Paired with `upgrade_available_count`.
- `vulnerable_package[]` – one or more package identifiers flagged as having known security issues (from `apt-get --dry-run`, YUM plugin, NetBSD/FreeBSD tools). Paired implicitly with a warning.
- `unattended_upgrade_tool[]` – any auto-update tool detected (e.g. `yum-cron`, `auter`).
- **Optional/derived fields**: Presence/absence of tests like apt repositories or plugins may be inferred from suggestions. For example, a missing `apt-show-versions` triggers only a suggestion, not a report field.
- **Recommendation text**: Many entries use `ReportSuggestion` (e.g. “Install yum-plugin-security”) that appear as free text in the report or log. These should _not_ be treated as standalone signals without concrete evidence in parsed fields.

#### Modes and Result Variants

- **Full audit (`lynis audit system`)** – generates the report and log as above. With root, _all_ tests run. Without root (`--pentest` or user), many checks skip or mark “not found” (e.g. “dpkg not found” if /usr/bin/dpkg isn’t visible due to privileges).
- **Partial output** – If run in `--quiet` mode, fewer on-screen messages but logs still have full info. `--cronjob` disables interactive prompts.
- **Error cases** – If run without necessary tools or on unsupported OS sections, Lynis will log “test skipped” (e.g. “dpkg not found, test skipped”). These skipped tests typically do not produce report fields.
- **Machine-readability** – The report file format is stable text but not JSON. Fields like `vulnerable_package[]` are parseable by simple text/regex. Relying on screen output (colored text) is not advisable. Always parse the report file or log.

#### Relevant Commands and Files

- **`/var/log/lynis.log`** – Verbose scan log (credentials, file permissions, etc.). Often too detailed for signals; mainly for audit trail.
- **`/var/log/lynis-report.dat` (or specified `--report-file`)** – Primary parseable output. Contains the `Option/value:` entries listed above.
- **Hardening Index** – printed on-screen (e.g. “Lynis scan details”) but not in report file. It is **contextual only** and not a direct signal (just overall audit score).
- **Examples**: A successful scan might show at the end: “Hardening index : 62%” and lists tests performed. If warnings occurred, e.g. PKGS-7330 found 3 vulnerable packages, the report will have lines like `Option/value: vulnerable_package[]=openssl-1.0.2-1` and `Option/value: vulnerable_package[]=libssl-1.0.2` plus a `ReportWarning` in the logs. If no issues, only counts (e.g. `installed_packages=98`) and no warnings appear, and the on-screen result shows green “OK” for those tests.

# Module Mapping

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|**os_security**|local_tool_or_deferred|`lynis audit system`|`lynis-report.dat`|direct_signal_input|hostname|Run as root (else many tests skip)||Emits hardening findings (warnings/misconfigs) from report. Key triggers are presence of warnings (e.g. missing security repo).|
|**patch_status**|local_tool_or_deferred|`lynis audit system`|`lynis-report.dat`|direct_signal_input|hostname|Root recommended; requires appropriate package tools (apt, portmaster, etc.)||Signals for available updates (fields `upgrade_available[]`) and missing security repos.|
|**software_vulnerability**|local_tool_or_deferred|`lynis audit system`|`lynis-report.dat`|direct_signal_input|hostname (see notes)|Root recommended; requires OS-specific audit tools (e.g. `apt-get`)||Emits signals for discovered vulnerable packages (`vulnerable_package[]` fields).|

- **Why:** The same audit output can feed all three modules, but different parts are relevant. _os_security_ consumes misconfiguration and hardening findings (e.g. missing repos, database inconsistencies). _patch_status_ consumes fields indicating missing updates (e.g. `upgrade_available[]`) and config gaps (no security repo). _software_vulnerability_ consumes `vulnerable_package[]` fields from Lynis’s CVE-package checks.
- **Enrichment-only:** Lynis fields like `installed_packages` or `package_manager[]` are only for context/metrics, not standalone signals. Many `ReportSuggestion` messages (e.g. “Install debsums”) are advice, not direct findings, and are **not** considered signals.
- **Utility-only:** The Lynis host ID (if any) or version checks are only used for correlating audits, not for signals. The hardening index is purely summary.
- **Out of scope:** Non-audit modes (e.g. `lynis show version`) do not emit signals. Tests purely advising on improvement (e.g. “unattended-upgrades available”) are not treated as signals.

# Signal Contract Table

Only the strongest standalone signals (true findings) are listed. Recommendations or purely contextual info are excluded.

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|os_security|lynis|lynis|audit system|security_repo_missing|patch_status|medium|no|ReportWarning for PKGS-7388 present|hostname|true_finding|[`PKGS-7388` triggered warning]|(none specific)|(none)|"No security updates repository found on host."|documented||Missing security repo implies host may not receive patches.|
|patch_status|lynis|lynis|audit system|updates_available|patch_status|medium|yes|`upgrade_available_count > 0`|hostname|true_finding|One or more `upgrade_available[]` entries in report|upgrade_available[], upgrade_available_count|(none)|"{0} update(s) available for installed packages."|documented||Triggered by Lynis tests on FreeBSD/macOS ports (others via apt-check count).|
|software_vulnerability|lynis|lynis|audit system|vulnerable_package_found|software_vulnerability|high|no|One or more `vulnerable_package[]` entries|hostname|true_finding|Presence of any `vulnerable_package[]` in report|vulnerable_package[]|(none)|"Host has vulnerable package: {0}."|documented||Found via OS audit (YUM/security plugin, apt-check, pkg_admin, etc.).|

- **Trigger conditions (field-based)**: We use fields emitted by Lynis `Report` statements. For example, `vulnerable_package[]` appears in `lynis-report.dat` whenever Lynis finds vulnerable packages. Similarly, `upgrade_available[]` entries come from Lynis’s port/updates tests. The missing-repository case has a `ReportWarning PKGS-7388` when none is found.
- **Entity type**: The closest fit in Zima’s schema is `hostname` (the audited host). (No standard “package” entity exists; the package name appears in evidence fields.)
- **Evidence fields**: For vulnerabilities, we store each `vulnerable_package[]` value. For updates, we store `upgrade_available[]` and its count. We do _not_ promote generic fields like `installed_packages`.
- **Severity**: Per Zima calibration, confirmed vulnerabilities are **high** (they indicate exploitable software). Available updates/patches are **medium** (they indicate potential exposure or misconfiguration). Missing security repos is **medium** (it’s a misconfiguration increasing risk).
- **Finding kind**: All above are true findings (not mere enrichment). The `security_repo_missing` is a misconfig finding (so true_finding in Zima’s taxonomy).
- **Notes**: We do not emit signals for low-risk suggestions. For example, Lynis might advise “Install `debsums`” or “apt-show-versions not found”, but these have no direct evidence (just tool absence) and thus are omitted.

# Confidence Guidance

|module|signal_type|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|os_security|security_repo_missing|High (parses known config files). Lynis reliably detects missing `security.ubuntu.com` or `security.debian.org` entries.|Config drift is rare; once missing, this remains until fixed. Regular scans can catch changes.|Corroborate via direct check of `/etc/apt/sources.list*` for security lines.|Evaluate severity mapping vs actual risk (none=exposed).|
|patch_status|updates_available|High (pulls from package manager). Lynis uses `portmaster` or `apt-show-versions` etc. to list updates.|Highly time-sensitive: hosts rapidly change. Each scan only reflects the moment of audit.|Confirm with OS package manager (`apt list --upgradable`, `yum check-update`, etc.).|Determine threshold for action (e.g. ≥1 update).|
|software_vulnerability|vulnerable_package_found|High (calls native audit tools). E.g. uses `apt-check`, YUM security plugin, FreeBSD `pkg audit`. These are vendor-maintained sources.|Can become stale if vulnerabilities are patched. Re-scan regularly.|Match with CVE databases or NVD for details; verify against actual OS.|Tune severity for partial results (some tools list numerous updates).|

- **Source reliability:** Lynis’s package and security checks use OS-native tools (`zypper pchk`, `apt-get --dry-run`, `pkg audit`, etc.). These are generally reliable. If a third-party tool (like `apt-show-versions`) is missing, Lynis may skip or warn, reducing reliability (we note this under gating logic).
- **Freshness:** All Lynis outputs are point-in-time. Package vulnerabilities or updates are valid only as of the scan. Frequent rescanning is needed. The audit itself is a snapshot, so older scans lose relevance as OS updates occur.
- **Corroboration:** Signals from Lynis can (and should) be confirmed via other host telemetry: e.g. an actual `apt list --upgradable` or osquery package inventory for updates; direct CVE lookup for flagged packages; checking `/etc/apt` for repos.
- **Calibration:** We should calibrate how Lynis warnings map to Zima severity. For example, Lynis’s notion of “vulnerable package” is conservative (only uses known security update channels). We advise no automatic mapping of Lynis severity labels – instead treat a flagged vulnerability as high unless there is evidence otherwise. Similarly, "updates available" is medium risk by default, but could be high if those updates fix critical CVEs (future work to integrate CVE data).

# Provider Summary

- **Strongest signals:** The most actionable outputs are **“vulnerable_package[]”** entries (software_vulnerability) and **“upgrade_available[]”** entries (patch_status). These directly indicate real host state (packages needing patch or already exploited). Lynis also clearly flags missing security repositories (host not receiving patches).
- **What _not_ to use Lynis for:** Lynis is _not_ a CVE scanner or exploit detector; it should not be used for general vulnerability enumeration beyond its built-in package checks. Many Lynis findings are _recommendations_ (e.g. “enable cron job for debsums”) that are not evidence of compromise or misconfiguration by themselves. Generic hardening advice (like “set sticky bit on /tmp”) should not produce signals unless tied to a concrete setting violation. Lynis scores or index values are for audit summary only.
- **Execution constraints:** Lynis requires local execution with root for full results. Insufficient privileges cause skipped tests and incomplete data. It can run as a one-off or via cron. Its output is textual; version differences of Lynis or the OS may add/rename tests, so parsers must tolerate unknown fields. The report format is fairly stable, but relying on specific ordering is risky. Repeated scans should deduplicate signals by host and check ID (the Zima platform should key signals by a combination of host and Lynis test ID or package name).
- **Signal vs Enrichment vs Utility:** Depending on the test:
    - Outputs like `vulnerable_package[]` and `upgrade_available[]` are **signal-producing** (direct evidence of issues).
    - Outputs like `installed_packages` or `package_manager[]` are **utility/context** (not alerts).
    - Suggestions or findings without a field (e.g. “no cron job” suggestions) are **out-of-scope** for signals.
- **Stable artifacts:** The canonical Lynis output to store is the entire `lynis-report.dat` (or specified report file). Key fields to preserve are those listed above under “Output Artifacts.” We should log the Lynis version and scan timestamp (available in screen output or log) for audit. Zima should treat Lynis primarily as a **periodic audit source**, not a continuous telemetry source; it gives a snapshot of host state.
- **Repeated findings:** If the same vulnerability is found on repeated scans, Zima should dedupe by package name and host. If an issue remains unpatched, it might repeatedly trigger; correlation logic can silence duplicates.
- **Final framing:** Lynis is best treated as a **mixed** provider: it produces _direct findings_ (vulnerabilities, missing updates) and rich **context/enrichment** (packages installed, audit score, tool presence) from a local host scan. Its recommendations (text advice) should **not** directly become signals without concrete evidence behind them.

{
  "provider": "lynis",
  "provider_category": "tools",
  "provider_role": "local_tool_or_deferred",
  "module_mappings": [
    {
      "module": "os_security",
      "provider_role": "local_tool_or_deferred",
      "provider_method": "lynis audit system",
      "endpoint_or_artifact": "lynis-report.dat",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "Run as root for full results; tests skip if insufficient privileges【16†L52-L58】【19†L92-L100】",
      "citation_refs": "【25†L119-L122】【70†L672-L676】",
      "notes": "Parses Lynis warnings for misconfigurations (e.g. missing security repo) as signals; suggestions without concrete evidence are ignored."
    },
    {
      "module": "patch_status",
      "provider_role": "local_tool_or_deferred",
      "provider_method": "lynis audit system",
      "endpoint_or_artifact": "lynis-report.dat",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "Requires appropriate package tools (apt, portmaster) installed for update checks",
      "citation_refs": "【36†L3880-L3886】【34†L3300-L3310】",
      "notes": "Detects available OS updates (`upgrade_available[]`) and missing patch repos (`PKGS-7388`)."
    },
    {
      "module": "software_vulnerability",
      "provider_role": "local_tool_or_deferred",
      "provider_method": "lynis audit system",
      "endpoint_or_artifact": "lynis-report.dat",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "Requires package audit tools (e.g. `apt-get`, `pkg_admin`, YUM security plugin) to be installed and updated",
      "citation_refs": "【31†L3190-L3200】【66†L736-L743】",
      "notes": "Emits signals for vulnerable packages found (`vulnerable_package[]`). Other vulnerability recommendations (tool suggestions) are not signals."
    }
  ],
  "signal_contracts": [
    {
      "module": "os_security",
      "source": "lynis",
      "provider": "lynis",
      "provider_method": "audit system",
      "signal_type": "security_repo_missing",
      "category": "patch_status",
      "severity": "medium",
      "severity_is_conditional": "no",
      "conditional_rule": "",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "`PKGS-7388` warning present (no security repository found)【70†L672-L676】",
      "evidence_fields": [],
      "enrichment_fields": [],
      "summary_template": "Host has no security updates repository configured.",
      "evidence_status": "documented",
      "citation_refs": "【70†L672-L676】",
      "notes": "Lynis emits a warning (PKGS-7388) if security apt repository is missing; treat as a finding of missing patch source."
    },
    {
      "module": "patch_status",
      "source": "lynis",
      "provider": "lynis",
      "provider_method": "audit system",
      "signal_type": "updates_available",
      "category": "patch_status",
      "severity": "medium",
      "severity_is_conditional": "yes",
      "conditional_rule": "`upgrade_available_count` > 0",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "Any `upgrade_available[]` entry appears in report【36†L3880-L3886】【34†L3300-L3310】",
      "evidence_fields": ["upgrade_available[]", "upgrade_available_count"],
      "enrichment_fields": [],
      "summary_template": "Package updates are available ({} package(s) upgradable).",
      "evidence_status": "documented",
      "citation_refs": "【36†L3880-L3886】【34†L3300-L3310】",
      "notes": "Based on Lynis checks for available updates (e.g. FreeBSD portmaster or Mac ports). Multiple packages are listed in evidence."
    },
    {
      "module": "software_vulnerability",
      "source": "lynis",
      "provider": "lynis",
      "provider_method": "audit system",
      "signal_type": "vulnerable_package_found",
      "category": "software_vulnerability",
      "severity": "high",
      "severity_is_conditional": "no",
      "conditional_rule": "",
      "entity_type": "hostname",
      "finding_kind": "true_finding",
      "trigger_condition": "One or more `vulnerable_package[]` entries in report【31†L3190-L3200】【66†L736-L743】",
      "evidence_fields": ["vulnerable_package[]"],
      "enrichment_fields": [],
      "summary_template": "Host has known vulnerable package: {}.",
      "evidence_status": "documented",
      "citation_refs": "【31†L3190-L3200】【66†L736-L743】",
      "notes": "Lynis uses OS tools (apt, yum, pkg) to find known vulnerable packages. Each entry is a signal. Zima should list each package name."
    }
  ],
  "confidence_guidance": [
    {
      "module": "os_security",
      "signal_type_or_use_case": "security_repo_missing",
      "source_reliability": "High (direct file scan for 'security.ubuntu.com'/security.debian.org)【70†L672-L676】.",
      "freshness_considerations": "Persistent until config changed; re-run Lynis when repos may change.",
      "corroboration_rules": "Verify `/etc/apt/sources.list` and `/etc/apt/sources.list.d/` for security entries.",
      "calibration_todo": "Assess real-world risk: not having a security repo may not immediately be exploited."
    },
    {
      "module": "patch_status",
      "signal_type_or_use_case": "updates_available",
      "source_reliability": "High (uses OS package manager output)【36†L3880-L3886】.",
      "freshness_considerations": "Time-sensitive; must re-scan frequently as new updates are released.",
      "corroboration_rules": "Check with native commands (`apt list --upgradable`, `yum check-update`, etc.) for consistency.",
      "calibration_todo": "Determine severity mapping if only non-critical updates are found."
    },
    {
      "module": "software_vulnerability",
      "signal_type_or_use_case": "vulnerable_package_found",
      "source_reliability": "High (uses vendor security tools; e.g. `apt-check`, `yum-security`)【66†L735-L743】【63†L4435-L4443】.",
      "freshness_considerations": "Stale after patches applied; re-run when OS is updated.",
      "corroboration_rules": "Cross-reference with official CVE databases or run `apt-get upgrade` dry-run.",
      "calibration_todo": "Refine severity if Lynis lists many updates (e.g. ignore low-risk findings)."
    }
  ]
}
