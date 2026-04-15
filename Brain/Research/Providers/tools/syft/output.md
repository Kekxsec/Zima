---
title: "output / tools / syft"
aliases: ["syft output", "syft signal registry"]
tags: [zima, research, outputs, signal-registry, tools, syft]
type: provider_research_output
provider: syft
provider_category: tools
status: complete
prompt_note: prompt.md
provider_folder: syft.md
obsidianUIMode: preview
kind: reference
llm_include: true
code_scope: backend
---

## Tool/API Surface Appendix

### Overview and OS support

Syft is a CLI tool and Go library that generates SBOMs for container images, filesystems, and archives, with multiple output formats including a native JSON schema, CycloneDX, and SPDX.

Official docs describe Syft as a single compiled executable with installation via shell script, Homebrew, and Winget, which implies official support for Linux, macOS, and Windows.

### Scan targets and source types

Official "Supported Scan Targets" and "Supported sources" docs plus the architecture page describe Syft's scan inputs as follows.

#### Scan target types (CLI / source type)

- Auto-detected target: syft <target> automatically infers whether <target> is an image, directory, file, or archive.

**Explicit --from / SYFT_FROM source specifiers:**

- docker, podman, containerd – use local container runtimes.
- docker-archive – tarball from docker save.
- oci-archive – tarball in OCI layout.
- oci-dir – on-disk OCI layout directory.
- singularity – Singularity Image Format file.
- dir – arbitrary directory path on disk.
- file – single file path on disk.
- registry – pull directly from remote registry, bypassing local runtimes.

The internal architecture resolves the source by trying File → Directory → OCI → Docker → Podman → Containerd → Registry, returning a source.Source + file resolver that is then cataloged into an sbom.SBOM object.

#### Relevance to software_inventory

- Container images (via runtimes, docker-archive, oci-*, registry) and local directories/files are directly relevant as software inventory sources for images and hosts.
- Singularity images are technically supported but likely lower priority for initial endpoint inventory support unless you have a Singularity-heavy environment.
- Archives that are not container images (generic tars/zip) can be scanned via directory or file targets plus Java/archive catalogers, but for endpoint inventory they are noisy and should usually be scoped or excluded.

### Package ecosystems and catalogers

The Syft module docs state that it "supports dozens of packaging ecosystems" including Alpine (apk), Debian (dpkg), RPM, Go, Python, Java, JavaScript, Ruby, Rust, PHP, .NET and more.

The official "Supported package ecosystems" page lists detailed catalogers and evidence for many ecosystems (Alpine APK, Debian/Ubuntu DPKG, RPM, Arch ALPM, Conda, Java, npm/yarn/pnpm, pip/Poetry, Go modules, RubyGems, Cargo, Composer, NuGet, CocoaPods, Homebrew, etc.), along with various binary classifiers.

A third-party but detailed review corroborates that Syft detects packages from major Linux distros and language ecosystems, automatically inferring which ecosystems are present from manifests and package databases.

Key implication: package presence is strongly evidenced by OS package DBs, language lockfiles, and binary signatures, but completeness depends on which catalogers are enabled and where those manifests live.

### Output formats and which to use

The official "Output Formats" guide defines the main formats:

- table – human-readable columnar summary (default).
- json – native Syft JSON, described as "complete data" and recommended when you need as much information as possible.
- purls – line-separated list of Package URLs for all packages.
- github-json – GitHub dependency snapshot JSON format.
- template – Go-template-driven custom output.
- text – row-oriented human/machine-friendly text.
- CycloneDX SBOMs: cyclonedx-json, cyclonedx-xml.
- SPDX SBOMs: spdx-json, spdx-tag-value.

Multiple formats may be emitted at once by using -o multiple times, and specific schema versions may be requested via -o <format>@<version>.

#### For Zima software_inventory:

- **Canonical ingestion format:** json (Syft native JSON) – contains artifacts, files, source, distro, relationships, descriptor, and schema.
- **Optional/utility:** CycloneDX JSON/SPDX JSON may be kept for interoperability or export, but their schemas are more complex and less directly aligned with Syft's internal package and location model; Zima should treat them as utility outputs, not the primary ingestion.
- **Out of scope for ingestion:** table, text, template, and github-json are best viewed as human-readable or tool-specific reports; purls is lossy and does not carry enough metadata (locations, distro, file links) for rich inventory.

### Syft JSON document and core schema

The official JSON schema reference (v16) defines the top-level Document and core types.

#### Document (SBOM) structure

**Fields:**

- artifacts: Array<Package> – list of discovered packages ("Artifacts is the list of packages discovered and placed into the catalog").
- artifactRelationships: Array<Relationship> – relationships among artifacts (e.g., contains, dependency-of).
- files: Array<File> – file artifacts when file catalogers are enabled.
- source: Source – description of the analyzed artifact (image, directory, file, etc.).
- distro: LinuxRelease – detected Linux distribution, when applicable.
- descriptor: Descriptor – metadata about Syft itself and configuration.
- schema: Schema – schema version and URL for validation.

#### Package (inventory unit)

Each Package represents a discovered software package:

**Core identifying fields:**

- id: str – unique ID within the SBOM.
- name: str – package name.
- version: str – package version.
- type: str – package type/ecosystem (e.g. rpm, deb, npm, apk, etc.).
- purl: str – Package URL identifier.
- language: str – language ecosystem where relevant.
- foundBy: str – cataloger that detected the package.

**Location and identifiers:**

- locations: Array<Location> – each with path, layerID, and optional accessPath and annotations, describing where on disk or in which image layer the package was found.
- cpes – CPE identifiers (array wrapper type).

**Licensing and metadata:**

- licenses – package license information, with value, SPDX expression, locations, etc.
- metadataType: str – identifies which ecosystem-specific metadata shape is in metadata.
- metadata: ... – many ecosystem-specific structs, e.g. Debian/DPKG, APK, Conda, Java archive details, etc.

#### Files and file metadata

File artifacts include:

- id: str, location: Coordinates, metadata: FileMetadataEntry, digests: Array<Digest>, licenses: Array<FileLicense>, executable: Executable, and optional contents.
- Coordinates include canonical path and layerID for container images or empty for directories/root filesystems.
- FileMetadataEntry includes mode, type (RegularFile, Directory, SymbolicLink, etc.), owner UID/GID, MIME type, and size.

#### Source and distro

**Source fields:**

- id, name (e.g., image name or directory path), version (e.g., tag), supplier, type (e.g. "image", "directory", "file"), and metadata.

**LinuxRelease fields** capture distribution information like id, versionID, prettyName, cpeName, idLike, etc.

#### Inventory-relevant vs enrichment fields

For software_inventory:

**Direct inventory evidence (should map into normalized records):**

Package.name, Package.version, Package.type, Package.purl, Package.language, Package.locations[].path, Package.locations[].layerID, Source.type, Source.name, Source.version, and possibly distro.id/distro.versionID.

**Enrichment/evidence but not primary keys:**

foundBy, licenses, cpes, metadataType, ecosystem-specific metadata, File artifacts and File.digests, Executable flags (e.g., ELF security features), and descriptor.configuration.

### Configuration, scope, and filters relevant to inventory

The Syft configuration reference documents numerous options that shape inventory coverage.

#### Output and format config

- output – list of output formats (e.g. ["syft-table"] by default); supports values like syft-json, spdx-json, etc., and can direct specific formats to files ("syft-json=<file>").
- Per-format settings such as JSON pretty flags and legacy JSON compatibility modes exist but mainly affect display/wire shape, not content.

#### Cataloger selection and package search

- catalogers, default-catalogers, select-catalogers – control which package/file catalogers run; defaults differ based on whether the source is an image or directory.
- package.search-unindexed-archives and package.search-indexed-archives toggle scanning of archives without/with indices (e.g., tar vs zip), currently applied notably to Java packages; enabling unindexed archive scanning can significantly increase workload.
- package.exclude-binary-overlap-by-ownership can drop synthetic binary packages when overlapping with "real" packages, reducing duplicate entries.

#### File and executable cataloging

- file.metadata.selection controls which files are captured: "all", "owned-by-package" (default), or "none".
- file.metadata.digests selects which hash algorithms to compute (md5, sha1, sha256, etc.).
- file.content.skip-files-above-size avoids scanning very large files for content (default 256000 bytes in the config snippet), and file.content.globs plus file.executable.globs restrict which files are candidates for content or executable analysis.

#### Scope, exclusions, base path

- scope – "selection of layers to catalog, options = [squashed all-layers deep-squashed]", with default squashed, meaning the view of the filesystem as seen in the final image layer.
- exclude – list of glob expressions (CLI --exclude or env SYFT_EXCLUDE) to omit paths from scanning (e.g., build output directories, caches).
- source.base-path – base directory for scanning; symlinks are not followed above this directory, and reported paths are relative to it.

#### Relationships, unknowns, and compliance

- relationships.package-file-ownership and relationships.package-file-ownership-overlap toggle package→file and package→package relationships inferred from file ownership overlap.
- unknowns.* controls whether to include unknown errors, executables without packages, and unexpanded archives in the SBOM.
- compliance.missing-name and compliance.missing-version specify what to do with packages missing required fields (e.g. drop or stub).

#### Implications for Zima

- Inventory completeness is bounded by scope, exclude, cataloger selection, and archive search options; overly broad scope with no excludes will be noisy and expensive, but aggressive excludes can silently drop installed software from view.
- For endpoint-style directory scans, Zima should encourage sensible source.base-path settings (e.g. true filesystem root or application root) and exclude patterns (e.g. transient build/output directories) to keep the inventory representative but tractable.

### Behavior / result variants

#### 1) Inventory present and parseable

When a scan completes successfully, Syft emits a JSON document with a valid schema.version, descriptor.name (e.g. "syft"), source.type, and typically some combination of artifacts, files, and distro.

Even a minimal SBOM with zero packages is structurally valid as long as the schema, descriptor, and source blocks are present.

#### 2) No packages discovered

The schema shows artifacts is an array; an empty array is allowed, so "no packages discovered" will be represented as artifacts: [] with other top-level metadata intact.

This can reflect genuine minimal images or directories, or lack of cataloger coverage; distinguishing those requires awareness of cataloger configuration and expected ecosystems.

#### 3) Partial inventory coverage

Options such as exclude, scope (e.g. squashed vs all-layers), archive search toggles, and per-ecosystem enrich flags (Java, JavaScript, Python, Go) can all affect which packages are discoverable.

For example, leaving package.search-unindexed-archives disabled avoids decompressing embedded archives, so any packages present only inside such archives may be missed, leading to partial coverage.

#### 4) Scope too broad / noisy

Scanning a whole host root (dir:/) with file.metadata.selection: all, unknowns.unexpanded-archives: true, and no exclude globs can generate large files and unknowns data sets as well as many binary classifiers, which is unwieldy for endpoint inventory.

For endpoint use, Zima should:

- Constrain base-path to the root or a specific application tree.
- Prefer file.metadata.selection: owned-by-package unless you deliberately want all filesystem files.
- Use exclude to avoid ephemeral or redundant areas (e.g., build caches, /proc, /sys, container runtimes).

#### 5) Unsupported target / malformed input

The scan-target docs list valid types and indicate that Syft "automatically detects" the type or allows explicit hints; there is no documented JSON representation for unsupported/malformed targets, which typically result in CLI errors instead of SBOMs.

For Zima, treat absence of a JSON document (or parsing failure) as "scan failed" handled entirely by the local runner/client rather than the mapper.

#### 6) Permission-limited / errorful scans

The JSON schema doesn't include a top-level error list; error handling is mainly at CLI/runtime level.

Zima should therefore detect permission/IO errors from the Syft process exit code, logs, or stderr, rather than expecting error fields in the SBOM; any truncated inventory must be inferred from configuration plus unexpected emptiness in ecosystems you expect to see.

### Inventory-relevant schema details (field-level)

**Target type / source type:** source.type (e.g., "image", "directory", "file") plus source.name and source.version identify the scanned asset (container image name:tag, path).

**OS/platform:** distro.id, distro.versionID, distro.cpeName, and distro.idLike give Linux distro identity, useful for tying inventory to platform.

**Package identity and ecosystem:** Package.name, version, type, and language define what software is present and which ecosystem it belongs to.

**Location / path:** Package.locations[].path and .layerID show where each package's evidence lives in the filesystem and in which container layer it appears; Coordinates.accessPath can differ from canonical path where symlinks/hardlinks exist.

**Identifiers:** purl and cpes are strong identifiers useful for cross-tool correlation but not strictly necessary for "package present" inventory; they are more valuable once you introduce vulnerability and posture modules.

**Licensing and hashes:** licenses, File.digests, Executable security flags, and other ecosystem-specific metadata are valuable enrichment for audits and forensic evidence but typically should not be used as primary keys in normalized inventory.

## Module Mapping Table

For this provider map, only software_inventory is a target module; other modules (vuln, posture, etc.) would consume the same SBOMs but are explicitly out of scope here.

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|--------|---|---|---|---|---|---|---|---|
| software_inventory | local_tool_or_deferred | syft_json (Syft -o json) | Container images via runtimes/archives/registry; local directories and files as scan sources | direct_signal_input (for inventory records) | hostname, container_image (derived) | Accept only well-formed Syft JSON documents where schema.version is present, descriptor.name identifies Syft, and source.type is one of "image", "directory", or "file"; treat artifacts as package inventory, files and distro as enrichment. | | Use this as the canonical software inventory input; later inventory DB and correlation logic decide what turns into alerts vs stored records. |
| software_inventory | local_tool_or_deferred | syft_cyclonedx_spdx (Syft -o cyclonedx-json, -o spdx-json) | Same scan sources as above, but SBOM serialized in industry formats | utility_only | hostname, container_image (derived) | Generate and optionally store for export/compliance use; do not parse into normalized inventory when Syft JSON is already available, to avoid redundant parsers and schema drift. | | Treat as export/interop only; rely on Syft JSON for internal normalization. |
| software_inventory | local_tool_or_deferred | syft_purls (Syft -o purls) | Same scan sources; package URL list only | utility_only | none (no standalone entity) | Optionally log or cache PURL lists to accelerate matching in other pipelines; do not use as a primary inventory source because it lacks location, distro, and source metadata. | | PURLs are valuable identifiers but lossy versus full JSON; best as supplemental utility. |

No other modules from your map should consume Syft directly in this pass; vulnerability and posture logic should consume normalized inventory and/or SBOMs from software_inventory rather than integrating Syft again.

## Signal Contracts Severity and Tags

### Design decision

For this pass, Syft is treated as:

- A primary evidence source for software inventory records; and
- A weak producer of standalone "signals" in your sense (security-relevant events).

Pure package presence generally does not justify emitting per-package signals; those belong in a normalized inventory store with later policy/vuln modules generating actionable findings (e.g. "forbidden_software_present", "vulnerable_package_present").

The only Syft-driven standalone signals that make sense at the module boundary today are scan-coverage/control-plane signals about inventory scans themselves (e.g. "scan completed", "scan returned zero packages"). These are low-impact (info severity) but important for measuring coverage.

Accordingly, the table below defines two conservative signal types; no per-package presence signals are created.

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|--------|--------|----------|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| software_inventory | software_inventory | syft | syft_json (Syft -o json) | software_inventory_scan_completed | software_inventory | info | no | n/a | hostname (or container_image; derived) | contextual_enrichment | A Syft JSON document is successfully parsed where schema.version is non-empty, descriptor.name identifies Syft, and source.type ∈ {"image","directory","file"} regardless of how many packages are in artifacts. | source (id, name, version, type), schema.version, descriptor.version, counts of artifacts, files, and artifactRelationships (derived from JSON). | distro (LinuxRelease), sample of artifacts fields (name, version, type, purl, locations.path), configuration hints from descriptor.configuration if present. | "Syft software inventory scan completed for {source.name} ({source.type}) with {artifacts_count} packages discovered." | derived | | Treats any structurally valid Syft JSON as a successful scan; exit code/IO errors should be handled before mapping. |
| software_inventory | software_inventory | syft | syft_json (Syft -o json) | software_inventory_scan_empty | software_inventory | info | yes | Elevate to low only if Zima has an independent expectation that software should be present (e.g. policy that a host must have specific agents) and Syft's config/capabilities cover those ecosystems. | hostname (or container_image; derived) | contextual_enrichment | Same as above, plus artifacts is present and len(artifacts) == 0. | Same as above plus explicit artifacts length. | Same as above. | "Syft software inventory scan for {source.name} ({source.type}) completed with no packages discovered." | derived | | Empty package lists may be legitimate (scratch/minimal images) or due to missing catalogers; severity remains info by default, with optional elevation through out-of-band policy. |

**No per-package signals** (e.g. package_present) are defined, because:

- Package existence alone isn't a risk; it only becomes meaningful once combined with policy, vulnerability, or posture rules.
- Turning every package into a signal would be extremely noisy and better handled as inventory rows in your internal datastore.

## Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|--------|---|---|---|---|---|
| software_inventory | software_inventory_scan_completed (Syft JSON) | High reliability that reported packages and metadata match disk/image contents within the configured scope, because Syft directly reads package DBs, manifests, and files. | Inventory is accurate only at scan time; subsequent package installs/upgrades/removals will not be captured until the next scan, so scans should be timestamped and scheduled appropriately. | Cross-check select packages or counts with OS package managers (e.g. dpkg -l, rpm -qa), language tools (pip list, npm list), or another SBOM/inventory tool where feasible, at least during initial calibration. | Empirically compare Syft inventories against OS/package manager inventories on representative hosts/images to quantify typical miss/false-positive rates and tune cataloger selection and exclude patterns accordingly. |
| software_inventory | software_inventory_scan_empty | High reliability that Syft did not find packages under current configuration, but lower confidence that no software exists if catalogers are incomplete or excludes are broad. | Staleness risk is similar: if a host/image changes after scan, an empty result may no longer be accurate; also, config drifts (e.g. adding excludes) can suddenly cause emptier inventories. | Treat empty inventories as informational unless another system (CMDB, package manager, or baseline SBOM) indicates there should be packages; use those baselines to confirm whether "empty" means "truly minimal" or "coverage gap". | For each major OS/app stack, assemble a small ground-truth set of images/hosts and intentionally misconfigure Syft (e.g., change exclude or catalogers) to observe when emptiness appears, then encode those patterns into posture/coverage checks. |
| software_inventory | General use of Syft JSON as inventory input | High per-record reliability for discovered packages (name, version, type, purl, locations) due to strong evidence sources (DBs, lockfiles, manifests). Completeness depends on cataloger coverage and configuration; new ecosystems require updated Syft versions and config review, so you should pin minimum Syft versions for supported stacks. | For critical assets, compare Syft SBOMs with at least one additional technique: OS-native inventory, configuration management data, or another SBOM tool, and ensure major packages match across tools before treating Syft as authoritative. | Track which ecosystems you rely on (e.g., Debian, RHEL+RPM, npm, pip, Maven) and regularly review the official "Supported package ecosystems" matrix to confirm cataloger support and adjust your own "supported inventory coverage" list. | |

## Implementation Notes

### Scan targets Zima should support first

**Priority 1 – Container images:** local daemons (docker, podman, containerd), docker-archive, oci-archive, oci-dir, and registry sources, as these are the most common SBOM use cases and map cleanly to container image entities.

**Priority 1 – Local directories (host or app tree):** dir sources representing host root or application roots for server/endpoint inventory.

**Priority 2 – Single files / specialized archives:** file targets and non-image archives for niche workflows (e.g., scanning a jar or zip directly).

### Canonical raw output schema to preserve

Treat Syft JSON v16 (or newer) as canonical and preserve these top-level blocks verbatim in raw evidence storage: artifacts, artifactRelationships, files, source, distro, descriptor, schema.

Within artifacts, preserve all fields for each Package, even if normalization only lifts a subset, so you can re-map later as catalogers evolve.

### Minimum fields for a stable software_inventory record

For each normalized software inventory row, at minimum:

- **Asset context:** a normalized asset key derived from source.type, source.name, and source.version (e.g., container image name:tag + registry, or host identifier + base path).
- **Package identity:** Package.name, Package.version, Package.type, and ideally Package.purl.
- **Location:** one canonical locations[].path plus associated layerID (for images) or indication that it is a host/directory path.
- **Ecosystem hints:** Package.language and/or metadataType to support ecosystem-specific logic later.
- Everything else (licenses, cpels, full metadata) is enrichment rather than a strict requirement for row creation.

### Mapping core vs enrichment fields

**Normalize into inventory:**

Asset identity (from source), package identity (name/version/type/purl), ecosystem (language), and primary location.

**Store as enrichment only:**

licenses, cpes, foundBy, ecosystem-specific metadata, File artifacts, Linux distro metadata, descriptor/configuration, and file digests/hardening features.

### Handling empty, partial, and filtered inventory

**Empty inventory (artifacts empty):**

Record the scan as completed but with zero packages; emit software_inventory_scan_empty and store descriptor.configuration, scope, and exclude settings (if available) as evidence to interpret emptiness later.

**Partial inventory:**

When you detect configurations that reduce coverage (e.g., many exclude globs, disabled archive search, custom cataloger lists), store those config fragments alongside the raw SBOM so downstream posture modules can evaluate coverage quality.

**Filtered scopes:**

For directory scans where source.base-path is not / or where excludes remove large directory trees, treat inventory records as scoped to that sub-tree, not the whole host.

### Duplicates, multiple locations, identifiers

Syft may report multiple locations per package, especially when the same package is spread across multiple directories or image layers.

For normalization:

- Choose a canonical location per package (e.g., first location, or one with a real path outside vendor directories) for the "primary" location field, but keep the full list as evidence for audits.
- Deduplicate packages by a composite key such as (asset_id, Package.purl) or (asset_id, name, version, type, primary_location) to avoid multiple rows for the same logical package.
- Keep purl and cpes for cross-tool correlation, but don't rely on them alone for uniqueness because some ecosystems may not have them or may change them across schema versions.

### Provider vs mapper vs correlation responsibilities

**Provider client (Syft runner):**

Run Syft with appropriate --from, --scope, --exclude, and cataloger configurations; handle process exit codes, stderr, and non-JSON failures; attach timestamps and execution metadata.

**Mapper (software_inventory):**

Validate and parse Syft JSON, derive asset identity from source, and transform each Package into normalized inventory rows, capturing canonical location and enrichment fields.

Emit only the two low-impact coverage signals defined above; leave higher-level risk in downstream modules.

**Correlation layer / other modules:**

Join inventory rows with vulnerability feeds, policy rules, posture checks, and other telemetry to create higher-severity signals (e.g., "forbidden_software_present", "vulnerable_package_not_patched"), possibly reusing PURLs and CPEs.

### Primary vs corroborating evidence source

Syft should be treated as a primary evidence source for software inventory where its catalogers support the ecosystem (as documented in the "Supported package ecosystems" matrix).

In stacks where Syft's capabilities are limited or newly added, treat it as a corroborating source alongside OS package managers, application-specific tools, or other SBOM generators until validated.

### Tags for defined signals

For the two defined signals, none of the provided tags (breach, stealer_log, malware, misconfiguration, etc.) accurately apply, because they are coverage/telemetry signals about inventory collection, not security incidents.

- **software_inventory_scan_completed:** no tag from the given list is appropriate; treat tag list as empty.
- **software_inventory_scan_empty:** only if posture logic later interprets emptiness as a misconfiguration should misconfiguration be applied, but that would be in another module's signal, not the bare Syft-derived event.

## Provider Summary and Structured JSON

### Strongest contributions

- High-fidelity, multi-ecosystem SBOM and package inventory for container images, directories, and files, with a well-documented JSON schema that maps cleanly into normalized software inventory records.
- Rich enrichment data (licenses, distro info, file hashes, binary security metadata) suitable for audits and for feeding other modules later, without forcing any risk scores at the Syft boundary.

### What Syft should not be used for in this module

- Direct vulnerability judgements, exploitability assessment, or threat scoring; Anchore explicitly positions Grype as the vulnerability scanner and Syft as SBOM generation.
- Direct policy/misconfiguration findings (e.g., "forbidden_software_present") without additional business logic or corroboration from posture modules.

### Local execution, privilege, scope, shape cautions

- Syft must run with filesystem and registry access sufficient to read package databases and manifests; restricted permissions can silently reduce coverage.
- Over-broad directory scopes with no exclude globs and aggressive file cataloging can produce very large SBOMs and performance overhead, especially on hosts; prefer carefully chosen base paths and excludes.
- JSON schema versions may evolve; Zima should track schema.version and be ready to adjust mappers for breaking changes, though core fields (name, version, type, locations, purl) are relatively stable.

### Overall treatment

For software_inventory, Syft is a mixed provider:

- Direct signal input for inventory records (primary evidence of software present).
- Utility-only for CycloneDX/SPDX and PURL-only outputs, which are mainly for export and interoperability.
- Low-impact signal producer for simple coverage telemetry (software_inventory_scan_completed / software_inventory_scan_empty), both info severity.

```json
{
  "provider": "syft",
  "provider_category": "tools",
  "provider_role": "local_tool_or_deferred",
  "module_mappings": [
    {
      "module": "software_inventory",
      "provider_role": "local_tool_or_deferred",
      "provider_method": "syft_json",
      "endpoint_or_artifact": "container images (via runtimes, archives, registry), local directories, and files",
      "classification": "direct_signal_input",
      "entity_types": ["hostname", "container_image"],
      "gating_logic": "Accept only well-formed Syft JSON documents where schema.version is present, descriptor.name identifies Syft, and source.type is one of 'image', 'directory', or 'file'. Use artifacts as package inventory and files/distro as enrichment.",
      "citation_refs": ["web:1", "web:8", "web:11", "web:18"],
      "notes": "Canonical inventory input; inventory DB and downstream modules decide what becomes an alert vs stored record."
    },
    {
      "module": "software_inventory",
      "provider_role": "local_tool_or_deferred",
      "provider_method": "syft_cyclonedx_spdx",
      "endpoint_or_artifact": "same scan sources, SBOM emitted as CycloneDX or SPDX",
      "classification": "utility_only",
      "entity_types": ["hostname", "container_image"],
      "gating_logic": "Generate and optionally archive for export/compliance; do not parse into normalized inventory when Syft JSON is available.",
      "citation_refs": ["web:11", "web:18"],
      "notes": "Interop/export only; avoids maintaining redundant parsers."
    },
    {
      "module": "software_inventory",
      "provider_role": "local_tool_or_deferred",
      "provider_method": "syft_purls",
      "endpoint_or_artifact": "same scan sources, output as PURL list only",
      "classification": "utility_only",
      "entity_types": [],
      "gating_logic": "Optional utility for fast lookups or correlation; not sufficient alone for inventory because location, distro, and source metadata are missing.",
      "citation_refs": ["web:18", "web:11"],
      "notes": "Best used as supplemental data in other pipelines, not as primary inventory."
    }
  ],
  "signal_contracts": [
    {
      "module": "software_inventory",
      "source": "software_inventory",
      "provider": "syft",
      "provider_method": "syft_json",
      "signal_type": "software_inventory_scan_completed",
      "category": "software_inventory",
      "severity": "info",
      "severity_is_conditional": "no",
      "conditional_rule": "",
      "entity_type": "hostname",
      "finding_kind": "contextual_enrichment",
      "trigger_condition": "A Syft JSON document is successfully parsed where schema.version is non-empty, descriptor.name identifies Syft, and source.type is one of 'image', 'directory', or 'file', regardless of artifacts length.",
      "evidence_fields": [
        "source.id",
        "source.name",
        "source.version",
        "source.type",
        "schema.version",
        "descriptor.version",
        "artifacts (count)",
        "files (count)",
        "artifactRelationships (count)"
      ],
      "enrichment_fields": [
        "distro",
        "artifacts[].name",
        "artifacts[].version",
        "artifacts[].type",
        "artifacts[].purl",
        "artifacts[].locations[].path",
        "descriptor.configuration"
      ],
      "summary_template": "Syft software inventory scan completed for {source.name} ({source.type}) with {artifacts_count} packages discovered.",
      "evidence_status": "derived",
      "citation_refs": ["web:11", "web:18"],
      "notes": "Pure coverage/telemetry event; no inherent risk."
    },
    {
      "module": "software_inventory",
      "source": "software_inventory",
      "provider": "syft",
      "provider_method": "syft_json",
      "signal_type": "software_inventory_scan_empty",
      "category": "software_inventory",
      "severity": "info",
      "severity_is_conditional": "yes",
      "conditional_rule": "May be elevated to low severity by separate posture/policy modules if there is independent evidence that software should be present and Syft is correctly configured to see it.",
      "entity_type": "hostname",
      "finding_kind": "contextual_enrichment",
      "trigger_condition": "Syft JSON document meets the scan_completed conditions and artifacts is present with length equal to 0.",
      "evidence_fields": [
        "source.id",
        "source.name",
        "source.version",
        "source.type",
        "schema.version",
        "descriptor.version",
        "artifacts (count=0)"
      ],
      "enrichment_fields": [
        "distro",
        "descriptor.configuration",
        "cataloger and scope-relevant settings if available"
      ],
      "summary_template": "Syft software inventory scan for {source.name} ({source.type}) completed with no packages discovered.",
      "evidence_status": "derived",
      "citation_refs": ["web:11", "web:22", "web:26"],
      "notes": "Empty inventories are often legitimate (e.g. scratch images); treat as info unless corroborating data indicates a coverage issue."
    }
  ],
  "confidence_guidance": [
    {
      "module": "software_inventory",
      "signal_type_or_use_case": "software_inventory_scan_completed (Syft JSON)",
      "source_reliability": "High reliability that reported packages and metadata match the scanned artifact within the configured scope, due to direct parsing of package DBs, manifests and files by catalogers.",
      "freshness_considerations": "Inventory reflects software state only at scan time; changes between scans are not captured. Scans should be timestamped, and scheduling should match how dynamic each asset is.",
      "corroboration_rules": "For representative assets, compare Syft inventories against OS package managers and language tools to verify major package sets align before treating Syft as authoritative.",
      "calibration_todo": "Run side-by-side comparisons on key stacks (Debian, RHEL, Alpine, Java, Node, Python) to measure typical discrepancies and tune cataloger and exclude settings accordingly."
    },
    {
      "module": "software_inventory",
      "signal_type_or_use_case": "software_inventory_scan_empty",
      "source_reliability": "High confidence that Syft found no packages under current configuration, but incomplete confidence that no software exists when catalogers or excludes may hide packages.",
      "freshness_considerations": "An empty result can become stale quickly on mutable hosts or images; config drift (e.g. new excludes) may also create empty inventories where previous scans had packages.",
      "corroboration_rules": "Cross-check empty results against expectations from CMDB/baselines or OS package managers; treat discrepancies as potential coverage issues rather than trusting emptiness blindly.",
      "calibration_todo": "Deliberately misconfigure Syft on test assets (e.g. adjust excludes, catalogers, scope) to observe when empty SBOMs occur, and capture those patterns into posture/coverage heuristics."
    },
    {
      "module": "software_inventory",
      "signal_type_or_use_case": "General use of Syft JSON as inventory input",
      "source_reliability": "Per-record reliability is high for ecosystems with dedicated catalogers; presence evidence is strong when tied to package DBs or lockfiles, while absence is weaker unless coverage is carefully constrained.",
      "freshness_considerations": "Ensure Syft versions and supported ecosystems match your use cases; new languages or OSes may not be fully covered until you upgrade.",
      "corroboration_rules": "Use at least one alternative inventory method on high-value assets (native package tools, another SBOM generator, or config management data) to validate Syft-based records.",
      "calibration_todo": "Track which ecosystems are considered 'supported for inventory' based on the official capabilities matrix and your own testing, and periodically re-evaluate as Syft evolves."
    }
  ]
}
```
