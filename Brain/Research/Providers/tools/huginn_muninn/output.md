---
title: "output / tools / huginn_muninn"
aliases: ["huginn_muninn output", "huginn_muninn signal registry"]
tags: [zima, research, outputs, signal-registry, tools, huginn_muninn]
type: provider_research_output
provider: huginn_muninn
provider_category: tools
status: complete
prompt_note: prompt.md
provider_folder: huginn_muninn.md
obsidianUIMode: preview
kind: reference
llm_include: true
code_scope: backend
---

# Huginn-Muninn (Internet Crowdsourced Device Fingerprint Database)

**Source:** https://github.com/Ringmast4r/Huginn-Muninn
**Author:** Ringmast4r
**Type:** Static reference dataset (no API — local lookup only)
**License:** ODbL (OpenStreetMap data), GPL (Satori project data), mixed for community contributions
**Size:** ~11 million records across 8 datasets

Named after Odin's knowledge-gathering ravens from Norse mythology, Huginn-Muninn is a **crowdsourced device fingerprint reference database** combining MAC vendor data, DHCP fingerprints, device profiles, and protocol signatures. It's a **superset** of OUI-Master-Database — it includes MAC vendor data (10.1M records) PLUS device-level fingerprinting that OUI alone can't provide.

**Strategic value for Zima:** Extends OUI-Master-Database from "what vendor made this device" to "what specific device model is this" using DHCP and protocol fingerprinting. Relevant for network exposure analysis — identifying device types on the local network at a more granular level than MAC vendor alone.

---

## A. Tool/API Surface Appendix

### No API — Static Dataset

This is a **downloadable reference dataset**, not a running service. All data is stored locally in multiple formats. Zima would embed or reference the SQLite version.

### Datasets (8 folders)

| Dataset | Records | Description | Format |
|---|---|---|---|
| MAC Vendor Identifiers | 10,100,000+ | OUI → manufacturer mapping (superset of IEEE) | CSV, JSON, Parquet, SQLite |
| DHCP Fingerprints | 368,000+ | DHCP option patterns → device OS/type | CSV, JSON, Parquet, SQLite |
| Device Profiles | 116,000+ | Detailed device model/OS identification | CSV, JSON, Parquet, SQLite |
| Protocol Fingerprints (Satori) | 1,980 | Network protocol behavior signatures | CSV, JSON, Parquet, SQLite |
| Fingerprint → Device Mappings | 813 | Cross-reference: fingerprint hash → specific device model | CSV, JSON, Parquet, SQLite |
| (3 additional datasets) | Varies | Supporting lookup tables | CSV, JSON, Parquet, SQLite |

### Data Sources

| Source | Type | License |
|---|---|---|
| IEEE OUI Registry | Official MAC vendor assignments | Public domain |
| Satori Project | Protocol fingerprints | GPL |
| Community OSINT contributions | Device profiles, DHCP signatures | ODbL |
| Nmap/Wireshark supplementary data | MAC + protocol data | GPL |

### Query Model

```python
import sqlite3
db = sqlite3.connect('huginn_muninn.db')

# MAC vendor lookup (same as OUI-Master-Database but larger dataset)
vendor = db.execute("SELECT * FROM mac_vendors WHERE oui = ?", (mac_prefix,)).fetchone()

# DHCP fingerprint lookup
device = db.execute("SELECT * FROM dhcp_fingerprints WHERE fingerprint = ?", (dhcp_fp,)).fetchone()

# Device profile lookup
profile = db.execute("SELECT * FROM device_profiles WHERE model LIKE ?", (f"%{query}%",)).fetchone()
```

---

## Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|
| device_inventory | enrichment_only | mac_vendor_lookup | SQLite query on mac_vendors table | enrichment_only | mac_address | Same as OUI-Master-Database — requires MAC address from osquery/network scan. | github.com/Ringmast4r/Huginn-Muninn README | Overlaps with OUI-Master-Database; use one or the other, not both. |
| device_inventory | enrichment_only | dhcp_fingerprint_lookup | SQLite query on dhcp_fingerprints table | enrichment_only | dhcp_fingerprint | Requires DHCP fingerprint from network capture (osquery or passive monitoring). | github.com/Ringmast4r/Huginn-Muninn README | Adds device model/OS identification beyond MAC vendor. |
| network_exposure | enrichment_only | device_profile_enrichment | SQLite query on device_profiles table | enrichment_only | device_model | Requires device model string from DHCP or user-agent. | github.com/Ringmast4r/Huginn-Muninn README | Deep device identification for network context. |

---

## Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| — | — | huginn_muninn | — | — | — | — | — | — | — | — | — | — | — | — | — | — | No standalone signals. Enrichment only — adds device model/OS context to network inventory. |

---

## Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|
| device_inventory | mac_vendor_enrichment | High: Same IEEE + community data as OUI-Master-Database. | Medium: Static dataset, unknown update cadence (commit history sparse). | Cross-reference with OUI-Master-Database results — should match on MAC vendor. | Compare freshness/coverage with OUI-Master-Database. If OUI-Master-Database is equally comprehensive for MAC vendors, use that instead and only add Huginn-Muninn for DHCP fingerprinting. |
| device_inventory | dhcp_fingerprint_enrichment | Medium: Community-sourced fingerprints. Coverage varies by device type — well-covered for common devices, gaps for niche/enterprise hardware. | Medium-Low: Static dataset. DHCP fingerprint patterns can change with OS updates. | Corroborate DHCP-identified device type with MAC vendor. If DHCP says "iPhone" and MAC says "Apple", high confidence. | Measure hit rate against real-world network scans. |

---

## Provider Summary

### Strongest Use Cases

- **DHCP fingerprinting** — Unique value beyond OUI-Master-Database. Can identify specific device models (iPhone 14, Samsung Galaxy S23, HP LaserJet, etc.) not just vendors.
- **Protocol fingerprint reference** — 1,980 signatures from the Satori project for deep protocol identification.
- **All-in-one device reference** — If you want a single database for MAC + DHCP + device profiles, this is it.

### What Not To Use It For

- Do not use as the primary MAC vendor database if OUI-Master-Database is already integrated — too much overlap.
- Do not treat DHCP fingerprints as definitive device identification — they can be spoofed and change with OS updates.

### Implementation Cautions

- **Dataset size:** ~11M records. SQLite file is larger than OUI-Master-Database (~50MB+ estimated). May not be suitable for lightweight agent deployments.
- **Overlap with OUI-Master-Database:** MAC vendor data is redundant. Consider using OUI-Master-Database for MAC lookups and Huginn-Muninn only for DHCP fingerprinting.
- **Update cadence:** Unknown/sparse. OUI-Master-Database has documented monthly updates; Huginn-Muninn may be less actively maintained.
- **DHCP fingerprint collection:** Requires passive network monitoring or osquery DHCP data. Not all Zima deployment environments will have this data available.
- **License:** Mixed (ODbL + GPL). Review implications for commercial bundling.

### Current Zima Stage Fit

- **Phase:** Post-launch enrichment — adds device model identification to network inventory
- **Module:** `device_inventory` (DHCP fingerprint enrichment)
- **Classification:** `enrichment_only`
- **Recommendation:** Use OUI-Master-Database for MAC vendor lookups (better maintained, smaller footprint). Only add Huginn-Muninn if Zima collects DHCP fingerprint data and needs model-level identification. This is a **P3 / post-launch** enhancement.

---

# Structured JSON

```json
{
  "provider": "huginn_muninn",
  "provider_category": "tools",
  "provider_role": "enrichment_only",
  "source": "https://github.com/Ringmast4r/Huginn-Muninn",
  "requires_api_key": false,
  "requires_network": false,
  "local_artifact": "SQLite database (~50MB+ estimated)",
  "coverage": "11M+ records: MAC vendors, DHCP fingerprints, device profiles, protocol signatures",
  "launch_fit": "post_launch_p3",
  "module_mappings": [
    {
      "module": "device_inventory",
      "provider_role": "enrichment_only",
      "provider_method": "dhcp_fingerprint_lookup",
      "classification": "enrichment_only",
      "entity_types": ["dhcp_fingerprint", "mac_address"],
      "gating_logic": "Requires DHCP fingerprint or MAC address from network scan",
      "notes": "Unique value: DHCP fingerprints for device model identification beyond MAC vendor."
    }
  ],
  "signal_contracts": [],
  "confidence_guidance": [
    {
      "module": "device_inventory",
      "signal_type_or_use_case": "dhcp_fingerprint_enrichment",
      "source_reliability": "Medium (community-sourced fingerprints)",
      "freshness_considerations": "Medium-Low (static dataset, unknown update cadence)",
      "corroboration_rules": "Cross-reference DHCP device type with MAC vendor",
      "calibration_todo": "Measure hit rate; compare update freshness with OUI-Master-Database"
    }
  ]
}
```
