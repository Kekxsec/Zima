---
title: "output / tools / malicious_extension_sentry"
aliases: ["malicious_extension_sentry output", "malicious_extension_sentry signal registry"]
tags: [zima, research, outputs, signal-registry, tools, malicious_extension_sentry, graph_exclude]
type: provider_research_output
provider: malicious_extension_sentry
provider_category: tools
status: not_started
prompt_note: prompt.md
provider_folder: malicious_extension_sentry.md
obsidianUIMode: preview
---
# Malicious Extension Sentry (Browser Extension DB)

This provider is a **local matcher** using a maintained database of known-malicious Chrome/Edge extensions (IDs) to flag installed browser extensions. It does **not** perform any API calls; instead, the database (CSV/Markdown) is updated frequently (daily commits) from multiple sources and loaded locally. Extensions are identified by their 32-character Chrome Web Store ID. When an installed extension’s ID matches the list, it yields a direct signal.

According to the maintainer, the database aggregates **Chrome/Edge extensions removed** from the Web Store for malware or policy violations. Entries include **Extension ID, Name, and Date Added**. There is **no explicit severity or category field** in the DB – all listed extensions are simply “malicious/removed.” Metadata like the source of discovery (blog or monitoring service) is often captured as a reference link in the Markdown version.

**Database format & provenance:** The data is stored in both `.csv` and `.md` files. The plain list (`Malicious-Extensions.csv`) is a comma-separated list of extension IDs (~400+ IDs, e.g. “khoapclcikhbeaggmmfcnckcnhfniijj,” etc. shown in [14]). A detailed CSV/Markdown (952+ lines) lists each ID with its name, discovery source, and date. The project is maintained by an individual developer (user **@toborrm9**) on GitHub; it’s updated nearly daily by automated scraping of extension store takedowns, security blogs, and threat feeds.

**Matching:** Matching is an **exact ID lookup**. Extension IDs are unique 32-character alphanumeric (Chrome format). IDs are compared in a case-insensitive manner (they are all lowercase by convention). The database is focused on Chromium-based stores, so it covers Chrome and Chromium-based Edge extensions. It does **not** cover Firefox or Safari add-ons.

**Output:** On a match, the provider offers the extension ID, name, date added to the list, and often a reference/source URL. There are no built-in threat categories or severity scores in the data. The caller (Zima) must interpret severity. By default any _malicious extension found_ is serious: we treat confirmed malware as **critical**; data-harvesting/threat extension as **high**; minor adware as **medium** (per guidelines). The summary and tags can reflect “malware”, “proxy/vpn”, or “data_broker” depending on context.

**Coverage & Limits:** The list covers **known-bad** extensions caught by Google/Edge (store removals, research reports). It does _not_ detect unknown malware or side-loaded (non-store) extensions. The false-negative rate is high for new/unreported threats: absence from the list does **not** mean safe. It also does not track versions – any updated code under the same ID remains flagged unless manually removed from the DB. Some entries may be removed if later deemed false positives, but that’s managed by the maintainer.

**Key citations:** The repository README and Malicious-Extensions.md confirm the use-case (“Cross-platform scan of Chrome/Edge”) and content fields. It explicitly states the data is from “Chrome extension monitoring services, security research blogs, and threat intelligence feeds”. The example scan output shows the tool “loaded 437 known malicious extension IDs”. These sources underpin the database’s scope and freshness.

### Tool & Database Appendix

- **Name/Repo:** _Malicious Extension Sentry_ by toborrm9 (GitHub: `malicious_extension_sentry`).

- **Source Database:** Aggregated list of Chrome/Edge extensions removed for malicious behavior. No single official source; data pulled from store monitoring, security blogs, threat feeds.

- **Format:** Primary files are CSV/Markdown. `Malicious-Extensions.csv` is a comma-separated list of IDs (~400–500 entries). A detailed CSV/MD (`malicious_extensions_detailed.csv` / `Malicious-Extensions.md`) includes columns: Extension ID, Name, (often) Source URL, Date Added.

- **Size:** On the order of hundreds of extension IDs (the scanner output example shows “437 known malicious extension IDs”). The CSV is ~31 KB (single row) as of the latest commits.

- **Update Cadence:** Commit history shows daily updates (multiple commits per day). The maintainer automates scraping each day.

- **Maintainer:** Individual developer (GitHub user _toborrm9_). The project is MIT-licensed and community-contributed.

- **Provenance:** Extensions found via automated monitoring of Chrome Web Store removals and reported campaigns, plus security research blogs (e.g. security.com, Obsidian, etc.). Each entry’s source is often cited in the Markdown list (e.g.  or news site link next to the name).

- **Matching Mechanism:** Exact match on Chrome extension ID (32-char alphanumeric). IDs are matched case-insensitively (all stored IDs are lowercase). No regex or name matching is used. Only Chrome/Chromium extension IDs are supported. Firefox or non-Chromium extensions use different ID schemes and are _not_ in scope.

- **Identifiers:** Chrome Web Store ID (32-char string). Edge (Chromium) uses the same ID scheme for shared extensions, so Edge extensions are implicitly supported if same ID. No support for Firefox add-on IDs or manifest-based IDs.

- **Output Metadata:** When matched, the tool provides the extension’s ID, human-readable name, date added, and source reference (if available). The database does _not_ include an explicit category (malware/spyware/etc.) or severity. However, the entry’s name often hints at functionality (e.g. “VPN” or “Cursor”). Any severity labeling must be inferred by us.

- **Categories/Ratings:** There is no built-in threat category or severity score per entry. The list includes anything flagged malicious or policy-violating. We will map severity ourselves (e.g. treat clearly malicious spyware or credential stealers as critical; benign-appearing adware as lower).

- **Limitations:** Only detects **known** bad IDs. It does not analyze code or detect zero-day threats. Extensions not yet reported or not removed from the store will be missed (high false-negative rate). It covers **store-listed** extensions; unofficial or sideloaded extensions won’t be in the list. It is not version-aware – an extension ID remains flagged regardless of version changes. There is no logic for “was malicious but updated to benign” beyond manually removing IDs from the list.


**Citations:** The GitHub README and commit logs describe this database and its fields. We rely on the repository as the authoritative source for what data is included and how it’s updated.

---

## Module Mapping Table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|extension_risk|direct_signal_input|local database scan|`Malicious-Extensions.csv` (CSV/MD DB)|direct_signal_input|extension_id*|Use only if a list of installed extension IDs is available (from browser_extension_detector). For each installed extension ID, check if it exists in the malicious-extensions DB. Trigger only when a match is found.|[36†L412-L417][19†L347-L351]|Implements local lookup of extensions; no network calls. *Entity type: Chrome/Edge extension (ID).|

**Notes:** The extension_risk module uses the Malicious Extension Sentry list as a **local matcher**. It requires as input the set of installed extension IDs (obtained from a browser extension detector). The gating logic is “if any installed_extension_id ∈ malicious_extension_list”. The provider is effectively a static database (CSV or script). The source value in signals should be the extension_risk module name. We cite the structure of the database and contents.

_We denote the entity as the extension ID (there is no formal “extension” type, but we use the unique ID string as the key)._

---

## Signal Contract Table

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|extension_risk|extension_risk|malicious_extension_sentry|local_scan (CSV match)|`malicious_extension_found`|account_security|critical|no|N/A|extension_id*|true_finding|`extension_id in malicious_extensions_db`|`extension_id`, `extension_name`, `date_added`, `source_url`||"Malicious Chrome extension "{extension_name}" (ID: {extension_id}) is installed."|documented|[36†L412-L417][25†L1410-L1418]||

- **signal_type:** We define `malicious_extension_found` for any matched malicious extension (renaming as needed).
- **category:** We suggest `account_security` (extension can compromise account/session). Other plausible categories include `privacy` or `application_security`, but none are in the given list.
- **severity:** Default **Critical** for all matches, per guidelines (known-malware extension is direct credential/exposure risk). We mark no conditional logic here because the database doesn’t label types. If desired, one could lower severity (to High/Medium) based on inferred extension behavior (e.g. “Cursor” extensions could be medium if only considered adware).
- **trigger_condition:** Expressed as a simple field check. In practice: if any installed extension’s ID appears in the malicious list. E.g.:

    swift

    Copy

    ```
    for each extension in installed_extensions:
        if extension.id in malicious_extensions_db: trigger signal
    ```

- **evidence_fields:** We record the raw extension ID, extension name, and when added (from DB), plus the source reference (URL of report). These come from the provider’s DB.
- **summary_template:** An example human-readable summary combining name and ID.
- **finding_kind:** `true_finding` (this is a direct detection of malicious content, not just enrichment).
- **evidence_status:** All listed fields are documented by the provider’s files (ID, name, date, source all appear in the detailed CSV/Markdown).
- **citation_refs:** We cite the DB’s documentation of its fields and an example entry.

_Note:_ No separate enrichment signals are generated by this provider. It purely flags the presence of a known-malicious extension.

---

## Severity Rules

- **malicious_extension_found:** **Default Critical.** A known-malicious extension is a direct compromise: e.g. stealer, spyware, crypto hijacker ⇒ **Critical** (matches “direct credential exposure or active malware”). If certain entries are clearly only privacy-invasive/adware (e.g. a “Cursor” theme), one could consider **High** or **Medium**; but absent explicit type data, we err on the side of caution.
- _Conditional logic (optional):_ If the extension name or known behavior suggests only adware/PII collection, severity could be lowered (e.g. High for data harvesting, Medium for benign-but-privacy-invasive extensions). We recommend tuning after seeing actual matches in data.
- We reference the calibration guide: known malware extension = critical, data-harvester = high, adware = medium.

---

## Confidence Guidance

|module|signal_type_or_use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|extension_risk|`malicious_extension_found`|Medium: Data comes from a community-maintained list (1 author) aggregated from public sources. No formal QA or official vetting.|High: DB is updated daily with new reports. However, individual entries may lag behind the latest threats, and removals are retrospective.|Corroborate with independent threat intel (e.g. security blog reports, antivirus detections) where possible. Investigate extension code if flagged.|Track false positives/negatives: some flagged extensions may be borderline. Possibly cross-check with other blocklists. Adjust severity rules if certain classes (e.g. “cursor” themes) prove less risky.|

- **Source reliability:** This is an open-source aggregator, not an official vendor feed. It collects from research blogs and scans. The author claims accuracy but this is community data. Marked **medium** reliability due to single-maintainer nature.
- **Freshness:** Very fresh – updated daily (commits on March 2026 almost every day). However, extension threats evolve quickly; the list only reflects what has already been reported/removed.
- **Corroboration:** We should verify detections against other data (e.g. check if AV or Chrome policy lists the extension as malicious, or if it appears in other threat databases). Use the extension’s behavior or code analysis to confirm. A matching ID from this list should trigger urgent review but can be cross-checked with another source if available.
- **Calibration TODO:** Monitor real-world hits vs false alarms. For example, if an extension from this list turns out benign, we need to adjust (perhaps mark severity lower or remove it). Similarly, new malicious extensions missed by the list should be identified and possibly fed back to update the list. Document any patterns (e.g. if “Cursor” extensions are frequently false positives, lower default severity or treat as enrichment).

---

## Provider Summary

1. **Strongest signal:** Flags when _known-malicious Chrome/Edge extensions_ are installed. The core signal is simply “malicious extension found”. This is a direct high-priority alert if triggered.
2. **Not for:** It should **not** be used for detecting unknown threats or evaluating extension safety beyond known-bad IDs. Clean results are merely _absence of evidence_ – extensions not in the list could still be malicious. Thus this provider should not be treated as a full security analysis, only as a list-based check.
3. **Cautions:** No special installation or privileges needed, but it depends on having a list of installed extension IDs (likely from a browser agent with sufficient privileges). As a local scanner, it does not send data outbound. Watch out that matching relies on the exact extension ID; some security tools report extensions by name or manifest, so ensure ID is extracted correctly.
4. **Role:** This is strictly **signal-producing** for the `extension_risk` module. It is not an enrichment (it doesn’t add context to other signals) nor merely a utility. Its output is the presence/absence of malicious IDs.
{
  "provider": "malicious_extension_sentry",
  "provider_category": "tools",
  "provider_role": "direct_signal_input",
  "module_mappings": [
    {
      "module": "extension_risk",
      "provider_role": "direct_signal_input",
      "provider_method": "local_scan",
      "endpoint_or_artifact": "Malicious-Extensions.csv (static DB)",
      "classification": "direct_signal_input",
      "entity_types": ["extension_id"],
      "gating_logic": "Requires list of installed extension IDs; trigger only if ID is in malicious list.",
      "citation_refs": ["36","19"],
      "notes": "Local matcher of known bad Chrome/Edge extension IDs; no API."
    }
  ],
  "signal_contracts": [
    {
      "module": "extension_risk",
      "source": "extension_risk",
      "provider": "malicious_extension_sentry",
      "provider_method": "local_scan",
      "signal_type": "malicious_extension_found",
      "category": "account_security",
      "severity": "critical",
      "severity_is_conditional": "no",
      "conditional_rule": "",
      "entity_type": "extension_id",
      "finding_kind": "true_finding",
      "trigger_condition": "extension_id in malicious_extensions_db",
      "evidence_fields": ["extension_id","extension_name","date_added","source_url"],
      "enrichment_fields": [],
      "summary_template": "Malicious Chrome extension \"{extension_name}\" (ID: {extension_id}) is installed.",
      "evidence_status": "documented",
      "citation_refs": ["36","25"],
      "notes": ""
    }
  ],
  "confidence_guidance": [
    {
      "module": "extension_risk",
      "signal_type_or_use_case": "malicious_extension_found",
      "source_reliability": "Medium (community-curated list)【36†L404-L413】",
      "freshness_considerations": "High (daily updates【46†L210-L218】, but may lag new threats)",
      "corroboration_rules": "Cross-check with independent threat intel or AV detection; validate extension behavior/code.",
      "calibration_todo": "Monitor false positives (e.g. benign themes); adjust severity or filter entries accordingly."
    }
  ]
}
