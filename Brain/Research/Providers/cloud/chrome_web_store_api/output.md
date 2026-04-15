---
title: "output / cloud / chrome_web_store_api"
aliases: ["chrome_web_store_api output", "chrome_web_store_api signal registry"]
tags: [zima, research, outputs, signal-registry, cloud, chrome_web_store_api]
type: provider_research_output
provider: chrome_web_store_api
provider_category: cloud
status: complete
prompt_note: prompt.md
provider_folder: chrome_web_store_api.md
obsidianUIMode: preview
kind: reference
llm_include: true
code_scope: backend
---

## API Surface Appendix

### 1) Official Chrome Web Store Publish API (V1)

This is the documented Chrome Web Store API; it is a publish/manage API, not a public metadata API.

#### 1.1 GET https://www.googleapis.com/chromewebstore/v1.1/items/{itemId}?projection=DRAFT

Purpose: Get an item's publish/upload status and basic identity (Item Resource).

Entity type: browser_extension (Chrome extension/app/theme identified by itemId).

Auth: OAuth 2.0, scope https://www.googleapis.com/auth/chromewebstore.readonly.

Top-level response (Item Resource):

- kind (string, always "chromewebstore#item") – static type indicator.
- id (string) – unique ID of the item.
- publicKey (string) – public key of the item.
- uploadState (string enum: FAILURE, IN_PROGRESS, NOT_FOUND, SUCCESS) – status of most recent draft upload within last 24 hours.
- itemError (array of objects) – human-readable upload error details (fields like error_code, error_detail shown in examples, but not fully enumerated).

Presence: kind, id always present on success; uploadState present with one of the enum values; itemError only when there was an upload failure.

Response variants:

- Successful hit: HTTP 200 with Item Resource as above.
- No recent upload: HTTP 200 with uploadState: "NOT_FOUND".
- Error (auth, ownership, etc.): Google-standard error JSON (not specific to Web Store API).

Metadata not present: ratings, rating_count, user_count/install count, description, category, last_updated, permissions, developer info – none are exposed here.

Zima classification: out_of_scope for extension metadata; purely developer/publisher workflow.

#### 1.2 POST https://www.googleapis.com/upload/chromewebstore/v1.1/items?uploadType=media (insert)

Purpose: Upload a new item (first-time extension upload).

Entity type: browser_extension (new package archive).

Auth: OAuth 2.0, scope https://www.googleapis.com/auth/chromewebstore.

Request: Media upload (extension .zip); no JSON body.

Response: Item Resource (same schema as above) with id, uploadState, possibly itemError.

Zima classification: out_of_scope (developer publishing only).

#### 1.3 POST https://www.googleapis.com/chromewebstore/v1.1/items/{itemId}/publish

Purpose: Publish draft version for review and release.

Key params:

- publishTarget query: "trustedTesters" or "default" (optional; default default).
- Optional deployPercentage, reviewExemption in query/body.

Response example:

- kind ("chromewebstore#item"),
- item_id (string),
- status (array of status codes like OK, ITEM_PENDING_REVIEW, ITEM_TAKEN_DOWN, etc.),
- statusDetail (array of human-readable messages).

Zima classification: out_of_scope (no risk/inventory metadata).

#### 1.4 PUT /upload/chromewebstore/v1.1/items/{itemId} and PUT /chromewebstore/v1.1/items/{itemId} (update)

Purpose: Update existing item draft; upload new package and/or metadata.

Auth and semantics: Similar to insert/publish; still developer-centric.

Zima classification: out_of_scope.

#### 1.5 Official API conclusion

Chrome's own docs describe this API as for programmatically publish/manage Web Store items, not as a public metadata/ratings endpoint.

Community answers state there is no public API for Web Store ratings/metadata; the publish API is for updating/publishing, not analytics.

Therefore, any provider that returns ratings, permissions, install counts, etc., is not using a documented, stable Google metadata API.

### 2) Unofficial Metadata Clients / Scrapers (basis for chrome_web_store_api)

In practice, chrome_web_store_api as an "extension_metadata_source" must be implemented via scraping or internal RPC reverse-engineering.

#### 2.1 chrome-extension-info (Python) – ChromeWebStoreClient

This package is a clear, modern example of the metadata surface Zima likely wants.

Status: Unofficial; uses scraping/internal structures (not documented in detail) to extract metadata.

Auth: None – hits public Web Store pages / internal endpoints.

Entity type: browser_extension (extension ID or URL).

Constructor:

```python
ChromeWebStoreClient(cache_ttl=3600, rate_limit_delay=1.0)
```

- cache_ttl (seconds; default 3600) – cache lifetime to avoid repeated network hits.
- rate_limit_delay (seconds; default 1.0) – delay between requests to be "respectful of Chrome Web Store servers".

Methods:

**get_extension(extension_id: str) -> ExtensionMetadata**

Purpose: Fetch metadata by extension ID.

- Successful hit: returns ExtensionMetadata instance.
- Not found: raises ExtensionNotFoundError.

**get_extension_by_url(url: str) -> ExtensionMetadata**

Purpose: Extract ID from Web Store URL and fetch metadata.

Semantics similar to get_extension.

**search_extensions(query: str, max_results: int = 10) -> List[ExtensionMetadata]**

Documented but "not yet implemented"; should be treated as unavailable.

Exceptions (used to define response variants):

- ChromeExtensionInfoError – base class.
- ExtensionNotFoundError – item not in Web Store.
- NetworkError – network failures.
- RateLimitError – client-side rate-limit exceeded.
- ParseError – scraper could not parse Web Store response.

ExtensionMetadata dataclass (partial, documented):

```python
@dataclass
class ExtensionMetadata:
    id: str
    name: Optional[str]
    description: Optional[str]
    version: Optional[str]
    developer: Optional[str]
    user_count: Optional[int]
    rating: Optional[float]
    # ... and many more fields
```

Available metadata categories (documented high-level, field names summarized by category):

- Basic Info: name, description, version, extension ID.
- Developer: developer name, website, support URL, privacy policy URL.
- Stats: user_count, rating, rating_count.
- Technical: size, languages, manifest_version, permissions.
- Store Info: category, last_updated date, featured status.
- Assets: icon_url, screenshot_urls.

Field-by-field optionality is only explicitly shown for a subset (name, description, version, developer, user_count, rating are Optional[...]), but by analogy all non-core fields should be treated as optional at mapping time.

Response variants:

- Hit: ExtensionMetadata with id always populated and other fields present when parseable.
- No-hit: raises ExtensionNotFoundError.
- Partial result: fields may be None where unavailable or parse fails (implied by Optional types and ParseError).
- Error: throws one of the error classes above; caller must handle and treat as metadata-missing condition.

Enums/status:

No documented enums for category, permissions, or featured flag; values are taken verbatim from Web Store pages or manifests.

Permissions correspond to Chrome's manifest permission names and host permissions as documented separately (e.g., tabs, history, webRequest, cookies, host_permissions patterns, etc.).

These are strings; Zima should not treat them as an enum from this provider.

Stability/fragility:

Because Chrome has no public ratings/metadata API, this library necessarily depends on HTML structure or internal RPC endpoints that may change at any time.

The library implements caching and rate limiting, but no contractual guarantees of schema or uptime.

#### 2.2 simov/chrome-webstore (Node)

Methods shown: items({category, search}), detail({id}), reviews({id}), issues({id}).

It clearly scrapes store pages, returning search results, detailed metadata, reviews, and issues.

Fields are not fully documented; examples indicate access to title, ratings, review counts, etc., similar to StackOverflow CLI output (name, version, image, interactionCount.UserDownloads, ratingValue, ratingCount).

This confirms that ratings and install counts can be scraped but not via official API.

#### 2.3 Chrome Web Store scraping patterns

Example CLI output from a scraping module shows JSON fields: name, url, image, version, price, priceCurrency, interactionCount.UserDownloads, operatingSystems, ratingValue, ratingCount, id.

Gists show use of the internal endpoint /_/ChromeWebStoreConsumerFeUi/data/batchexecute and HTML <script> tags to retrieve structured JSON, again via scraping, not documented APIs.

Third-party services like Apify's Chrome Extension Scraper claim to extract developer information, category, ratings, review counts, user installation counts, icon and cover images, and the full manifest (including permissions), reinforcing that all of this is technically retrievable but not contractually stable.

## Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|--------|---|---|---|---|---|---|---|---|
| browser_inventory | enrichment_only | get_extension(extension_id) | Unofficial Web Store metadata client (e.g., ChromeWebStoreClient.get_extension) | enrichment_only | browser_extension | Only call for Chrome extensions when a local inventory source has already observed an extension ID; enforce provider-side cache and rate limiting; treat ExtensionNotFoundError as "no store metadata" without failing inventory. |  | Uses scraping/internal endpoints; schema may change; cannot detect local presence, only enrich known IDs. |
| browser_inventory | enrichment_only | get_extension_by_url(url) | Same client, parses extension ID from Chrome Web Store URL | enrichment_only | browser_extension | Use only when a full Web Store URL is available (e.g., from other systems); otherwise prefer get_extension by ID; same caching/rate-limit behaviour; treat not-found and parse errors as metadata-missing. |  | Optional helper; not necessary if inventory always stores IDs. |
| extension_risk | enrichment_only | get_extension(extension_id) | Unofficial Web Store metadata client | enrichment_only | browser_extension | Use only for extensions already known to be installed from other telemetry; consume permissions, last_updated, manifest_version, stats, developer info as risk factors; never emit standalone risk signals from this metadata alone. |  | Risk scoring must combine this metadata with local behaviour or threat intel; metadata alone is contextual. |
| extension_risk | enrichment_only | get_extension_by_url(url) | Same client, by URL | enrichment_only | browser_extension | Use where risk workflows are keyed by Web Store URLs rather than IDs (e.g., imported admin lists); treat as enrichment only. |  | Helper, not primary. |
| extension_risk | out_of_scope | official_publish_api | https://www.googleapis.com/chromewebstore/v1.1/items/* (publish/manage endpoints) | out_of_scope | browser_extension | Do not integrate; requires owning developer credentials and does not expose ratings/permissions/user counts. |  | Only relevant to extension developers, not Zima consumers. |

## Signal Contracts Severity and Tags

No standalone module-level signals should be emitted directly from chrome_web_store_api at this stage. The resulting table is intentionally empty.

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|--------|--------|----------|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

**Reasoning:**

Chrome Web Store metadata is contextual: it exposes risk potential (permissions, outdated, low rating) but not direct compromise.

There is no field that guarantees malicious behaviour or direct data exposure (e.g., no "this extension is malware" flag from Chrome).

Official docs and community commentary emphasise that the API surface is for publishing, and that there is no public ratings/metadata API; any metadata client is scraping-based and therefore too fragile to anchor critical signals.

Zima's severity guide reserves critical/high for direct credential exposure, active malware/C2, confirmed breach, or exposed PII—none of which can be inferred with high confidence from store metadata alone.

Instead, metadata from this provider should be attached to signals produced by other modules (e.g., endpoint-detected malicious extension) as enrichment.

## Confidence Guidance

While chrome_web_store_api does not itself produce signals, higher-level Zima rules may combine its metadata with other evidence. Suggested severity mapping for those combined rules, not for this provider alone:

- Permissions indicating broad data access (e.g., history, webRequest, tabs, broad host permissions) should increase the severity of any independently confirmed malicious extension finding, but not create new findings.
- Very stale last_updated (e.g., not updated in several years) plus powerful permissions and low rating may justify escalating a medium-severity "risky_extension_installed" signal when the extension is locally present, but that signal would be owned by extension_risk, not this provider.
- Low install count alone (e.g., near-zero user_count) should at most influence prioritization, not severity, since new legitimate extensions also have low counts.
- For this research pass, do not codify these into provider-level rules.py; they belong in the extension_risk rules that consume enrichment.

### Confidence Guidance Table

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|--------|---|---|---|---|---|
| browser_inventory | Enrich inventory entries with Web Store metadata | Official Web Store content is generally accurate, but access is via scraping/internal endpoints, not a stable API. | Fields may lag real-time by Web Store caching; cache_ttl and rate_limit_delay in client add another 1h+ of staleness. | Cross-check extension id and version against local manifest/management APIs when available to detect mismatches or stale store info. | Measure hit-rate, field completeness, and error frequency across fleet; tune cache TTL and retry strategy based on observed stability. |
| browser_inventory | Populate human-readable name/publisher/category | Name and developer fields come directly from store listing; typically accurate but may change on updates. | Metadata may change when developers rebrand or transfer ownership; store may update without notice. | If local manifest metadata (e.g., name) conflicts with store, prefer local value for installed extension, storing both for audit. | Track frequency of name/publisher changes over time and decide whether to snapshot or always refresh for inventory UI. |
| extension_risk | Use permissions and host_permissions as risk input | Permissions and host patterns come from extension manifests; these are authoritative for what code can do. | Permissions only change on extension update; last_updated from store helps detect staleness. | Corroborate with local browser APIs (e.g., chrome.management) or local manifest to confirm that installed version and permissions align with store metadata. | Build a permission-to-risk taxonomy aligned with Chrome's permission guidance; calibrate risk scores empirically using known-bad extensions. |
| extension_risk | Use rating/user_count as weak reputation signals | Ratings and user counts come from store UI; scraping may miss or misparse values if layout changes. | Ratings can shift quickly; user_count is coarse-grained and updated on Google's schedule; not real-time. | Combine low rating with powerful permissions and external threat intel or EDR detections before increasing severity; never use rating alone as a signal trigger. | Analyze historical correlation between ratings/user_counts and confirmed malicious extensions to determine whether these metrics meaningfully improve triage. |
| extension_risk | Use last_updated/manifest_version for outdated risk | last_updated and manifest_version are scraped from store listing; generally correct for published version. | May not reflect side-loaded or enterprise-distributed versions; also not useful when extension is unpublished. | Cross-check with locally installed version; consider outdated risk only when installed version matches an old published version and extension has strong permissions. | Tune thresholds for "too old" (e.g., >N years) based on Chrome deprecation timelines and empirical exploit data; avoid over-alerting on benign but stable tools. |

## Implementation Notes

### Strongest usable enrichment fields

From scraping-based clients like chrome-extension-info (and similar Node scrapers), the most valuable fields for Zima are:

- Identity & presentation: id, name, description, version, icon_url, screenshot_urls.
- Developer / publisher: developer name, website, support URL, privacy policy URL.
- Technical/manifest: manifest_version, permissions, languages, size (and potentially host-permission patterns if exposed).
- Store context: category, last_updated, featured flag.
- Reputation stats: user_count, rating, rating_count (purely as weak signals).

These fields strongly support inventory enrichment and risk scoring inputs but not standalone incident detection.

### Strongest signal types, if any

At the provider boundary there are no justified standalone signal types. Any resulting signals should be owned by higher-level modules that combine:

- Local evidence of installation (from endpoint/browser telemetry),
- Behavioural detections (e.g., data exfiltration patterns), and
- External threat intelligence.

chrome_web_store_api acts only as a metadata/enrichment feed into those decisions.

### What the provider should not be used for

- Not for detecting local extension presence – this must come from endpoint/browser telemetry (chrome.management, OSQuery, or similar), not Web Store.
- Not for direct compromise/breach detection – no evidence of credential theft, stealer logs, PII exposure, or malware C2 lives in store metadata.
- Not for publishing or managing customer-owned extensions – that would require developer OAuth credentials for each extension, and is outside Zima's scope.
- Not for high-confidence malicious classification solely from low ratings or low user counts – too noisy and prone to false positives.

### API/auth/rate-limit/licensing/package-stability cautions

- There is no official public ratings/metadata API; only the publish API is documented, and it does not expose ratings/install counts/permissions.
- All metadata clients (Python or Node) rely on scraping and/or undocumented internal RPC endpoints whose schema, URLs, or parameters may change without notice, potentially breaking the provider.
- chrome-extension-info implements self-imposed rate limiting and caching (rate_limit_delay, cache_ttl) to avoid over-hitting Web Store; Zima should respect and possibly tune these knobs.
- Excessive scraping traffic might trigger anti-bot protections; some third-party services (e.g., Apify) explicitly require residential proxies and JS rendering to reliably scrape Web Store, which underscores fragility.
- Licencing: these libraries are MIT-licensed open-source, but they sit on top of Google's terms of service for automatic access to Chrome Web Store; legal/compliance review is advisable before large-scale scraping.

### Overall role in current Zima stage

For the current Zima stage:

- Treat chrome_web_store_api as enrichment_only and extension_metadata_source.
- Wire it into:
  - browser_inventory for naming and contextualizing installed Chrome extensions.
  - extension_risk as a data feed (permissions, last_updated, manifest_version, stats) into risk scoring logic.
- Do not create direct rules.py entries that emit standalone signals solely from this provider; use it only in mappers and correlation/risk engines.

## Provider Summary and Structured JSON

```json
{
  "provider": "chrome_web_store_api",
  "provider_category": "cloud",
  "provider_role": "enrichment_only",
  "module_mappings": [
    {
      "module": "browser_inventory",
      "provider_role": "enrichment_only",
      "provider_method": "get_extension",
      "endpoint_or_artifact": "Unofficial Chrome Web Store metadata client (e.g., ChromeWebStoreClient.get_extension)",
      "classification": "enrichment_only",
      "entity_types": ["browser_extension"],
      "gating_logic": "Only call for Chrome extensions discovered by local inventory; respect cache_ttl and rate_limit_delay; treat ExtensionNotFoundError as metadata-missing and do not fail inventory.",
      "citation_refs": ["web:33", "web:9", "web:6"],
      "notes": "Scraping-based; schema and availability may change without notice."
    },
    {
      "module": "browser_inventory",
      "provider_role": "enrichment_only",
      "provider_method": "get_extension_by_url",
      "endpoint_or_artifact": "Same client, fetch by Chrome Web Store URL",
      "classification": "enrichment_only",
      "entity_types": ["browser_extension"],
      "gating_logic": "Use when only Web Store URL is available; otherwise prefer get_extension by ID; same cache and error handling behaviour.",
      "citation_refs": ["web:33"],
      "notes": "Helper for URL-based workflows; not primary discovery mechanism."
    },
    {
      "module": "extension_risk",
      "provider_role": "enrichment_only",
      "provider_method": "get_extension",
      "endpoint_or_artifact": "Unofficial Chrome Web Store metadata client",
      "classification": "enrichment_only",
      "entity_types": ["browser_extension"],
      "gating_logic": "Use only for extensions already confirmed installed; consume permissions, last_updated, manifest_version, stats, and developer info as risk inputs; never generate standalone signals from this metadata alone.",
      "citation_refs": ["web:33", "web:29", "web:32", "web:11"],
      "notes": "Feeds risk scoring; signals should be emitted by higher-level rules that combine this with local behaviour or threat intel."
    },
    {
      "module": "extension_risk",
      "provider_role": "enrichment_only",
      "provider_method": "get_extension_by_url",
      "endpoint_or_artifact": "Same client, fetch by URL",
      "classification": "enrichment_only",
      "entity_types": ["browser_extension"],
      "gating_logic": "Use where risk workflows are keyed by Web Store URLs rather than IDs; same enrichment-only semantics.",
      "citation_refs": ["web:33"],
      "notes": "Optional helper; same risks and limitations as get_extension."
    },
    {
      "module": "extension_risk",
      "provider_role": "enrichment_only",
      "provider_method": "official_chrome_webstore_publish_api_v1",
      "endpoint_or_artifact": "https://www.googleapis.com/chromewebstore/v1.1/items/*",
      "classification": "out_of_scope",
      "entity_types": ["browser_extension"],
      "gating_logic": "Do not use; requires owning developer credentials and exposes only publish/upload status, not ratings/permissions/user counts.",
      "citation_refs": ["web:26", "web:14", "web:11"],
      "notes": "Developer-only; irrelevant for consumer-side extension risk or inventory."
    }
  ],
  "signal_contracts": [],
  "confidence_guidance": [
    {
      "module": "browser_inventory",
      "signal_type_or_use_case": "enrich_inventory_with_webstore_metadata",
      "source_reliability": "Underlying Web Store data is authoritative, but access via scraping is unofficial and prone to breakage when layouts or internal endpoints change.",
      "freshness_considerations": "Metadata reflects latest published Web Store state plus client cache_ttl; may lag real-time installs or developer changes by hours or longer.",
      "corroboration_rules": "Cross-check id and version against local manifest/management APIs when available; treat discrepancies as informational rather than errors.",
      "calibration_todo": "Measure error rate and field completeness across fleet; adjust cache_ttl and request backoff to balance freshness vs. reliability."
    },
    {
      "module": "browser_inventory",
      "signal_type_or_use_case": "populate_name_publisher_category",
      "source_reliability": "Names and developer info are defined by the publisher in the store listing and typically accurate; they can change on rebranding or ownership transfer.",
      "freshness_considerations": "Name/publisher/category updates may appear in Web Store without any change to installed extension code; local manifests may briefly diverge.",
      "corroboration_rules": "If local manifest name differs from store name, prefer local for the installed instance and keep store name as secondary label.",
      "calibration_todo": "Track rate of publisher/name changes; decide whether to snapshot at install time vs. continuously refreshing for UI searchability."
    },
    {
      "module": "extension_risk",
      "signal_type_or_use_case": "permissions_based_risk_scoring",
      "source_reliability": "Permissions and host patterns derive from extension manifests and accurately represent potential capabilities.",
      "freshness_considerations": "Permissions only change on extension updates; last_updated and manifest_version from store help infer staleness.",
      "corroboration_rules": "Verify permissions against locally installed manifest or browser management APIs where possible to ensure store data matches installed version.",
      "calibration_todo": "Define a permission-to-risk taxonomy using Chrome's permission guidance and validate scores against known malicious extensions."
    },
    {
      "module": "extension_risk",
      "signal_type_or_use_case": "rating_usercount_reputation_signals",
      "source_reliability": "Ratings and user counts come from store UI; scraping makes them vulnerable to layout changes and occasional parse errors.",
      "freshness_considerations": "Ratings can change rapidly; user counts are often coarse and updated on Google's schedule, not in real time.",
      "corroboration_rules": "Use low rating/high complaints only as a modifier when combined with strong permissions and independent detections; never as standalone evidence.",
      "calibration_todo": "Analyze historical distribution of ratings for malicious vs. benign extensions to determine whether these metrics improve triage."
    },
    {
      "module": "extension_risk",
      "signal_type_or_use_case": "outdated_extension_risk",
      "source_reliability": "last_updated and manifest_version reflect the published store listing for the extension.",
      "freshness_considerations": "Not meaningful for side-loaded or enterprise-only extensions; installed version may differ from latest store version.",
      "corroboration_rules": "Compare installed version to latest store version; consider age plus powerful permissions before adjusting severity.",
      "calibration_todo": "Choose thresholds for when an extension is considered too old (e.g., multiple years without updates) based on exploit data and Chrome deprecation timelines."
    }
  ]
}
```
