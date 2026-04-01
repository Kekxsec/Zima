---
title: "output / tools / socid_extractor"
aliases: ["socid_extractor output", "socid_extractor signal registry"]
tags: [zima, research, outputs, signal-registry, tools, socid_extractor, graph_exclude]
type: provider_research_output
provider: socid_extractor
provider_category: tools
status: complete
prompt_note: prompt.md
provider_folder: socid_extractor.md
obsidianUIMode: preview
---

# socid-extractor (Social Media Profile Data Extractor)

**Source:** https://github.com/soxoj/socid-extractor
**Author:** soxoj (same author as maigret — these tools are designed as a pipeline)
**License:** GPL-3.0
**Language:** Python (99.9%)
**PyPI:** `pip3 install socid-extractor`

This tool extracts structured identity data from social media profile URLs. It is a **downstream enrichment companion** to maigret and whatsmyname: those tools find which sites a username exists on, socid-extractor then fetches each found profile URL and parses machine-readable identity fields from it (unique platform IDs, creation dates, linked accounts, location, etc.).

The key unique value is **cross-platform ID extraction** — platforms like Google, Yandex, and Facebook embed internal user IDs (GAIA IDs, UIDs) in public profile pages. These IDs persist even if a user changes their username or display name, enabling identity correlation across services.

**Coverage:** 100+ extraction methods across major platforms including Google, Yandex, Facebook, Instagram, TikTok, GitHub, Twitter/X, and many others.

---

## A. Tool/API Surface Appendix

### CLI Interface

```bash
socid_extractor --url <profile_url>
# Examples:
socid_extractor --url https://github.com/soxoj
socid_extractor --url https://www.instagram.com/username/
```

**Without installation:**
```bash
./run.py --url <profile_url>
```

**Input:** A single profile URL per invocation.
**Output:** Structured data printed to stdout.

### Python Library Interface

```python
import socid_extractor

# Pass raw HTML content of a profile page
result = socid_extractor.extract(html_content)
# Returns: dict of extracted fields
```

The library interface allows integration without shelling out — useful for Zima's backend where the HTTP fetch and parsing can be decoupled (e.g. fetch via a privacy-respecting proxy, then extract locally).

### Output Schema

The tool returns a flat dictionary of extracted fields. Fields present depend on the platform; not all are present for every site.

| Field | Type | Notes |
|---|---|---|
| `username` | string | Platform username |
| `name` / `fullname` | string | Display name |
| `created_at` | string (ISO-ish) | Account creation timestamp |
| `country` | string | Country if stated on profile |
| `location` | string | City/region if stated |
| `gender` | string | Gender if stated |
| `website` | string | Linked website |
| `links` | list[string] | Other linked profiles/URLs |
| `id` / `uid` / `gaia_id` | string | Platform-internal user ID |
| `biography` | string | Bio text |

**Field presence:** Highly platform-dependent. The platform ID fields (uid, gaia_id) are the most strategically valuable — they are stable identifiers even when usernames change.

### Supported Platforms (sample)

Google, Yandex, Facebook, Instagram, TikTok, GitHub, Twitter/X, VK, OK.ru, Flickr, Pinterest, Steam, Reddit, and 100+ others. Full list in the repository's `socid_extractor/` module files.

### Privilege Requirements

None beyond network access. The tool makes standard HTTP GET requests to public profile pages. No authentication required.

### Rate Limits / Throttling

No built-in rate limit controls. Zima should implement polite delays between requests, especially when enriching many profiles from a maigret run. Aggressive fetching will trigger bot protection on most platforms.

### Installation

```bash
pip3 install socid-extractor
# or from source:
pip3 install -U git+https://github.com/soxoj/socid_extractor.git
```

---

## Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|
| username_exposure | enrichment_only | profile_url_extraction | HTTP GET to platform profile URL | enrichment_only | username, account_url | Requires a confirmed profile URL (from maigret CLAIMED result or similar). Only invoke for sites where socid-extractor has a registered extractor method. | github.com/soxoj/socid-extractor README | Do not emit standalone signals; enrich existing account inventory entries. |
| account_inventory | enrichment_only | profile_url_extraction | HTTP GET to platform profile URL | enrichment_only | username | Same gating as above. Useful for adding platform UIDs, creation dates, linked accounts to inventory records. | github.com/soxoj/socid-extractor README | Platform UID is the most stable identifier — persist alongside the profile URL. |

---

## Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| username_exposure | username_exposure | socid_extractor | profile_url_extraction | — | — | — | — | — | — | — | — | — | — | — | — | — | No direct signals. Enrichment only. |

**No standalone signals.** socid-extractor does not generate findings on its own. Its output enriches account inventory entries created by maigret, whatsmyname, or holehe. The most actionable enrichment data is:
- **Platform UID** — for cross-service identity correlation
- **created_at** — account age (old accounts = lower risk of throwaway; very old = long-standing footprint)
- **links** — other profiles to feed back into maigret/whatsmyname for recursive discovery

---

## Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|
| account_inventory | profile_enrichment | Medium-High: Data parsed from live public profile pages. Platform-native fields are factual where present. | High: Data is fetched live at scan time. Account data may not reflect recent changes if cached. | Cross-reference extracted uid/gaia_id with maigret's claimed username to confirm identity continuity. | Track sites where extraction fails (bot protection, layout changes). Gracefully degrade to partial enrichment. |
| username_exposure | cross-platform_uid_correlation | High for uid/gaia_id fields: these are embedded in page source and stable. Lower for display fields (name, location). | High (live fetch). | Treat uid extraction as corroborating evidence when correlating identities across platforms. | Monitor for DOM/API changes that break extractors; expect maintenance overhead. |

---

## Provider Summary

### Strongest Use Cases

- **Platform UID extraction** — Persistent internal IDs (Google GAIA ID, Facebook UID, etc.) that survive username changes. Enables reliable cross-service identity graph building.
- **Account creation date** — Adds temporal context to account inventory (old established account vs. recently created throwaway).
- **Linked account discovery** — Profiles often link to other services; these can be fed back into discovery tools.

### What Not To Use It For

- Do not treat socid-extractor output as a breach or exposure signal — it extracts public profile data only.
- Do not run it unsupervised at high concurrency — platforms will block the IP.
- Do not use it as the primary discovery mechanism — it only works when you already have a confirmed profile URL.

### Implementation Cautions

- **Dependency:** Requires a confirmed profile URL as input. Must be used after maigret/whatsmyname, not before.
- **Extractor staleness:** Social platforms change their page structure; extractors break silently. Monitor for empty/incomplete output.
- **GPL-3.0 license:** Copyleft; review implications for Zima's distribution model. Library usage in a SaaS backend may be acceptable but requires legal review.
- **Bot detection:** Major platforms (Instagram, Facebook, TikTok) aggressively block scraping. Success rate will vary; treat missing output as graceful degradation, not an error.
- **Privacy:** Fetching public profiles does not require the user's consent, but Zima should document this in its data processing agreement.

### Current Zima Stage Fit

- **Phase:** Enrichment layer, runs after maigret/whatsmyname discovery
- **Module:** `account_inventory` enrichment, `username_exposure` enrichment
- **Classification:** `enrichment_only`
- **Pipeline position:** maigret → [claimed profile URLs] → socid_extractor → [enriched account records]

---

# Structured JSON

```json
{
  "provider": "socid_extractor",
  "provider_category": "tools",
  "provider_role": "enrichment_only",
  "source": "https://github.com/soxoj/socid-extractor",
  "license": "GPL-3.0",
  "requires_api_key": false,
  "requires_network": true,
  "install": "pip3 install socid-extractor",
  "module_mappings": [
    {
      "module": "username_exposure",
      "provider_role": "enrichment_only",
      "provider_method": "profile_url_extraction",
      "endpoint_or_artifact": "HTTP GET to platform profile URL",
      "classification": "enrichment_only",
      "entity_types": ["username", "account_url"],
      "gating_logic": "Requires confirmed profile URL from upstream discovery (maigret/whatsmyname CLAIMED result)",
      "notes": "Enrich with uid, created_at, links. No standalone signals."
    },
    {
      "module": "account_inventory",
      "provider_role": "enrichment_only",
      "provider_method": "profile_url_extraction",
      "endpoint_or_artifact": "HTTP GET to platform profile URL",
      "classification": "enrichment_only",
      "entity_types": ["username"],
      "gating_logic": "Same as above",
      "notes": "Platform UID is the most stable enrichment field."
    }
  ],
  "signal_contracts": [],
  "confidence_guidance": [
    {
      "module": "account_inventory",
      "signal_type_or_use_case": "profile_enrichment",
      "source_reliability": "Medium-High (live public profile parse)",
      "freshness_considerations": "High (live fetch at scan time)",
      "corroboration_rules": "Cross-reference uid with maigret claimed username",
      "calibration_todo": "Track extraction failures per site; graceful degradation required"
    }
  ]
}
```
