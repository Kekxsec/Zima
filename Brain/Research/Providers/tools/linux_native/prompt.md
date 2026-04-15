---
title: "prompt / tools / linux_native"
aliases: ["linux_native", "linux native prompt", "linux_native research prompt"]
tags: [zima, research, prompts, provider-research, tools, linux_native, graph_exclude]
type: provider_research_prompt
provider: linux_native
provider_category: tools
obsidianUIMode: preview
kind: artifact
status: not_started
llm_include: false
code_scope: backend
---

Research > Zima Research > provider workspace

## Context

I am building Zima, a cybersecurity platform whose modules consume provider data and emit normalized signals. This prompt is for implementation-grade research, not a generic provider summary.

Primary goal:
- determine how this provider should be used by each target module
- identify which provider outputs create standalone signals, which are enrichment-only, and which are utility-only
- define field-level trigger logic, severity rules, evidence fields, and mapper notes that can be carried directly into `modules/*/rules.py` and `modules/*/mapper.py`

My platform's normalized signal schema includes:

| Field        | Type                | Notes |
|--------------|---------------------|-------|
| signal_type  | string (snake_case) | Internal name, e.g. `credential_breach_found` |
| category     | string              | Use the best-fit Zima category/domain for the module. Common examples: `identity_security`, `account_security`, `network_security`, `domain_security`, `threat_intel`, `dark_web`, `privacy`, `cloud_security`, `secrets`, `saas`. Do not force a worse category just to match this example list. |
| severity     | string              | critical / high / medium / low / info |
| confidence   | string              | Final `high` / `medium` / `low` is calibrated later from real data. In this research pass, provide confidence guidance, not a guessed production value. |
| entity_type  | string              | Examples: email / domain / ip / hostname / username / phone / hash / url / account / company / repository / cloud_resource |
| source       | string              | The module that emits the signal, not the raw provider endpoint name |
| summary      | string              | One-sentence signal summary template |
| evidence     | object              | Raw provider fields worth storing for audit, remediation, and deduplication |
| tags         | list[string]        | Domain and finding tags, e.g. `["breach", "stealer_log", "plaintext_password"]` |

Severity calibration guide (do not deviate without strong justification):
- critical: direct credential exposure, plaintext passwords, active stealer logs, live malware C2
- high: confirmed breach, exposed PII, verified malicious infrastructure, active threat actor attribution
- medium: suspicious activity, unverified breach, reputation degradation, passive threat indicators
- low: informational findings with mild risk, historical data with low recency confidence
- info: pure enrichment/context with no standalone risk (e.g. WHOIS data, ASN lookup)

Important interpretation rules:
- Research at the module boundary. A provider endpoint is not a finished signal until a target module decides it is.
- One provider may feed multiple modules; keep module decisions separate.
- Distinguish four classes of provider output: `direct_signal_input`, `enrichment_only`, `utility_only`, and `out_of_scope`.
- Base severity on my platform's calibration guide, not the provider's own score/label unless the provider field directly evidences one of my severity definitions.
- Do not assign final production confidence based on AI judgment alone. Instead provide source-reliability notes, freshness considerations, corroboration opportunities, and calibration TODOs.
- Distinguish between true findings and enrichment-only/context fields.
- Do not invent field names, enum values, response shapes, or trigger conditions. If unclear, mark as unknown or inferred.
- Prefer stable, implementation-worthy signal types. Do not create unnecessary vendor-specific variants if they map to the same internal concept.

---

## Provider Under Research

**Provider:** linux_native
**Category:** tools
**URL:** https://kernel.org — distro package manager and system tool docs
**Tool type:** os_native_interface — distro-native commands
**OS support:** Linux only (must handle Debian/Ubuntu, RHEL/Fedora, Arch families)

**Target modules:** `os_security`, `patch_status`, `disk_encryption_check`, `firewall_status`

**Provider role:** direct_signal_input for posture checks, utility_only for inventory

**Build priority:** P0 / Core

**Cautions:**
Very distro-specific. Commands, output formats, and package managers differ materially across distro families. Must branch normalization by distro.

**First-pass severity:**
- LUKS not enabled on root = high
- firewall not active = high
- root SSH enabled = high
- unattended-upgrades disabled = medium
- kernel significantly out of date = high

---

## Research Instructions

Use official provider documentation, official API references, official OpenAPI specs, official example responses, and provider-maintained SDK/docs as primary sources. Use third-party sources only to fill gaps, and label them clearly.

For every important claim about schema, trigger logic, enums, authentication, or limits, cite the source. Clearly label whether each trigger is:
- documented
- derived from documented fields
- inferred from examples only
- unclear

Research at the module boundary: for each target module, decide whether the provider contributes a direct signal, only enrichment, only utility output, or is out of scope.

If the provider is a local tool, utility parser, or alerting service, say that explicitly and do not invent standalone signals just to fill the table.

Identify all relevant endpoints, methods, or output artifacts for this provider and classify each as:
- direct_signal_input
- enrichment_only
- utility_only
- out_of_scope

Important: stay scoped to this provider only. Do not generalize from adjacent providers unless the docs explicitly share the same backend/schema.

---

## Tasks

### 1) Tool Surface & Provider Research
Document per distro family (Debian/Ubuntu, RHEL/Fedora, Arch):

**Disk encryption:**
- `lsblk -f` — LUKS detection via FSTYPE column showing "crypto_LUKS"
  - Output format, relevant columns: NAME, FSTYPE, MOUNTPOINT
  - How to determine if root filesystem sits on an encrypted volume
- `cryptsetup status <name>` — active LUKS device details
  - Properties: type, cipher, keysize, device
  - Requires root
- `dmsetup ls --target crypt` — alternative LUKS detection
  - When to prefer over lsblk

**Firewall:**
- Debian/Ubuntu: `ufw status` — output strings: "Status: active" / "Status: inactive"
  - Verbose mode: `ufw status verbose` for default policies
- RHEL/Fedora: `firewall-cmd --state` — output: "running" / "not running"
  - `firewall-cmd --list-all` for active zone details
- Generic: `iptables -L -n` / `nft list ruleset`
  - Fallback when neither ufw nor firewalld is installed
  - How to determine if rules are actually configured vs empty default
  - Requires root

**OS version and kernel:**
- `/etc/os-release` — file format, key fields: ID, VERSION_ID, PRETTY_NAME, ID_LIKE
  - How to determine distro family from ID_LIKE
- `uname -r` — kernel version string format
  - How to compare against latest available kernel

**Updates:**
- Debian/Ubuntu: `apt list --upgradable` — output format, parsing
  - Distinguish security updates: `apt list --upgradable 2>/dev/null | grep -i security` or use `unattended-upgrades --dry-run`
- RHEL/Fedora: `dnf check-update` — exit code 100 = updates available, 0 = up to date
  - `dnf updateinfo list security` for security-specific updates
- Arch: `pacman -Qu` — lists upgradable packages, one per line

**Auto-updates:**
- Debian/Ubuntu: `systemctl is-enabled unattended-upgrades` — enabled/disabled
  - Config: `/etc/apt/apt.conf.d/20auto-upgrades`
- RHEL/Fedora: `systemctl is-enabled dnf-automatic` — enabled/disabled
  - Config: `/etc/dnf/automatic.conf`
- Arch: typically no built-in auto-update mechanism

**Installed software:**
- Debian/Ubuntu: `dpkg -l` — output format, columns: Status, Name, Version, Architecture, Description
  - `dpkg-query -W -f='${Package}\t${Version}\n'` for cleaner output
- RHEL/Fedora: `rpm -qa --queryformat '%{NAME}\t%{VERSION}-%{RELEASE}\n'`
- Arch: `pacman -Q` — package name and version per line

**SSH configuration:**
- `/etc/ssh/sshd_config` — key directives:
  - PermitRootLogin: yes / no / prohibit-password / forced-commands-only
  - PasswordAuthentication: yes / no
  - PubkeyAuthentication: yes / no
- Include directives: `Include /etc/ssh/sshd_config.d/*.conf` (modern distros)
- How to determine effective config vs commented defaults

For each command/file, document:
- exact invocation per distro family
- output format and parsing strategy
- privilege requirements (user vs root)
- distro version compatibility concerns
- error conditions and edge cases (command not found, service not installed)

### 2) Module Mapping Appendix
For each target module, document:
- module name
- provider method(s), endpoint(s), or artifacts used
- classification: direct_signal_input / enrichment_only / utility_only / out_of_scope
- why the module should or should not consume it
- important gating logic before signal creation
- source module name to use in emitted signals

### 3) Signal Contract Table
Only create rows for standalone signals that should actually be emitted by a module.

For each signal row, provide:
- module
- source
- provider
- provider_method
- snake_case signal_type
- category
- entity_type
- finding_kind: true_finding / contextual_enrichment
- exact trigger_condition using actual API field names
- evidence_fields to persist
- enrichment_fields worth storing but not promoting into separate signals
- summary_template
- evidence_status: documented / derived / inferred / unclear

If the provider should not emit standalone signals for a target module, say so explicitly and leave it out of the signal table.

### 4) Severity Rules
For each signal row:
- assign severity
- explain why using my calibration guide
- identify conditional severity logic if applicable

### 5) Confidence Guidance
Do not output final production confidence values. For each signal type or module use-case, provide:
- source_reliability notes
- freshness / staleness considerations
- corroboration opportunities
- suggested calibration TODOs

### 6) Tags
For each signal type, suggest 2-5 applicable tags from:
breach, stealer_log, plaintext_password, exposed_secret, pii_exposure, phishing, malware, c2, botnet, spam, proxy, tor, vpn, data_broker, dark_web, credential_stuffing, open_port, misconfiguration, threat_actor, ransomware, typosquat, lookalike, dmarc_fail, spf_fail

### 7) Implementation Notes
Capture mapper/rules concerns that would matter during build-out:
- field paths that must survive parsing
- null / empty / no-hit behavior
- rate limits, billing, licensing, or premium-tier constraints
- deduplication keys or natural identifiers
- raw evidence worth storing for remediation or audit
- what belongs in provider client vs module mapper vs correlation layer

Additionally:
- Distro detection strategy: document how the provider client should detect the distro family at runtime (parse `/etc/os-release` ID_LIKE field) and branch to the correct command set.
- Handling missing commands gracefully: when `ufw` is not installed, fall back to `iptables`/`nft`. When `systemctl` is not available, check for init scripts. Document the full fallback chain.
- Sudo requirements: document which commands need root and the fallback behavior when run unprivileged. Determine if Zima should request sudo upfront or handle permission errors gracefully.
- Parsing different output formats: many Linux commands output unstructured text. Document regex patterns or parsing strategies for each command, per distro.
- Document the relationship between this provider and the posture provider — linux_native provides the raw data, posture provides the abstraction layer.

---

## Required Output

### A. Tool Surface Appendix
Provide a structured per-command, per-artifact, or per-interface appendix.

### B. Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|

### C. Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Where:
- severity_is_conditional = yes / no
- conditional_rule = plain-English logic
- trigger_condition = actual field-based logic
- evidence_status = documented / derived / inferred / unclear
- finding_kind = `true_finding` or `contextual_enrichment`

If there are no standalone signals for this provider, return an empty signal table and explain why.

### D. Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|

### E. Provider Summary
1. strongest signal types (or strongest utility contributions)
2. what the provider should not be used for
3. installation / privilege / platform cautions
4. whether this provider should be treated as signal-producing, enrichment-only, utility-only, or deferred

### F. Structured JSON
After the markdown report, provide a JSON object with keys: `provider`, `provider_category`, `provider_role`, `module_mappings`, `signal_contracts`, `confidence_guidance`. Use `"unknown"` for unavailable details.
