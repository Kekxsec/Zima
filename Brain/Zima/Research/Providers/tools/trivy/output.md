---
title: "output / tools / trivy"
aliases: ["trivy output", "trivy signal registry"]
tags: [zima, research, outputs, signal-registry, tools, trivy, graph_exclude]
type: provider_research_output
provider: trivy
provider_category: tools
status: not_started
prompt_note: prompt.md
provider_folder: trivy.md
obsidianUIMode: preview
---


# A. Tool/API Surface Appendix

**Trivy CLI Modes:** Trivy is a local CLI vulnerability scanner. Relevant to software_vulnerability, use primarily:

- **Filesystem scan (`trivy fs <path>`)** – scans a directory or project for vulnerabilities in language-specific packages (reads lockfiles, manifests). Supports languages (e.g. npm, pip, Maven) via detected dependency files. By default it scans for vulnerabilities and secrets. With `--list-all-pkgs` it lists all detected packages (inventory).
- **Rootfs scan (`trivy rootfs <ROOTDIR>`)** – scans an unpacked filesystem (e.g. container root or local root) for OS-package vulnerabilities. Use this to scan the host or container’s full root.
- **Repository scan (`trivy repository <REPO_PATH|REPO_URL>` or `trivy repo`)** – scans a local or remote Git repo directory for vulnerabilities (parses dependency files and code).
- **DB update commands (`--download-db-only`, `--download-java-db-only`)** – fetch the vulnerability database images without scanning. These preload Trivy’s cache for offline use. Conversely, `--skip-db-update` (and `--skip-java-db-update`) skip network DB fetch during a scan. For air-gapped use, run `trivy image --download-db-only` on a networked host to update, then export cache.

**Execution & Prerequisites:** Trivy runs on Linux, macOS, Windows. Scanning OS/packages often requires elevated privileges or host access (root or container context) to enumerate installed packages. It requires periodic DB sync to download the `trivy-db` (vulnerability feeds) and optionally the Java index DB. Trivy’s vulnerability DB is packaged as OCI images (in GHCR, dockerhub, or mirror.gcr.io). Without updates, scans may miss recent CVEs. The `trivy clean` command can remove stale DB cache.

**JSON Output (schema v2):** Using `--format json`, Trivy outputs a top-level object with fields like `SchemaVersion`, `CreatedAt`, `ArtifactName`, `ArtifactType`, and `Metadata` (OS info, e.g. Family/Version). The core is a **`Results`** array: each element has

- `Target` (scanned item, e.g. path or repo name)
- `Class` (scan class, e.g. `"os-pkgs"` for OS packages, `"lang-pkgs"` for language packages)
- `Type` (distribution or language type, e.g. `"alpine"` or `"npm"`)
- `Vulnerabilities` (list of vulnerability objects)
- _Or_ `Packages` for inventory (in code scans) – see below.

Each vulnerability entry includes fields (most documented): `VulnerabilityID` (e.g. CVE code), `PkgName`, `InstalledVersion`, `FixedVersion` (might be empty if no fix), `Status` (e.g. `"fixed"` or `"unknown"`), and `Severity` (Trivy’s label). It also includes `PkgIdentifier` (with `PURL` and `UID`), `Layer` (image diff ID, if applicable), `PrimaryURL`, `DataSource` (vendor feed info), `Title`, `Description`, `CweIDs`, `VendorSeverity`, `CVSS` scores, `References`, `PublishedDate`, `LastModifiedDate`, etc. Notably **`VulnerabilityID`, `PkgName`, `InstalledVersion`, and `Severity` are always present**. Other fields may be empty or absent depending on context.

**Modes and Output Characteristics:**

- **`trivy fs` (default)** – Scans code directory. If dependency lockfiles are present, produces one `Results` entry per file with `"Class": "lang-pkgs"`, containing `Packages` (if `--list-all-pkgs`) and/or `Vulnerabilities`. If no vulns, Trivy’s JSON _may omit_ an empty `Vulnerabilities` array (a known issue in versions prior to v0.57). In practice, when vulnerabilities exist, each is listed under `Vulnerabilities`. If only inventory, the result has `"Packages"`. Example: see [18] for a `lang-pkgs` result with `Packages` (no `Vulnerabilities`) when using `--list-all-pkgs`.
- **`trivy rootfs`** – Scans an entire root file-system. Produces `Results` with `"Class": "os-pkgs"` and vulnerabilities in system packages. Similar JSON schema as image scanning, minus image-specific metadata. On success with findings, returns a non-zero exit code by default; no-findings returns 0 with empty `Vulnerabilities`. If OS detection fails (e.g. minimal rootfs), Trivy warns (“OS is not detected”) and may list no OS-pkg entries.
- **`trivy repo`** – Similar to `fs`, but explicitly for Git repos. It identifies package files (e.g. `package.json`, `requirements.txt`) and outputs `lang-pkgs` results.
- **Filtering flags:** Use `--ignore-unfixed` to hide unfixed issues, `--severity <levels>` to filter by severity, `--ignorefile` to skip CVEs, and `--scanners vuln` (default) to select only vulnerability scans. These flags only affect which vulnerabilities appear, not schema.

**Response Variants:**

- _Vulnerabilities found:_ `Results[].Vulnerabilities` contains one object per CVE.
- _No vulnerabilities:_ `Results[].Vulnerabilities` may be empty or omitted. On `trivy fs`, entire `Results` may be empty. Trivy’s exit code will be 0.
- _Partial/Unsupported:_ If a lockfile is unsupported or no known version, Trivy may emit a warning but may still list packages (without vulns).
- _Errors:_ Missing DB (no internet, outdated mirror) yields errors unless `--skip-db-update` is used. Permission denied yields scan abort.

**Offline/Caching:** Trivy caches vulnerability data in a local SQLite-like store (`~/.cache/trivy`). Use `trivy image --download-db-only` periodically to refresh. In restricted environments, use flags: `--skip-db-update` (skip main DB fetch), `--skip-java-db-update`, `--offline-scan` (disable network), and preload DB images via OCI pull.

**Output Stability:** The JSON schema is versioned (`SchemaVersion: 2`). The top-level and vulnerability schema fields are stable across minor versions. Always-captured fields are documented. Optional fields (e.g. `FixedVersion`, `CweIDs`, `CVSS`) may be absent. The `PURL` and `UID` under `PkgIdentifier` uniquely identify the package version. The field `Target` identifies the scan target (file or image).

# B. Module Mapping Table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|software_vulnerability|local_tool_or_deferred|trivy fs (filesystem) scan|Project directory path (lockfile)|direct_signal_input|repository (code)|Scan must complete without error; languages detected||Scans code for vulnerable deps; outputs CVE matches as signals.|
|software_vulnerability|local_tool_or_deferred|trivy fs --list-all-pkgs|Project directory path|enrichment_only|repository (code)|Used only if inventory requested (not a finding)||Lists all detected packages; useful for context/inventory, not a finding.|
|software_vulnerability|local_tool_or_deferred|trivy rootfs scan|Host root directory ("/")|direct_signal_input|hostname|Host OS must be Linux/Unix; requires root access||Scans OS packages on host; produces vulnerability findings.|
|software_vulnerability|local_tool_or_deferred|trivy repository scan|Git repo path or URL|direct_signal_input|repository|Repository must contain supported package files||Scans code repo similarly to fs; yields vuln signals from dependencies.|
|software_vulnerability|local_tool_or_deferred|trivy image scan|Container image (not target)|out_of_scope|-|Not used for endpoint module|-|Image scanning targets container images, not host/software.|
|software_vulnerability|local_tool_or_deferred|trivy sbom scan|SBOM file (not target)|out_of_scope|-|SBOM scanning not endpoint software.|-|SBOM mode outside scope.|

_Notes:_ All **direct_signal_input** modes produce vulnerability findings that should be emitted as signals. The package inventory (via `--list-all-pkgs`) is **enrichment_only** (useful for context, not separate signals). `trivy image` and SBOM modes are out-of-scope for the software_vulnerability module.

# C. Signal Contract Table

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|software_vulnerability|software_vulnerability|trivy|fs/rootfs/repository|software_vulnerability_found|software_security|medium|no|–|repository|true_finding|`.Results[].Vulnerabilities[]` exists (one signal per item)|VulnerabilityID, PkgName, InstalledVersion, Severity, Title, Description, PrimaryURL|(none – all evidence fields included above)|`Vulnerability {{VulnerabilityID}} found in package {{PkgName}} version {{InstalledVersion}}.`|documented||Signals emitted per CVE; only true vulnerability findings, not inventory.|

- **signal_type:** we use a generic `software_vulnerability_found` for any package vulnerability. (No separate OS vs language variant to keep signals stable.)
- **entity_type:** code repositories or paths are treated as `repository` (the closest fit).
- **trigger_condition:** each JSON vulnerability object triggers a signal. In implementation, parser would emit one signal per `.Results[].Vulnerabilities[*]` entry.
- **evidence_fields:** include key fields from the JSON: CVE ID (`VulnerabilityID`), package name, installed version, title, description, source URL. Severity from provider is captured but not used as final.
- **summary_template:** a simple templated description.
- **finding_kind:** `true_finding` since vulnerabilities are actual issues.
- **evidence_status:** documented (the Trivy docs explicitly state required fields).
- **notes:** Vendor severity is captured but Zima recalibrates it (see Severity Rules below).

_No standalone signals_ are emitted for package inventory (`Packages[]` lists) or scan metadata. Those are treated as enrichment/context and not separate signals.

# D. Severity Rules

For `software_vulnerability_found` signals, Zima does _not_ directly trust Trivy’s `"Severity"`. Instead:

- **Base assignment:** Most vulnerabilities represent confirmed software flaws, so we classify them at least **Medium** by default (unverified threat but real CVE).
- **Conditional escalation:** If Trivy’s `Severity` label is HIGH or CRITICAL _and_ the vulnerability is known to be exploitable, consider raising to **High**. If it’s CRITICAL with evidence of active exploitation, consider **Critical**. (This aligns with Zima: critical = immediate credential/secret leak or active exploit; high = confirmed serious vulnerability.) For example, a CVE with vendor-critical rating and no fix might be **High** severity.
- **Lower bounds:** If Trivy reports a vulnerability as `LOW` or if CVSS score is very low (<4.0), it may stay at **Low** or **Medium** (likely medium, since even low-vuln means code flaw).
- **Rationale:** A detected CVE is a direct security weakness, so at least medium. Only escalate to high/critical if context justifies (e.g. CVSS ≥9 or zero-day exploitation).

_We _do not_ simply copy Trivy’s label as final Zima severity._ Instead use it as one input (e.g. Trivy HIGH often → Zima Medium/High).

# E. Confidence Guidance

|module|signal_type|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|software_vulnerability|software_vulnerability_found|Trivy uses well-known CVE databases and vendor feeds, so reliability is high for known OS/language CVEs. However, it may miss vulnerabilities if lockfiles are incomplete or DB is stale. Its language dependency parser can sometimes misclassify (see known dev-dep bug). Treat output as authoritative if fields present, but verification via a second source (e.g. OS package manager audit) could improve confidence.|The vulnerability database must be up-to-date. A stale DB (weeks-old) risks missing new CVEs; conversely, very recent fixes may not yet be in DB. Track `CreatedAt` or DB update time. If `--skip-db-update` or offline mode is used, reduce confidence (missing data).|Cross-check critical CVEs against another scanner or public feeds (NVD). Re-scan after DB updates to corroborate new finds. If multiple Trivy modes (e.g. rootfs and fs) report the same CVE on same host/package, this increases confidence.|Calibrate mapping from provider severity to Zima severity: e.g. test mapping HIGH→High vs Medium. Determine CVSS thresholds for High vs Medium. Assess false positives due to mis-detected package names. Monitor how often vulnerabilities appear without fixes (Status!=“fixed”) and whether that impacts urgency.|

# F. Provider Summary

- **Strong signals:** Trivy’s strongest contribution is **software vulnerability detection**: CVEs in OS packages or dependencies found on the host. These should be used as direct findings (true positives of vulnerable software). Its package inventory output is useful context but not a risk signal on its own.
- **Not for:** Do _not_ use Trivy for misconfigurations, secrets, or infrastructure scanning signals here (those are separate modules). Also, Trivy should not be the _sole_ inventory source for assets – it’s best used atop an existing asset list. It is not designed for real-time network telemetry or dynamic tests.
- **Execution cautions:** Trivy runs locally (no API key needed) but requires read access to package databases and possibly root privileges. It regularly updates a local DB (default in `~/.cache/trivy`), which must be maintained or preloaded (via `--download-db-only`) for accurate results. Offline/Air-gapped use requires manual DB syncing and use of `--skip-db-update` flags. Rate limits can occur when pulling DB images (multiple registry endpoints are attempted).
- **Role by mode:** Mixed. When run in vulnerability-scan mode (`fs`, `rootfs`, `repo`), Trivy is **signal-producing** (direct_signal_input). When used to list packages, it is **enrichment-only**. The DB download commands and `trivy clean` are **utility-only** (no signals). In summary: vulnerability results → direct signals; package inventory → enrichment; DB sync → utility.

{
  "provider": "trivy",
  "provider_category": "tools",
  "provider_role": "local_tool_or_deferred",
  "module_mappings": [
    {
      "module": "software_vulnerability",
      "provider_method": "trivy fs",
      "endpoint_or_artifact": "filesystem path",
      "classification": "direct_signal_input",
      "entity_types": ["repository"],
      "gating_logic": "Valid project directory with detectable dependencies",
      "citation_refs": ["【29†L721-L724】"],
      "notes": "Scans code for vulnerabilities via lockfiles; emits CVE signals"
    },
    {
      "module": "software_vulnerability",
      "provider_method": "trivy fs (inventory)",
      "endpoint_or_artifact": "filesystem path",
      "classification": "enrichment_only",
      "entity_types": ["repository"],
      "gating_logic": "Run with --list-all-pkgs; not used for signal generation",
      "citation_refs": ["【18†L345-L353】"],
      "notes": "Lists detected packages for context; no independent signals"
    },
    {
      "module": "software_vulnerability",
      "provider_method": "trivy rootfs",
      "endpoint_or_artifact": "root directory path",
      "classification": "direct_signal_input",
      "entity_types": ["hostname"],
      "gating_logic": "Requires root or container context with OS packages",
      "citation_refs": ["【9†L279-L287】【29†L721-L724】"],
      "notes": "Scans full host filesystem for OS-package CVEs; emits signals"
    },
    {
      "module": "software_vulnerability",
      "provider_method": "trivy repository",
      "endpoint_or_artifact": "Git repo URL or path",
      "classification": "direct_signal_input",
      "entity_types": ["repository"],
      "gating_logic": "Local/remote repo with detectable language files",
      "citation_refs": ["【4†L260-L268】"],
      "notes": "Scans code repo similarly to fs; finds vulnerabilities in dependencies"
    }
  ],
  "signal_contracts": [
    {
      "module": "software_vulnerability",
      "source": "software_vulnerability",
      "provider": "trivy",
      "provider_method": "fs/rootfs/repository scan",
      "signal_type": "software_vulnerability_found",
      "category": "software_security",
      "severity": "medium",
      "severity_is_conditional": "yes",
      "conditional_rule": "If CVE has vendor severity HIGH/CRITICAL or active exploit, escalate to High; else Medium",
      "entity_type": "repository",
      "finding_kind": "true_finding",
      "trigger_condition": "`Results[].Vulnerabilities[]` exists in JSON output【29†L721-L724】",
      "evidence_fields": ["VulnerabilityID", "PkgName", "InstalledVersion", "Severity", "Title", "Description", "PrimaryURL"],
      "enrichment_fields": [],
      "summary_template": "Vulnerability {{VulnerabilityID}} found in package {{PkgName}} version {{InstalledVersion}}.",
      "evidence_status": "documented",
      "citation_refs": ["【29†L721-L724】【14†L892-L895】"],
      "notes": ""
    }
  ],
  "confidence_guidance": [
    {
      "module": "software_vulnerability",
      "signal_type_or_use_case": "software_vulnerability_found",
      "source_reliability": "Uses official CVE/OS vendor feeds (Trivy DB)【25†L291-L300】. Generally reliable for known vulnerabilities, but can miss issues if DB is stale or lockfiles incomplete.",
      "freshness_considerations": "DB updates frequently; ensure periodic `--download-db-only`. If offline or `--skip-db-update` used, confidence drops due to missing new CVEs.",
      "corroboration_rules": "Cross-check critical CVEs with other sources (e.g. OS package manager or NVD). If multiple Trivy scans on same asset report same CVE, confidence increases.",
      "calibration_todo": "Validate severity mapping (e.g. Trivy HIGH→Zima High). Track false positives from misdetected packages (e.g. dev-dep bugs【18†L369-L377】) and adjust trigger logic."
    }
  ]
}
