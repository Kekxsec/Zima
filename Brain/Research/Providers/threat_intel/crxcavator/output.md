---
title: "output / threat_intel / crxcavator"
aliases: ["crxcavator output", "crxcavator signal registry"]
tags: [zima, research, outputs, signal-registry, threat_intel, crxcavator]
type: provider_research_output
provider: crxcavator
provider_category: threat_intel
status: complete
prompt_note: prompt.md
provider_folder: crxcavator.md
obsidianUIMode: preview
kind: reference
llm_include: true
code_scope: backend
---

CRXcavator integration design for Zima extension_risk module
Overview
CRXcavator is a Duo / Cisco service that continuously scans browser extension ecosystems (originally the Chrome Web Store) and assigns objective risk scores to extensions based on permissions, vulnerable third‑party JavaScript, content security policy (CSP) strength, web store metadata, and other criteria.
 The public API exposes per‑extension reports with a numerical total risk score and component scores for CSP, permissions, RetireJS vulnerabilities, metadata, and web store information, which are consumed by several third‑party tools and integrations.
 For Zima, the primary integration surface is the per‑extension report endpoint at https://api.crxcavator.io/v1/report/{extension_id}/{version}?platform={Chrome|FireFox|Edge}, which provides structured risk metrics under data.risk.* and is suitable as a direct signal producer for the extension_risk module.

The sections below document the observable API surface, map it to Zima’s extension_risk module, define initial signal contracts and severity logic, and capture implementation notes and confidence guidance. Where schema details are inferred from third‑party clients rather than official docs, this is called out explicitly.

## API Surface Appendix
1. GET /v1/report/{extension_id}/{version}?platform={platform}
Source of truth

PowerShell module BrowserExtensionRisk.psm1 calls https://api.crxcavator.io/v1/report/$ExtensionID/$ExtensionVersion?platform=$ExtensionPlatform and parses JSON via ConvertFrom-Json.

LogicHub / DevoSOAR "Get Report" action describes output as a JSON object containing an "Extension report".

Multiple community pipelines (Logstash, etc.) use https://api.crxcavator.io/v1/report/%{identifier}/%{version} for enrichment.

Purpose
Return a detailed risk report for a specific extension ID, version, and browser platform (Chrome, Firefox, Edge).

HTTP details (observable)

Method: GET (inferred from usage in PowerShell and Logstash examples).

Path: /v1/report/{extension_id}/{version}.

Query parameters:

platform (required in PowerShell client; values validated as FireFox, Chrome, Edge).

Supported entity types

extension_id – 32‑character Chrome/Chromium style extension identifier (letters only for Chrome IDs), also used for Edge and Firefox in third‑party tooling.

Version string (semantic version from manifest, e.g. 12.4.0, 5.0.4169.0628).

Platform enum (Chrome, FireFox, Edge) in query string.

Authentication / access

The mrxcavator client and Polarity integration are configured with a CRXcavator "API key", implying key‑based auth exists at least for some operations.

The PowerShell example calls the report endpoint without explicit auth headers; this may indicate a public unauthenticated tier, but this is not documented and must be confirmed against official docs.

Status: Authentication requirements and header names are unknown and must be obtained from https://crxcavator.io/docs.html#/report_breakdown or equivalent official documentation.

Top‑level response structure (observable)

From the PowerShell client:

The parsed response is bound to $CRXRiskDetails and accessed as:

$CRXRiskDetails.data.risk.total

$CRXRiskDetails.data.risk.csp.total

$CRXRiskDetails.data.risk.permissions.total

$CRXRiskDetails.data.risk.retire.total

$CRXRiskDetails.data.risk.webstore.total.

From Kolide’s device inventory schema (which stores the full CRXcavator JSON report and also denormalizes selected fields):

They expose:

crxcavator_report – "The full CRXcavator JSON report" (JSONB column).

crxcavator_risk_csp_total

crxcavator_risk_metadata_total

crxcavator_risk_permissions_total

crxcavator_risk_retire_total

crxcavator_risk_total

crxcavator_risk_webstore_total

crxcavator_updated_at.

Combining these, the following CRXcavator fields can be treated as documented/observed:

data (object) – root of report payload used by clients.

data.risk (object) – aggregate risk data.

data.risk.total (integer) – total risk score combining individual components.

data.risk.csp.total (integer) – CSP risk sub‑score.

data.risk.permissions.total (integer) – permissions risk sub‑score.

data.risk.retire.total (integer) – RetireJS vulnerability risk sub‑score.

data.risk.webstore.total (integer) – Chrome Web Store metadata risk sub‑score.

data.risk.metadata.total (integer) – metadata risk sub‑score (directly implied by crxcavator_risk_metadata_total).

Other parts of the JSON (e.g., extension metadata, CSP rule details, permission lists, external call hosts) are known conceptually from CRXcavator’s UI and CLI output, but their exact field paths are not visible in public client code and should be treated as unknown / inferred until confirmed in official docs.

Presence / optionality

data.risk.total appears to be present and numeric whenever a report exists for the requested {extension_id, version, platform}.

All five component totals (csp, permissions, retire, webstore, metadata) are treated as present in third‑party consumers; they may be zero when a dimension does not contribute risk, but are assumed to exist as integers.

Whether data or data.risk can be absent is not documented; LogicHub documents error handling at its wrapper level (has_error, error fields) rather than raw API behavior.

Response variants (observable / inferred)

Successful hit (report exists):

HTTP status presumed 200 (not explicitly documented, but standard for similar APIs).

JSON body with data.risk.* populated as above, and additional report metadata under data (schema unknown).

Invalid extension or version / report missing:

LogicHub’s wrapper returns e.g. { "error": "Invalid Extension ID", "has_error": true } with no result.

Raw CRXcavator behavior is undocumented; it may return HTTP 4xx or a JSON error object. Treat as unknown and guard for non‑2xx and non‑JSON responses.

Partial / limited result:

No explicit handling documented. Since risk totals exist for all major dimensions in third‑party use, partial results are likely rare, but cannot be ruled out.

Common error cases (inferred):

Invalid extension ID format (not 32‑char, wrong character set).

Non‑existent extension or version (e.g., removed from store).

Unsupported platform value.

Rate limiting or quota (noted generically in Public API directories; details unknown).

Example response fragments (derived from consumers)

PowerShell script usage:

powershell
$CRXRiskDetails = Invoke-WebRequest $Uri | ConvertFrom-Json
$CRXRiskDetails.data.risk.total
$CRXRiskDetails.data.risk.csp.total
$CRXRiskDetails.data.risk.permissions.total
$CRXRiskDetails.data.risk.retire.total
$CRXRiskDetails.data.risk.webstore.total
Kolide column mapping (denormalized from crxcavator_report JSON):

text
crxcavator_risk_csp_total          -> CSP sub-score
crxcavator_risk_metadata_total     -> Metadata sub-score
crxcavator_risk_permissions_total  -> Permissions sub-score
crxcavator_risk_retire_total       -> RetireJS sub-score
crxcavator_risk_total              -> Total risk score
crxcavator_risk_webstore_total     -> Webstore sub-score
crxcavator_report                  -> Full JSON report
crxcavator_updated_at              -> Last update time
Documentation status

Field names under data.risk.* are derived from code using the official endpoint and can be treated as stable unless contradicted by CRXcavator docs.

Other report fields (e.g., extension name, description, rating, external calls, CSP directive breakdowns, permission lists) are inferred from the CRXcavator UI and CLI output and must be verified against https://crxcavator.io/docs.html#/report_breakdown before being used in tight field‑level logic.

2. GET /v1/report/{extension_id}
Source of truth (third‑party only, inferred)

A community script crxcagrepper.py downloads "multiple versions of Chrome extension source from crxcavator.io" using:

python
r = requests.get(report_url + extension)
data = json.loads(r.text)
for ext in data:
    versions.append(ext['version'])
where report_url is defined earlier as a base URL ending with /report/.

This strongly suggests an endpoint that, given an extension_id, returns a list of version records, each including at least a version field and probably associated risk and metadata.

Purpose (inferred)
Return historical reports for all known versions of a given extension, enabling retrieval of older versions and their risk scores.

HTTP details (inferred)

Method: GET (from requests.get).

Path: /v1/report/{extension_id} (base path inferred from widespread use of /v1/report/{id}/{version} and the script’s concatenation semantics).

Query parameters: none observed.

Supported entity types

extension_id (same semantics as above).

Authentication / access

Unknown; likely same auth model as version‑specific report, but must be confirmed.

Top‑level response structure (inferred)

Response is parsed into a Python list: for ext in data: ..., implying the root JSON is an array of objects.

Each object has at least a version field (string).

Additional fields (e.g., risk totals, timestamps) are not shown; treat as unknown.

Response variants

Successful hit: list of version records (possibly empty).

No known versions / invalid ID: behavior unknown; assume potential HTTP 4xx or empty list and guard accordingly.

Documentation status

Entirely inferred from third‑party script, not directly documented in official CRXcavator docs. Use only as an optional enrichment endpoint (e.g., risk history) after verifying existence and behavior in staging.

3. UI / miscellaneous and aggregator endpoints (out of scope for signals)
Several sources mention additional capabilities or endpoints, but they are not clearly documented or are likely UI‑only:

CRXcavator web UI at https://crxcavator.io/report/{extension_id}/{version} renders a detailed HTML report, including CSP directive breakdowns, RetireJS findings, permissions lists, external calls, Facebook ThreatExchange checks, and related extensions.

The mrxcavator CLI offers commands to

submit extensions (--submit, --submit_all),

retrieve reports (--report, --report_all, --report_all_table),

graph risk over time (--graph), and

query VirusTotal for external call hostnames (--virustotal).

These map to internal CRXcavator and VirusTotal APIs but the exact CRXcavator paths and schemas (e.g., submission or history endpoints) are not visible.

Public API aggregators (PublicAPI.dev, FindAPIs, JSONAPI) list endpoints such as /extension/{extension_id}, /search?query=..., or /vulnerabilities/{extension_id}, but with inconsistent base URLs and obvious placeholder content; treat these as non‑authoritative and avoid depending on them for implementation.

Given the lack of stable, documented paths and schemas, these endpoints should be considered out of scope for initial Zima signal generation and used only as optional enrichers once verified directly against CRXcavator’s official documentation and a live API.

## Module Mapping Table
module	provider_role	provider_method	endpoint_or_artifact	classification	entity_types	gating_logic	citation_refs	notes
extension_risk	signal_producer	check(extension_id, version, platform)	GET https://api.crxcavator.io/v1/report/{extension_id}/{version}?platform={Chrome|FireFox|Edge}	direct_signal_input	extension_id	Require valid extension_id (Chrome/Chromium style), known version string, and platform in {Chrome, FireFox, Edge}. Only proceed if HTTP response is 2xx and JSON parses with numeric data.risk.total.
Primary integration surface. Per‑extension risk totals map directly to Zima browser_extension_risk signals. Low‑risk outputs may be used as enrichment only (see severity/gating).
extension_risk	enrichment_only	get_versions(extension_id)	GET https://api.crxcavator.io/v1/report/{extension_id} (inferred)	enrichment_only	extension_id	Optional. Use only if endpoint existence and schema confirmed. Limit to risk history enrichment; do not emit standalone signals purely from this history list.
Endpoint inferred from community script; treat as best‑effort enrichment for historical risk trending, not as a core dependency.
No other CRXcavator endpoints are recommended for Zima at this stage. Submission and search functions are oriented toward CRXcavator’s own backend workflows or UI and do not provide additional actionable security findings beyond the per‑version risk reports.

## Signal Contracts, Severity, and Tags
Selected signal types
Given CRXcavator’s scope as a posture‑level analyzer rather than an incident detector, the integration should focus on a single normalized signal type capturing overall extension risk, with severity conditional on the numerical risk score. More granular findings (e.g., specific dangerous permissions or weak CSP directives) can be layered in later once official field‑level schemas are available.

module	source	provider	provider_method	signal_type	category	severity	severity_is_conditional	conditional_rule	entity_type	finding_kind	trigger_condition	evidence_fields	enrichment_fields	summary_template	evidence_status	citation_refs	notes
extension_risk	extension_risk	crxcavator	GET /v1/report/{extension_id}/{version}?platform={platform}	browser_extension_risk	endpoint_security	medium	yes	Map severity from numeric risk score derived from data.risk.total: low for clearly low risk scores, medium for moderate risk, high for top‑tier risk; do not use critical because CRXcavator measures posture, not confirmed compromise. Initial numeric thresholds can reuse the PowerShell client’s low/medium/high bands (≤377, 378–478, >478) as a starting point, but must be recalibrated on real fleet data.	extension_id	true_finding	Create a signal whenever a valid report exists and data.risk.total is present and non‑null. Optionally gate out very low‑risk extensions (e.g., those falling into the lowest band) if noise is excessive; treat them as enrichment‑only.	data.risk.total; data.risk.csp.total; data.risk.permissions.total; data.risk.retire.total; data.risk.webstore.total; data.risk.metadata.total (inferred)	Full raw CRXcavator JSON report (stored as opaque blob); any additional documented sub‑objects once schema is confirmed (e.g., detailed CSP issues, permission lists, RetireJS vulnerability list, web store metadata).	"Browser extension {{extension_id}} (version {{version}} on {{platform}}) has CRXcavator total risk score {{data.risk.total}} (CSP={{data.risk.csp.total}}, permissions={{data.risk.permissions.total}}, RetireJS={{data.risk.retire.total}}, webstore={{data.risk.webstore.total}})."	data.risk.* totals are documented/observed via third‑party code using the official endpoint; metadata.total is derived from external column mapping; all other JSON fields are currently unknown and must be confirmed.
Severity mapping should not elevate to critical, as CRXcavator does not detect active compromise. Treat endpoint_security as a new Zima category focusing on browser/endpoint extension posture. Thresholds are imported from a third‑party PowerShell client and serve only as calibration seeds.
Notes on signal type and category

signal_type = browser_extension_risk is intentionally generic and vendor‑agnostic; other extension‑risk providers can map to the same internal concept.

category = endpoint_security is recommended as the best‑fit domain for browser extension posture. Browser extensions are part of endpoint configuration and can impact identity, SaaS, and data security, but the primary control surface is the browser itself.

## Confidence Guidance
Severity calibration for browser_extension_risk
Available risk indicators

Total numeric risk score: data.risk.total.

Component sub‑scores:

data.risk.csp.total – weak or missing CSP controls in extension code.

data.risk.permissions.total – powerful or excessive permissions requested in the extension manifest.

data.risk.retire.total – use of vulnerable third‑party JavaScript libraries detected via RetireJS.

data.risk.webstore.total – issues in Chrome Web Store metadata such as missing privacy policy or outdated version.

data.risk.metadata.total – risk from embedded extension metadata (inferred).

CRXcavator’s own scoring is posture‑oriented: it quantifies how risky an extension could be based on its capabilities and hygiene, not whether it has already been compromised or abused. This aligns with Zima’s medium/high severity definitions (suspicious/high‑risk posture, potential for compromise), but usually not with critical, which is reserved for direct credential exposure, active stealer logs, or live C2.[

]

Observed third‑party thresholding

The BrowserExtensionRisk PowerShell module classifies CRXcavator’s data.risk.total as:

Low: total ≤ 377

Medium: total 378–478

High: total > 478.

These thresholds are not official CRXcavator semantics but represent one reasonable partitioning of the score range in the wild.

Recommended initial mapping (to be calibrated)

For the single browser_extension_risk signal type:

High severity

Conditions (derived):

data.risk.total above an initial high threshold (e.g., > 478 as per PowerShell bands).

Or data.risk.permissions.total and/or data.risk.csp.total dominate the score, indicating broad data access and weak isolation.

Justification: extensions with powerful permissions (e.g., access to all URLs, cookies, webRequest, activeTab) and weak CSP provide a clear avenue for account takeover, data exfiltration, or abuse if compromised, which matches Zima’s "high" definition for exposed SaaS/identity surfaces, albeit without evidence of actual exploitation.

Medium severity

Conditions (derived):

data.risk.total in a mid‑range band (e.g., 378–478 per existing bands), or

data.risk.retire.total is non‑zero (vulnerable JS libraries present) but CSP/permissions scores are moderate.

Justification: indicates meaningful security weaknesses and elevated risk but not as extreme as the top tier; aligns with "suspicious activity / reputation degradation" in Zima’s calibration.

Low severity

Conditions (derived):

data.risk.total in the lowest band (≤ 377) or only minor metadata/webstore issues.

Justification: mostly informational risk posture issues (e.g., missing privacy policy, outdated metadata) with limited immediate exploitation risk.

Info only (no signal)

Optional gating rule:

For very low scores or purely metadata/webstore‑driven risk, Zima may choose not to emit a standalone signal and instead store CRXcavator data as enrichment for other alerts (e.g., extension found on a high‑value host).

Critical severity

Recommendation: Do not assign critical for any CRXcavator‑only finding in initial implementation.

Rationale: CRXcavator does not directly observe passwords, credentials, or active exploitation; it scores potential risk. Even extremely permissive, poorly secured extensions represent high but not guaranteed compromise. Reserving critical for confirmed compromise or direct data exposure aligns with Zima’s severity guidance.

Assessment of initial scaffold

The user’s "no provider‑specific stripped note" means there was no prior calibration; the above mapping constitutes a first pass built strictly from documented/observed numeric fields and narrative descriptions of what CRXcavator measures.

## Implementation Notes
Confidence considerations per use case
module	signal_type_or_use_case	source_reliability	freshness_considerations	corroboration_rules	calibration_todo
extension_risk	browser_extension_risk (per‑extension report)	CRXcavator is maintained by Duo / Cisco and continuously scans extension ecosystems, giving it strong coverage and a well‑understood scoring model. However, field‑level schemas are only partially documented via third‑party clients, so confidence in data.risk.* numerical semantics is high, but confidence in the structure of other sub‑objects is currently medium.	CRXcavator scans the Chrome Web Store on an ongoing basis (originally every three hours) and keeps risk scores up to date with extension updates; however, update cadence and coverage for Edge/Firefox must be validated. Use any updated_at or equivalent timestamp fields (exposed indirectly as crxcavator_updated_at in Kolide) to track staleness and consider down‑weighting or suppressing very old reports.	Corroborate high CRXcavator scores with: (1) local telemetry showing installation of the extension on endpoints, (2) extension permissions from browser inventory, and (3) any vendor advisories or CVEs tied to the extension. Use CRXcavator primarily as a risk‑scoring augment to endpoint/identity signals rather than as a standalone incident detector.	1) Confirm full JSON schema from official docs (especially extension metadata, CSP and permission breakdowns). 2) Collect distribution of data.risk.total across a representative fleet to tune severity thresholds and noise gating. 3) Validate consistency between risk scores across platforms for the same extension. 4) Decide whether to always emit a signal on any non‑zero risk or only above medium/high thresholds.
extension_risk	Historical risk (GET /v1/report/{extension_id}, inferred)	The existence and semantics of the historical report endpoint are derived from a single community script and not officially documented; treat reliability of this endpoint and its fields as low until verified in a lab environment.	Historical risk is useful for understanding when an extension became risky (e.g., a version jump adding permissions) but is not time‑sensitive in the same way as live compromise. Ensure any timestamps or version ordering are parsed correctly and avoid relying on this history for real‑time decisions until staleness semantics are well understood.	Use historical risk only to enrich an existing browser_extension_risk signal or an endpoint detection indicating this extension is present. Do not create signals solely from historical data (e.g., "extension was risky in past versions") without corroborating installed versions.	1) Verify that /v1/report/{extension_id} exists and returns a version list with consistent structure. 2) Determine which fields (e.g., version, release date, risk_total) are present per element. 3) Decide whether to store full history or a compressed summary (min/avg/max risk over time) in Zima’s enrichment layer.
F. Tags
For the browser_extension_risk signal type, the following tags from the provided set are appropriate, depending on context and downstream correlation:

saas (out of provided list this is the closest but not literally present; if restricted to the explicit list, use pii_exposure and credential_stuffing as conditional tags instead). Since the instruction says not to force ill‑fitting categories, tags below focus on available list.

Recommended tags (from allowed set):

pii_exposure – many high‑risk extensions can access browsing data, form inputs, and SaaS app content, exposing PII if abused.

credential_stuffing – permissive extensions with password manager hooks or form access increase the blast radius of credential theft, indirectly raising credential‑stuffing risk.

malware – while CRXcavator is not strictly malware detection, highly risky extensions are often a precursor or vehicle for malware and adware; use cautiously and consider only when combined with other telemetry.

Suggested base tag list for all CRXcavator‑derived browser_extension_risk signals:

pii_exposure

credential_stuffing

Optionally, add malware for the highest‑risk band once there is evidence of malware‑like behavior or when correlated with other threat intel.

G. Implementation Notes
1. Field paths and parsing
Treat data.risk.total and the five known component totals as the only schema‑stable fields for the initial integration; all other fields should be passed through as opaque enrichment until confirmed from official docs.

The PowerShell script demonstrates that data is the top‑level object holding the report and data.risk.* are numeric; Zima’s client should mirror this access pattern and avoid assuming any particular nesting structure for other keys.

Because third‑party platforms like Kolide persist the entire CRXcavator JSON under a single crxcavator_report column, Zima can safely store the raw JSON blob as evidence.raw and only parse data.risk.* for now.

2. Null / empty / no‑hit behavior
LogicHub’s wrapper returns { "error": "Invalid Extension ID", "has_error": true } when the request fails; Zima’s provider client must detect non‑2xx HTTP responses and non‑JSON bodies and convert them into a clean "no data" result without emitting a signal.

If JSON parses but data or data.risk.total is missing or non‑numeric, the client should treat this as a soft failure / schema drift and log telemetry rather than attempting to compute severity.

For numerical fields like data.risk.csp.total, treat missing fields as unknown rather than zero; only zeros explicitly present in JSON should be interpreted as "no risk" for that dimension.

3. Rate limits, billing, licensing
Public API directories suggest CRXcavator has a public/free API with some form of authentication and possible rate limits, but provide no concrete numbers.

The mrxcavator CLI warns that VirusTotal enrichment "requires throttling" but does not mention CRXcavator throttling; however, production use in Zima should assume practical rate limits and implement client‑side backoff and caching.

Licensing terms and enterprise usage limits must be checked directly with Duo / Cisco; treat CRXcavator as an external SaaS dependency.

4. Deduplication keys / natural identifiers
Natural key for CRXcavator reports: {extension_id, version, platform}.

Within Zima, deduplicate browser_extension_risk signals on:

entity_type = extension_id

entity = extension_id value

version (from request parameters or report metadata, once confirmed)

platform

plus a hash of data.risk.* to avoid re‑emitting when scores have not changed.

5. Raw evidence for remediation and audit
Persist raw CRXcavator response JSON exactly as returned for:

auditability of risk assessment decisions,

future schema expansion (e.g., once CSP directive lists and explicit permission names are parsed), and

correlation with browser telemetry (e.g., matching permissions from manifest to those flagged by CRXcavator).

At minimum, ensure data.risk.* integers are preserved as first‑class evidence fields in Zima’s normalized signal.

6. Client vs mapper vs correlation responsibilities
Provider client layer (crxcavator client):

Handle HTTP transport, authentication, retries, and basic error handling.

Validate and parse JSON, extracting data.risk.* and preserving the raw blob.

Implement rate‑limit backoff and optional local caching of {extension_id, version, platform} lookups.

Module mapper (extension_risk mapper):

Convert data.risk.* into normalized Zima signal fields (severity, evidence, tags).

Apply severity thresholds and gating rules (e.g., emit signals only above a medium threshold; tag pii_exposure/credential_stuffing).

Populate summary_template values using extension_id, version, platform, and the numeric risk fields.

Correlation layer:

Join CRXcavator risk signals with endpoint/browser inventory (list of installed extensions per device/user) to prioritize high‑risk extensions actually present in the environment.

Correlate with identity/SSO events and data exfiltration telemetry to escalate from "high‑risk posture" to more serious incidents if abuse indicators appear.

## Provider Summary and Structured JSON
Strongest signal types

High‑quality, vendor‑maintained numerical risk scores for browser extensions (data.risk.total plus CSP, permissions, RetireJS, webstore, and metadata sub‑scores) that quantify extension posture and are already consumed by multiple security tools.

Breadth of coverage via continuous scanning of popular extension ecosystems, making CRXcavator well suited as a central risk oracle for the extension_risk module.

What the provider should not be used for

Not a direct breach detector: CRXcavator does not observe active exploitation, credential dumps, or stealer logs; it should not be used to raise critical severity incidents on its own.

Not a general threat intel feed for domains/IPs: external call hosts and similar metadata can support enrichment, but they do not replace specialized threat intel or sandboxing tools.

API/auth/rate‑limit/licensing cautions

Authentication model, rate limits, and enterprise licensing are not fully documented in public sources and must be clarified directly with Duo / Cisco; Zima’s client must be designed for backoff and caching to avoid API abuse.

Schema for fields beyond data.risk.* is currently inferred; any logic using deeper nested objects (e.g., specific permissions or CSP directives) must be gated behind explicit schema validation and version pinning.

Role in Zima’s current stage

CRXcavator should be treated as a signal‑producing provider for the extension_risk module, emitting normalized browser_extension_risk signals with conditional severity based on numeric risk scores.

Additional endpoints/historical data should be considered enrichment‑only until officially verified; they can enhance prioritization and investigation but should not create independent signals.

```json
{
  "provider": "crxcavator",
  "provider_category": "threat_intel",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "extension_risk",
      "provider_role": "signal_producer",
      "provider_method": "check(extension_id, version, platform)",
      "endpoint_or_artifact": "GET https://api.crxcavator.io/v1/report/{extension_id}/{version}?platform={Chrome|FireFox|Edge}",
      "classification": "direct_signal_input",
      "entity_types": ["extension_id"],
      "gating_logic": "Require syntactically valid extension_id, known extension version string, and platform in {Chrome, FireFox, Edge}. Only proceed if HTTP response is 2xx and JSON parses with numeric data.risk.total.",
      "citation_refs": [
        "https://www.powershellgallery.com/packages/BrowserExtensionRisk/0.0.1/Content/BrowserExtensionRisk.psm1",
        "https://help.logichub.com/docs/crxcavator",
        "https://github.com/mstanislav/mrxcavator",
        "https://www.kolide.com/features/device-inventory/properties/device-chrome-extensions"
      ],
      "notes": "Primary integration surface. Per-extension risk totals under data.risk.* feed normalized browser_extension_risk signals. Lowest-risk outputs can optionally be treated as enrichment-only to reduce noise."
    },
    {
      "module": "extension_risk",
      "provider_role": "signal_producer",
      "provider_method": "get_versions(extension_id)",
      "endpoint_or_artifact": "GET https://api.crxcavator.io/v1/report/{extension_id}",
      "classification": "enrichment_only",
      "entity_types": ["extension_id"],
      "gating_logic": "Use only if endpoint existence and schema are verified in staging. Treat non-2xx or non-JSON responses as no-data. Do not emit standalone signals from this endpoint.",
      "citation_refs": [
        "https://gist.github.com/ryanbreed/ae679035b3f1298e3bf4dbc596906a31",
        "https://www.powershellgallery.com/packages/BrowserExtensionRisk/0.0.1/Content/BrowserExtensionRisk.psm1",
        "https://gist.github.com/defensivedepth/4642b59c8bc94293139781b78a0e1d02"
      ],
      "notes": "Inferred from community script that requests https://api.crxcavator.io/v1/report/{extension_id} and iterates versions from the returned JSON list. Suitable for historical risk enrichment but not required for core signal production."
    }
  ],
  "signal_contracts": [
    {
      "module": "extension_risk",
      "source": "extension_risk",
      "provider": "crxcavator",
      "provider_method": "GET /v1/report/{extension_id}/{version}?platform={platform}",
      "signal_type": "browser_extension_risk",
      "category": "endpoint_security",
      "severity": "medium",
      "severity_is_conditional": "yes",
      "conditional_rule": "Map severity from numeric data.risk.total: low for lowest score band, medium for moderate scores, high for highest scores. Start from existing third-party bands (e.g., <=377 low, 378–478 medium, >478 high) and recalibrate on real fleet distributions. Do not assign critical based on CRXcavator alone.",
      "entity_type": "extension_id",
      "finding_kind": "true_finding",
      "trigger_condition": "Emit a signal whenever the CRXcavator report request returns 2xx, JSON parses successfully, and data.risk.total is present and numeric. Optionally suppress very low-risk results and store them as enrichment-only.",
      "evidence_fields": [
        "data.risk.total",
        "data.risk.csp.total",
        "data.risk.permissions.total",
        "data.risk.retire.total",
        "data.risk.webstore.total",
        "data.risk.metadata.total"
      ],
      "enrichment_fields": [
        "full_raw_response_json",
        "any documented extension metadata fields once schema is confirmed (e.g., name, publisher, webstore URL, description, rating)",
        "any documented CSP, permissions, RetireJS, and webstore sub-objects once official schema is available"
      ],
      "summary_template": "Browser extension {{extension_id}} (version {{version}} on {{platform}}) has CRXcavator total risk score {{data.risk.total}} (CSP={{data.risk.csp.total}}, permissions={{data.risk.permissions.total}}, RetireJS={{data.risk.retire.total}}, webstore={{data.risk.webstore.total}}).",
      "evidence_status": "derived",
      "citation_refs": [
        "https://www.powershellgallery.com/packages/BrowserExtensionRisk/0.0.1/Content/BrowserExtensionRisk.psm1",
        "https://www.kolide.com/features/device-inventory/properties/device-chrome-extensions",
        "https://github.com/mstanislav/mrxcavator",
        "https://www.helpnetsecurity.com/2019/02/22/should-you-trust-that-chrome-extension/",
        "https://ahmedmusaad.com/examining-google-chrome-extensions-using-crxcavator/"
      ],
      "notes": "data.risk.* totals are observed in multiple independent clients and appear stable; other JSON fields are currently treated as opaque enrichment until confirmed from official CRXcavator docs. Severity is posture-based (extension configuration risk), not evidence of active compromise, so critical should be reserved for corroborating signals from other modules."
    }
  ],
  "confidence_guidance": [
    {
      "module": "extension_risk",
      "signal_type_or_use_case": "browser_extension_risk (per-extension report)",
      "source_reliability": "CRXcavator is operated by Duo/Cisco and continuously assesses browser extensions using a documented scoring model, giving high confidence in data.risk.* numeric scores but only medium confidence in un-documented nested fields that are currently inferred from clients and UI integrations.",
      "freshness_considerations": "Reports are generated from periodic scans of browser extension stores; use any updated-at style field in the JSON (e.g., surfaced externally as crxcavator_updated_at) to measure staleness, and consider down-weighting or suppressing very old reports when extension code and permissions have likely changed.",
      "corroboration_rules": "Treat high CRXcavator scores as posture signals that should be correlated with endpoint/browser inventory (installed extensions per device/user), identity telemetry, and any extension-related alerts before escalating. Use CRXcavator as a risk oracle rather than a standalone incident detector.",
      "calibration_todo": "1) Pull distributions of data.risk.total across a representative fleet to tune severity thresholds and decide when to emit vs. suppress. 2) Confirm full JSON schema from official docs, especially for CSP and permissions breakdowns. 3) Validate score consistency across platforms (Chrome, Edge, Firefox). 4) Decide whether to always emit a signal for non-zero risk or only for medium/high bands."
    },
    {
      "module": "extension_risk",
      "signal_type_or_use_case": "Historical risk (GET /v1/report/{extension_id}, inferred)",
      "source_reliability": "Endpoint behavior is inferred from a single community script that treats the response as a list of version objects; until verified against the live API and official docs, treat this endpoint as lower reliability and non-critical to the integration.",
      "freshness_considerations": "Historical risk is useful for understanding when a given extension version became risky but is not inherently time-sensitive. Ensure version ordering and any timestamps are parsed correctly and avoid taking real-time decisions from historical-only data.",
      "corroboration_rules": "Use historical risk solely as enrichment for extensions that are known to be installed or already have a current browser_extension_risk signal. Do not generate standalone alerts from history such as old risky versions that were never deployed in the environment.",
      "calibration_todo": "1) Verify that /v1/report/{extension_id} exists and returns a stable JSON schema including version identifiers and possibly risk totals. 2) Decide how much history to retain (full series vs. min/avg/max summaries). 3) Integrate version history into prioritization logic only after schema and semantics are confirmed."
    }
  ]
}
```
