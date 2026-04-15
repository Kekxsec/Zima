---
title: "output / tools / oui_master_database"
aliases: ["oui_master_database output", "oui_master_database signal registry"]
tags: [zima, research, outputs, signal-registry, tools, oui_master_database]
type: provider_research_output
provider: oui_master_database
provider_category: tools
status: complete
prompt_note: prompt.md
provider_folder: oui_master_database.md
obsidianUIMode: preview
kind: reference
llm_include: true
code_scope: backend
---

# OUI-Master-Database (MAC Address Vendor Lookup)

**Source:** https://github.com/Ringmast4r/OUI-Master-Database
**Author:** Ringmast4r (OSINT researcher / licensed PI)
**License:** Not explicitly stated; data aggregated from IEEE (public), Nmap, Wireshark, HDM Mac-Tracker
**Language:** JavaScript (build tooling); data outputs are format-agnostic
**Coverage:** 87,970+ MAC address vendor entries
**Update cadence:** Monthly automated pulls from all IEEE registries + community sources

This is the **most comprehensive publicly available MAC OUI database**, consolidating four authoritative sources into a single unified dataset. For Zima, it serves as an **embedded local lookup** — zero network calls, zero API keys, works offline. When osquery or the device baseline collects MAC addresses (network interfaces, ARP table, connected devices), this resolves each to a hardware vendor instantly.

---

## A. Tool/API Surface Appendix

### Data Sources (merged)

| Source | Coverage | Notes |
|---|---|---|
| IEEE OUI Registry | MA-L, MA-M, MA-S, IAB, CID registries | Official, authoritative |
| Nmap MAC Prefixes | nmap-mac-prefixes | Community-maintained, covers edge cases IEEE misses |
| Wireshark Manuf | wireshark/manuf | Extensive, includes OUI28 and OUI36 entries |
| HDM Mac-Tracker | hdm/mac-ages | Includes registration date data |

### Available Formats (10 total)

| Format | File | Use case |
|---|---|---|
| **SQLite** | `oui_master.db` | Best for Zima — pre-indexed, query-ready, ~5MB |
| **JSON** (pretty) | `oui_master.json` | API/web integration |
| **JSON** (minified) | `oui_master.min.json` | Bandwidth-optimized |
| **CSV** | `oui_master.csv` | Spreadsheet/analysis |
| **TSV** | `oui_master.tsv` | Tab-separated import |
| **TXT** | `oui_master.txt` | Legacy grep-friendly |
| **XML** | `oui_master.xml` | Enterprise system import |
| **SQL** | `oui_master.sql` | Direct DB import |
| **Kismet** | `oui_master.kismet` | Wireless IDS integration |
| **Kismet (gz)** | `oui_master.kismet.gz` | Compressed Kismet |

### Data Schema (per entry)

| Field | Type | Description |
|---|---|---|
| `oui` | string | OUI prefix (first 3 bytes of MAC, e.g. `AA:BB:CC`) |
| `manufacturer` | string | Full company name |
| `short_name` | string | Abbreviated name |
| `device_type` | string | Classification: Router, Phone, Camera, IoT, Server, etc. |
| `country_code` | string | Country of manufacturer registration |
| `registration_date` | string | When registered with IEEE |
| `address` | string | Company address |
| `source` | string | Which database(s) confirmed this entry |

### Query Examples

**SQLite (recommended for Zima):**
```sql
SELECT manufacturer, device_type, country_code
FROM oui_master
WHERE oui = 'AA:BB:CC';
```

**Python:**
```python
import sqlite3
db = sqlite3.connect('oui_master.db')
result = db.execute("SELECT * FROM oui_master WHERE oui = ?", (mac_prefix,)).fetchone()
```

**CLI (grep):**
```bash
grep "AA:BB:CC" oui_master.txt
```

### No Network Required

This is a **fully offline, local lookup**. The SQLite file is bundled with Zima's agent. Monthly update via Git pull or file download. No API key, no rate limits, no authentication.

---

## Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|
| device_inventory | enrichment_only | local_sqlite_lookup | `oui_master.db` SQLite query on MAC prefix | enrichment_only | mac_address | Requires MAC address from osquery or network scan. Extract first 3 bytes (OUI prefix) and query. | github.com/Ringmast4r/OUI-Master-Database README | Zero-cost enrichment. Adds vendor, device type, country to any MAC address in the scan. |
| network_exposure | enrichment_only | local_sqlite_lookup | `oui_master.db` SQLite query | enrichment_only | mac_address | Same as above. Used when scanning local ARP table to identify device types on the network. | github.com/Ringmast4r/OUI-Master-Database README | Can flag unknown/suspicious vendors as a soft signal. |

---

## Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| network_exposure | network_exposure | oui_master_database | local_sqlite_lookup | `unknown_device_vendor` | network_security | low | yes | Escalate to medium if device is on sensitive network segment or if MAC vendor is known IoT/surveillance manufacturer | mac_address | enrichment_finding | `oui_lookup_result.manufacturer == NULL OR oui_lookup_result.manufacturer IN suspicious_vendor_list` | `mac_address`, `oui_prefix` | `manufacturer`, `device_type`, `country_code` | "Unknown or suspicious device vendor ({manufacturer}) detected on local network (MAC: {mac_address})." | documented | github.com/Ringmast4r/OUI-Master-Database | Soft signal only — unknown vendor ≠ malicious. Context-dependent. |

### Signal Design Notes

- **Primary role is enrichment**, not signal generation. The main value is adding `manufacturer`, `device_type`, and `country_code` to every MAC address in the device/network inventory.
- The `unknown_device_vendor` signal is a **soft alert** — flagging devices with unresolvable OUIs or OUIs from known surveillance/IoT manufacturers could indicate rogue devices, but the false positive rate is high.
- Most value comes from the **enrichment fields** being visible alongside other signals (e.g., "this breached credential was used from a device manufactured by [Hikvision / TP-Link / Unknown]").

---

## Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|
| device_inventory | mac_vendor_enrichment | High: Aggregated from 4 authoritative sources (IEEE official + 3 community databases). Cross-referenced entries have highest reliability. | Medium: Monthly updates. New manufacturers registered with IEEE between updates will return NULL. | No corroboration needed — OUI assignment is deterministic (IEEE-assigned). | Track NULL lookup rate. If >5% of MACs resolve to NULL, check if database is stale. |
| network_exposure | unknown_device_vendor | Medium: Absence of evidence (unknown OUI) is not evidence of malice. Random MAC addresses (iOS/Android privacy feature) will always return NULL. | Same as above. | Corroborate unknown devices with ARP timing, traffic volume, or OS fingerprint. Do not alert solely on unknown OUI. | Measure false positive rate from randomized MACs. Consider filtering known randomized OUI prefixes (Apple, Google, Samsung privacy ranges). |

---

## Provider Summary

### Strongest Use Cases

- **MAC → Vendor resolution** for every device in the network scan. Instant, offline, deterministic for known OUIs.
- **Device type classification** — the `device_type` field distinguishes routers, phones, cameras, IoT, servers. Adds context to network inventory without active fingerprinting.
- **Country of origin** — flag devices from unexpected countries on the local network.

### What Not To Use It For

- Do not use OUI lookup alone to classify devices as safe/unsafe. OUI tells you manufacturer, not behavior.
- Do not rely on it for randomized MAC addresses (iOS 14+, Android 10+). These use locally-administered MACs that won't resolve.
- Do not treat it as a substitute for active device fingerprinting (DHCP fingerprint, OS detection, etc.).

### Implementation Cautions

- **Randomized MACs:** Modern mobile OSes randomize MAC addresses per-network. The OUI prefix of randomized MACs uses the locally-administered bit (second-least-significant bit of first byte is 1). Filter these before lookup to avoid pointless NULL results.
- **Database size:** ~5MB SQLite. Trivial to bundle with Zima's agent.
- **Update mechanism:** Git pull or download monthly. Automate in CI/CD.
- **License:** Data is from IEEE (public domain), Nmap (GPLv2), Wireshark (GPLv2), HDM (MIT-ish). The aggregated database inherits the most restrictive license — review GPL implications for Zima's distribution.

### Current Zima Stage Fit

- **Phase:** Device/network enrichment — runs alongside osquery and native posture checks
- **Module:** `device_inventory` enrichment, `network_exposure` soft signals
- **Classification:** `enrichment_only` (primary), `direct_signal_input` (weak, for unknown vendor alerts)
- **Pipeline position:** osquery/arp_scan → [MAC addresses] → OUI-Master-Database → [enriched device inventory]

---

# Structured JSON

```json
{
  "provider": "oui_master_database",
  "provider_category": "tools",
  "provider_role": "enrichment_only",
  "source": "https://github.com/Ringmast4r/OUI-Master-Database",
  "requires_api_key": false,
  "requires_network": false,
  "local_artifact": "oui_master.db (SQLite, ~5MB)",
  "update_cadence": "monthly",
  "coverage": "87970+ MAC vendor entries from IEEE + Nmap + Wireshark + HDM",
  "module_mappings": [
    {
      "module": "device_inventory",
      "provider_role": "enrichment_only",
      "provider_method": "local_sqlite_lookup",
      "endpoint_or_artifact": "oui_master.db",
      "classification": "enrichment_only",
      "entity_types": ["mac_address"],
      "gating_logic": "Requires MAC address; extract OUI prefix (first 3 bytes); filter randomized MACs",
      "notes": "Zero-cost offline enrichment. Adds vendor, device_type, country_code."
    },
    {
      "module": "network_exposure",
      "provider_role": "enrichment_only",
      "provider_method": "local_sqlite_lookup",
      "endpoint_or_artifact": "oui_master.db",
      "classification": "enrichment_only",
      "entity_types": ["mac_address"],
      "gating_logic": "Same as above",
      "notes": "Soft signal for unknown/suspicious vendors on local network."
    }
  ],
  "signal_contracts": [
    {
      "module": "network_exposure",
      "provider": "oui_master_database",
      "provider_method": "local_sqlite_lookup",
      "signal_type": "unknown_device_vendor",
      "category": "network_security",
      "severity": "low",
      "severity_is_conditional": true,
      "conditional_rule": "Escalate if device on sensitive segment or vendor is known surveillance/IoT manufacturer",
      "entity_type": "mac_address",
      "finding_kind": "enrichment_finding",
      "trigger_condition": "oui_lookup returns NULL or manufacturer in suspicious_vendor_list",
      "evidence_fields": ["mac_address", "oui_prefix"],
      "enrichment_fields": ["manufacturer", "device_type", "country_code"],
      "summary_template": "Unknown or suspicious device vendor ({manufacturer}) detected on local network (MAC: {mac_address}).",
      "evidence_status": "documented"
    }
  ],
  "confidence_guidance": [
    {
      "module": "device_inventory",
      "signal_type_or_use_case": "mac_vendor_enrichment",
      "source_reliability": "High (4 authoritative sources cross-referenced)",
      "freshness_considerations": "Medium (monthly updates)",
      "corroboration_rules": "None needed — OUI is deterministic",
      "calibration_todo": "Track NULL lookup rate; filter randomized MAC prefixes"
    }
  ]
}
```
