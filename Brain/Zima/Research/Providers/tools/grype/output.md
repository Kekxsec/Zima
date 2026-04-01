---
title: "output / tools / grype"
aliases: ["grype output", "grype signal registry"]
tags: [zima, research, outputs, signal-registry, tools, grype, graph_exclude]
type: provider_research_output
provider: grype
provider_category: tools
status: not_started
prompt_note: prompt.md
provider_folder: grype.md
obsidianUIMode: preview
---
# A. Tool/API Surface Appendix

**Grype Overview:** Grype is an open-source vulnerability scanner that can analyze container images, filesystem directories, archives, and SBOM files. It auto-detects the target type (image vs directory vs SBOM, etc) when you run `grype <target>`, or you can specify the source with `--from` (e.g. `--from dir` for a directory). For example, to scan a project directory or local filesystem path:

- `grype /path/to/project` (implicitly `dir:`).
    To scan an SBOM file:
- `grype sbom:./sbom.json` or `grype ./sbom.json`. Grype supports SBOM formats including Syft JSON, SPDX (JSON/XML), and CycloneDX (JSON/XML); you can pipe JSON SBOM data directly into Grype (e.g. `syft -o json image | grype`).

Grype also supports container image scanning (`grype alpine:latest` etc) and image archive scanning (`oci-archive:`), but for endpoint/software vulnerability use we focus on filesystem and SBOM modes. It can scan individual package URLs or CPEs via `--from purl` or `--from cpes` for targeted checks (not common in endpoint mode). Grype runs on Linux, macOS, and Windows; scanning a filesystem requires only read permissions on the target files (no special privileges beyond normal filesystem access).

**Output and JSON Schema:** By default Grype emits a human-readable table, but for integration use the JSON output (`-o json`). The JSON format has a top-level `matches` array, where each element represents one matched vulnerability instance. Each match object contains:

- **`vulnerability`** – an object with the CVE/GHSA/ID, data source URL, namespace (ecosystem context), provider severity, fix information, advisories, CVSS, risk score, and other metadata. For example, `"vulnerability.id"` (string) is the ID (e.g. `CVE-2021-36159`), `"severity"` (string) is the vendor rating, and `"fix.versions"` is a list of patched versions with `"fix.state"` (fixed/not-fixed).
- **`artifact`** – the package or file matched. Typically includes `"name"`, `"version"`, `"type"` (ecosystem, e.g. `apk`, `deb`, `npm`, `go-module`, etc.), and `"locations"` (file paths). (These fields align with Syft’s catalog: name, version, language/type, CPE or PURL may also appear.)
- **`matchDetails`** – an array of objects describing how the match was made. Each detail has `"type"` (e.g. `exact-direct-match` vs `cpe-match`), `"matcher"` (which algorithm), `"searchedBy"` (attributes used, e.g. package name/version/distro), and `"found"` (attributes in the vulnerability that matched, e.g. version constraints). The match type indicates confidence: `exact-direct-match` and `exact-indirect-match` imply high-confidence (package name matched directly in a vulnerability feed), while `cpe-match` is a lower-confidence fallback via CPE/NVD. Additional arrays appear if filtering rules are used (e.g. `ignoredMatches` for suppressed vulns). A truncated JSON example for one match might look like:

json

Copy

```json
{
  "vulnerability": {
    "id": "CVE-2021-36159",
    "dataSource": "https://security.alpinelinux.org/vuln/CVE-2021-36159",
    "namespace": "alpine:distro:alpine:3.10",
    "severity": "Critical",
    "urls": [],
    "description": "...",
    "fix": {
      "versions": ["2.10.7-r0"],
      "state": "fixed"
    },
    "advisories": [],
    "cvss": [...],
    "risk": 0.92
  },
  "artifact": {
    "name": "apk-tools",
    "version": "2.10.6-r0",
    "type": "apk",
    "locations": [{"path": "/etc/apk/installed"}],
    "language": "alpine"
  },
  "matchDetails": [
    {
      "type": "exact-direct-match",
      "matcher": "apk-matcher",
      "searchedBy": {
        "distro": {"type": "alpine","version": "3.10.9"},
        "package": {"name": "apk-tools","version": "2.10.6-r0"},
        "namespace": "alpine:distro:alpine:3.10"
      },
      "found": {
        "vulnerabilityID": "CVE-2021-36159",
        "versionConstraint": "< 2.10.7-r0 (apk)"
      }
    }
  ]
}
```

(Above excerpt formats are drawn from Anchore docs.)

**Vulnerability DB and Updates:** Grype relies on a local SQLite vulnerability database (Grype-DB) containing upstream feed data. On each run it **checks for an updated database** online and auto-downloads it if a new version exists. By default Grype will **fail a scan if the DB is over 5 days old**; this can be disabled or tuned in config (e.g. `db.validate-age: false`). The `grype db update` command forces a manual download of the latest DB, and `grype db check` reports if an update is available (exit code 0 = up-to-date, 1 = update available). Other subcommands (`grype db list/status/delete`) let you inspect or remove the DB. **Offline/Air-Gapped:** Without network access, Grype will not update, so a dated DB may cause scans to fail or miss new CVEs. In offline mode, ensure a recent DB is preloaded (e.g. via `grype db import` or disabling age check) or expect staleness risks.

**Matching Behavior & Policies:** Grype supports ignoring and filtering vulnerabilities via flags (e.g. `--only-fixed`, `--ignore-states`, or external VEX docs). Matches that are filtered out appear under an `ignoredMatches` array (not in `matches`). In JSON output, **all fields are present** (including suppressed ones if `--show-suppressed` is used). Grype also supports `--by-cve` to normalize all IDs to CVEs where possible. The output includes EPSS and calculated risk scores which could be used in advanced filtering or severity tuning.

**OS and Platform:** Grype runs natively on Linux, macOS, and Windows. Scanning container images requires a Docker/Podman engine or registry access, which is out-of-scope for endpoint use. File and directory scans work the same on all platforms, given file path support. Windows scanning will still catalog Windows executables and packages if the database has relevant feeds.

**Relevant Commands/Modes:**

- **`grype <target>`** – Primary scan command. `<target>` can be a directory, an SBOM (`sbom:...` or file path), or an image reference. This produces vulnerability **matches** in JSON via `-o json` (or text table if no `-o`). _Classification:_ **direct_signal_input** (yields vulnerability findings).
- **`grype -o json ...`** – Forces JSON report. Includes all matches and fields above. Required for machine parsing.
- **`grype db update`** – Updates local vulnerability DB (requires Internet). _Classification:_ **utility_only** (no signals).
- **`grype db check`** – Checks if DB update is available. _Utility_only_.
- **`grype explain --id <CVE>`** – Consumes JSON output and explains a CVE match (list of files, context). This is for user guidance; it produces a human-readable report. _Classification:_ **enrichment_only** (no new signal; contextual info).

**Modes Out-of-Scope:** Image/registry scanning, license scanning, EOL scanning, and database search commands (`grype db search`) are outside the endpoint/software use-case.

### B. Module Mapping Table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|software_vulnerability|local_tool_or_deferred|`grype <directory>`|local filesystem directory|direct_signal_input|file|Directory path exists and is accessible; requires up-to-date DB||Scans FS with auto-detected catalog (slow without SBOM). Vulnerability DB must be present/up-to-date; results include package inventory and vulnerability matches.|
|software_vulnerability|local_tool_or_deferred|`grype sbom:<file>`|SBOM JSON or SPDX/CycloneDX file|direct_signal_input|file|SBOM file exists and valid; DB present/up-to-date||Requires a prior SBOM generation (e.g. via Syft). This is faster/more reliable than raw FS scan.|
|software_vulnerability|local_tool_or_deferred|`grype db update`|(N/A)|utility_only|–|Internet access (unless using local archive); triggers DB download||Updates local vulnerability DB; no signals produced.|
|software_vulnerability|local_tool_or_deferred|`grype explain`|JSON scan output (stdin)|enrichment_only|–|Requires piped JSON output; `--id` argument provided||Provides remediation context for a specific CVE from existing results; no new findings.|

### C. Signal Contract Table

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|software_vulnerability|software_vulnerability|grype|filesystem scan / SBOM scan|`vulnerability_detected`|software_security|medium|yes|Map provider severity: _Critical⇒high_, _High⇒medium_, _Medium⇒low_, else _info_ (e.g. Unknown/Negligible⇒low)|file|true_finding|`.matches` array has ≥1 element|`vulnerability.id`, `vulnerability.severity`, `vulnerability.namespace`, `fix.versions`, `fix.state`, `artifact.name`, `artifact.version`|`vulnerability.dataSource`, `vulnerability.description`, `vulnerability.cvss`, `vulnerability.risk`, `matchDetails`, `artifact.type`, `artifact.locations`|"Vulnerability {vulnerability.id} detected in {artifact.name} {artifact.version} (namespace {vulnerability.namespace})"|documented||Each vulnerability match produces one signal. The `artifact` fields link to the vulnerable package. Artifact fields (`artifact.name`, `artifact.version`) are inferred from output schema; vulnerability fields are documented. Severity mapping is Zima‐specific (CVE severity label is _input_). _Finding kind:_ true (actionable vulnerability).|

_Notes:_

- **Trigger logic:** Each element in the JSON `.matches` array corresponds to one `vulnerability_detected` signal. We trigger when `.matches` is non-empty (i.e. at least one vulnerability found).
- **Summary template:** Uses placeholders `{vulnerability.id}`, `{artifact.name}`, and `{artifact.version}` based on JSON fields.
- **Evidence vs Enrichment:** We treat `vulnerability.id`, severity, fix info, and artifact identity as core evidence (for deduplication and audit). Additional fields (descriptions, CVSS, risk, match details) are enrichment/context.
- **Evidence status:** All listed evidence fields are from documented JSON fields, except `artifact.name/version` which are inferred as standard Syft/Grype output fields.
- **Entity type:** We label the affected artifact as a `file` entity (i.e. path/package on disk).

### D. Confidence Guidance

|module|signal_type_or_use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|software_vulnerability|vulnerability_detected|**Moderate.** Grype uses official vulnerability feeds (NVD, distro, GitHub, etc.) to compile its DB, so individual reports are as reliable as those sources. Exact-direct/indirect matches from curated feeds are high-confidence; matches based only on generic CPE rules are less certain.|**Critical.** A stale DB (older than 5 days by default) can miss recent CVEs or use outdated severity. Ensure the DB is updated (or disable age-check) before trusting new scans.|Cross-check against other vulnerability scanners or sources (e.g. run Syft + Trivy) for high-value targets. Use SBOM vs raw FS: SBOM-backed scans generally yield more complete results (less missing packages).|Validate severity mapping (Critical⇒high etc.) with real-world data. Measure false-positive rate (e.g. due to CPE matches). Assess need to weight exact-match confidence vs CPE matches in final risk scores.|

_Notes:_

- **Source reliability:** Grype’s JSON output includes the match type, which correlates with confidence: `exact-direct-match` and `exact-indirect-match` (ecosystem feed hits) are reliable; `cpe-match` (NVD fallback) is noisier. A vulnerability marked _Critical_ by a trusted feed implies serious risk (Zima labels it at least High).
- **Freshness:** If operating in air-gapped mode, periodically refresh the DB (via `grype db update`) and note the scan date in signals. A DB older than the threshold should degrade confidence.
- **Corroboration:** Ideally, use Syft or similar to generate an SBOM as input (Grype is strongest when given a complete package inventory). For endpoint assets, cross-validate findings with OS vendor advisories or another scanner.
- **Calibration TODO:** Determine how often Grype’s severity labels map to our critical/high categories. For example, a CVSS9 vulnerability in a widely-used library may justify _High_ severity in Zima. Collect telemetry on which matches are most actionable to refine scoring.

### E. Provider Summary

- **Strongest signals:** Grype’s primary contribution is **software vulnerability detections** (CVEs/GHSAs etc.) in installed packages. It reports each vulnerability instance with contextual fix/version info.
- **Not for:** Do not use Grype for PII/credentials/identity threats or network scanning – it only finds package CVEs. Also, raw package inventory (the list of all installed packages) is contextual and should not by itself trigger a signal.
- **Cautions:** Grype runs locally and requires a periodic database update (default online every run). In offline environments, disable the 5-day age check or manually provision a DB. It requires filesystem read access on the target; scanning a full system may need elevated access. There are no rate limits or licensing fees (open-source). The vulnerability DB is stored as SQLite (in `~/.cache/grype/db/` by default). On each run Grype will auto-update the DB if possible; ensure this doesn’t conflict with workflow.
- **Roles by mode:**
    - **Signal-producing:** The scan mode (`grype <path>` or `grype sbom:...`) produces signals for each vulnerability found (direct_signal_input).
    - **Utility-only:** DB maintenance commands (`grype db update/check/delete`) are purely utility.
    - **Enrichment-only:** The `grype explain` command enriches an existing finding but produces no new signals.

{
  "provider": "grype",
  "provider_category": "tools",
  "provider_role": "local_tool_or_deferred",
  "module_mappings": [
    {
      "module": "software_vulnerability",
      "provider_role": "local_tool_or_deferred",
      "provider_method": "grype <directory>",
      "endpoint_or_artifact": "local filesystem directory",
      "classification": "direct_signal_input",
      "entity_types": ["file"],
      "gating_logic": "Directory exists and is readable; requires an up-to-date vulnerability DB【48†L216-L223】",
      "citation_refs": ["【4†L212-L218】【48†L216-L223】"],
      "notes": "Scans directory for packages (slow without prior SBOM). Vulnerability DB must be present or auto-downloaded【48†L216-L223】."
    },
    {
      "module": "software_vulnerability",
      "provider_role": "local_tool_or_deferred",
      "provider_method": "grype sbom:<file>",
      "endpoint_or_artifact": "SBOM JSON/SPDX/CycloneDX file",
      "classification": "direct_signal_input",
      "entity_types": ["file"],
      "gating_logic": "SBOM file exists and is valid; requires DB present/up-to-date【48†L216-L223】",
      "citation_refs": ["【4†L285-L294】【48†L216-L223】"],
      "notes": "Uses pre-generated SBOM (e.g. from Syft). Faster scan with complete inventory."
    },
    {
      "module": "software_vulnerability",
      "provider_role": "local_tool_or_deferred",
      "provider_method": "grype db update",
      "endpoint_or_artifact": "",
      "classification": "utility_only",
      "entity_types": [],
      "gating_logic": "Network access required (or a local DB archive); no findings output【48†L231-L239】",
      "citation_refs": ["【48†L231-L239】"],
      "notes": "Updates the vulnerability database; this is maintenance-only (no signals)."
    },
    {
      "module": "software_vulnerability",
      "provider_role": "local_tool_or_deferred",
      "provider_method": "grype explain",
      "endpoint_or_artifact": "JSON output from grype",
      "classification": "enrichment_only",
      "entity_types": [],
      "gating_logic": "Requires piped JSON input and a CVE ID; provides explanation text【51†L1521-L1529】",
      "citation_refs": ["【51†L1521-L1529】"],
      "notes": "Generates human-readable context for a given CVE using existing scan output."
    }
  ],
  "signal_contracts": [
    {
      "module": "software_vulnerability",
      "source": "software_vulnerability",
      "provider": "grype",
      "provider_method": "scan (filesystem/SBOM)",
      "signal_type": "vulnerability_detected",
      "category": "software_security",
      "severity": "medium",
      "severity_is_conditional": "yes",
      "conditional_rule": "Map provider severity: Critical⇒high, High⇒medium, Medium⇒low, else⇒info",
      "entity_type": "file",
      "finding_kind": "true_finding",
      "trigger_condition": ".matches array contains >=1 element",
      "evidence_fields": [
        "vulnerability.id",
        "vulnerability.severity",
        "vulnerability.namespace",
        "fix.versions",
        "fix.state",
        "artifact.name",
        "artifact.version"
      ],
      "enrichment_fields": [
        "vulnerability.dataSource",
        "vulnerability.description",
        "vulnerability.cvss",
        "vulnerability.risk",
        "advisories",
        "matchDetails",
        "artifact.type",
        "artifact.locations"
      ],
      "summary_template": "Vulnerability {vulnerability.id} detected in {artifact.name} {artifact.version} (namespace {vulnerability.namespace})",
      "evidence_status": "documented",
      "citation_refs": ["【43†L239-L247】【51†L1487-L1492】"],
      "notes": "Each match in the JSON output yields one signal. Artifact fields are inferred from Grype’s output schema; vulnerability fields (id, severity, fix) are documented【43†L239-L247】."
    }
  ],
  "confidence_guidance": [
    {
      "module": "software_vulnerability",
      "signal_type_or_use_case": "vulnerability_detected",
      "source_reliability": "Moderate (uses official feeds; exact-match is high-confidence, CPE-match is weaker)【43†L319-L328】【51†L1487-L1492】",
      "freshness_considerations": "Must keep DB updated (fails scans if >5 days old)【48†L216-L223】. Outdated DB risks missing CVEs.",
      "corroboration_rules": "Use SBOM/inventory (Syft) for better coverage. Cross-check with other scanners or vendor advisories on critical findings.",
      "calibration_todo": "Validate severity mappings and match-type confidence against real scan results. Adjust Zima severity rules if needed."
    }
  ]
}
