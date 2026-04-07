---
title: "output / cloud / firefox_addons_site_api"
aliases: ["firefox_addons_site_api output", "firefox_addons_site_api signal registry"]
tags: [zima, research, outputs, signal-registry, cloud, firefox_addons_site_api, graph_exclude]
type: provider_research_output
provider: firefox_addons_site_api
provider_category: cloud
status: complete
prompt_note: prompt.md
provider_folder: firefox_addons_site_api.md
obsidianUIMode: preview
---

## API Surface Appendix

### 1. GET /api/v5/addons/addon/(int:id|string:slug|string:guid)/ – Add-on Detail

#### Purpose and role

Primary read-only metadata endpoint for a single add-on, addressable by AMO integer id, slug, or GUID. For Zima, this is the main enrichment source for Firefox extension records.

#### Supported entities / identifiers

- id (int): AMO internal numeric id.
- slug (string): human-readable add-on slug used in URLs.
- guid (string): WebExtension identifier, matching the extension's manifest id and serving as the canonical extension ID across Firefox.

Zima's logical entity is a browser extension; mapping between internal entity_type (e.g. extension or url) and AMO identifiers should be handled in the provider client.

#### Auth and access model

- Public, listed add-ons (standard store entries) are accessible without authentication.
- Non-public add-ons and add-ons with only unlisted versions require authentication plus reviewer or developer permissions; otherwise the API returns 401/403 with a JSON body including detail, is_disabled_by_developer, and is_disabled_by_mozilla flags.
- Endpoint is documented as part of the v5 API, which is "considered stable" but not frozen—fields may evolve over time as required by Mozilla's frontend.

#### Key query parameters

- app (string): add-on application (e.g. firefox, android), used with appversion to adjust current_version.
- appversion (string): version string (e.g. 46.0); used to select a compatible current_version for some add-on types.
- lang (string): language code; when supplied, translated fields (e.g. name, description) are returned primarily in that language.
- show_grouped_ratings (bool): include ratings.grouped_counts histogram.

#### Top-level response fields (selected)

**Identity & classification:**

- id (int): AMO numeric id.
- guid (string): extension identifier.
- slug (string): add-on slug.
- type (string): add-on type; for extensions this is extension.

**Naming and localization:**

- name (object|null): translated name map keyed by locale, or single-language map when lang is used.
- summary (object|null): short description (supports linkification; may contain HTML links).
- description (object|null): longer description; may contain HTML tags.

**Popularity and usage:**

- average_daily_users (int): average daily users, updated daily.
- weekly_downloads (int): downloads in last week.

**Lifecycle and status:**

- created (string): creation timestamp.
- last_updated (string): last developer update timestamp.
- status (string): add-on status; enum values: public, deleted, disabled, nominated, incomplete.
- is_disabled (boolean): whether the listing is disabled.

**Trust / policy indicators:**

- has_eula (boolean): whether a EULA must be accepted.
- has_privacy_policy (boolean): whether a privacy policy is present.
- promoted (object|null): promotion metadata; category (e.g. line, recommended, sponsored, verified, badged) and apps list.
- requires_payment (boolean): whether non-free services, software, or hardware are required.
- is_experimental (boolean): developer-marked experimental flag.

**Ratings & reviews:**

- ratings (object): includes count, text_count, average, bayesian_average, and optional grouped_counts histogram (1–5 stars).
- ratings_url (string): review listing URL.

**Taxonomy & tagging:**

- categories (object): per-application arrays of category slugs (e.g. productivity, combined with type to get display category).
- tags (array of string): freeform tags set by developers or AMO.

**Links / presentation:**

- icon_url (string) and icons (object of size→URL): icon URLs with cache-busting query strings.
- previews (array): screenshots and thumbnails with dimensions and captions.
- homepage, support_url, contributions_url: translated outgoing URLs wrapped through Mozilla's outgoing redirector; structure is {"url": ..., "outgoing": ...} or translated-object variants.

**Version linkage:**

- current_version (object): the current public version; references the same schema as Version Detail but with trimmed license text for performance.
- latest_unlisted_version (object|null): latest unlisted version (restricted to reviewers/developers).
- versions_url (string): HTML version history page.

#### Presence, optionality, and variants

- Most structural fields (id, guid, slug, type, status, created, last_updated) are always present for public add-ons.
- Many text fields (description, summary, developer_comments, homepage, support_email, support_url) may be null if not defined.
- promoted is null if the add-on is not in a promoted category.
- ratings.grouped_counts is only returned when show_grouped_ratings=true.
- latest_unlisted_version is only exposed to authenticated developers/reviewers.

#### No-hit and error behavior

- Non-existent id/slug/guid returns 404 Not Found.
- Non-public matching add-ons without suitable auth return 401/403 with detail and the is_disabled_by_* flags, which Zima should treat as no public listing for enrichment, not as a risk signal by itself.

#### Implementation notes for Zima

- Prefer guid as the canonical key when available; fall back to slug or id as needed.
- Consider passing lang=en-US (or deployment default) to simplify translated-field shapes; otherwise fields like name become multi-locale maps.
- Treat status, is_disabled, promoted.category, average_daily_users, weekly_downloads, ratings.average, last_updated, is_experimental, has_privacy_policy, and requires_payment as primary enrichment fields for risk modeling, not standalone signals.

### 2. GET /api/v5/addons/addon/(addon_id|addon_slug|addon_guid)/versions/ – Versions List

#### Purpose and role

Lists versions for a specific add-on, primarily for UI/management and reviewer workflows. For Zima, this can be used to retrieve historical version metadata or locate the latest listed version id when current_version alone is insufficient.

#### Auth and filtering

By default, returns only public versions (excluding incomplete, disabled, deleted, rejected, or flagged-for-review files).

filter parameter allows broader visibility:

- all_without_unlisted: all listed versions (requires developer or reviewer access).
- all_with_unlisted: all versions including unlisted (developer or reviewer).
- all_with_deleted: all versions including deleted (admin only).

#### Key query parameters and pagination

- filter (string): visibility as above.
- lang (string): localization for translated fields.
- page, page_size (default 25, max 50 for most v5 lists per overview): paginated list semantics.

#### Response fields (paginated wrapper)

- count (int): total versions.
- next, previous (string|null): page URLs.
- results (array): version objects matching the Version Detail schema but often with trimmed fields (e.g., license text omitted per v5 changelog).

#### Zima usage

Typically not required if current_version and a single Version Detail call provide enough data for permissions and risk enrichment.

Could be used opportunistically to analyze update cadence or long-term permission drift, but that is more advanced modeling and not required for initial integration.

### 3. GET /api/v5/addons/addon/(addon_id|addon_slug|addon_guid)/versions/(int:id|string:version_number)/ – Version Detail

#### Purpose and role

Returns detailed metadata about a specific add-on version, including WebExtension permissions and host permissions, which are a core input into extension risk modeling.

#### Identifier behavior

Path segment accepts either a numeric id or a version string (e.g. 1.2.3).

If the segment does not contain a dot (.), it is interpreted as an id; to force lookup by version string without dots, prefix with v (e.g. v1).

#### Key fields relevant to Zima

- id (int): version id.
- channel (string): listed or unlisted (visibility on AMO).
- compatibility (object): per-application min and max versions; keys include firefox and android.
- file.id (int), file.created (string), file.size (int), file.hash (string), file.url (string): file identity, timestamp, size, checksum, and download URL.

**Permission arrays (all empty for non-WebExtensions):**

- file.permissions[] (array of string): required WebExtension permissions.
- file.optional_permissions[] (array of string): optional permissions.
- file.host_permissions[] (array of string): host permission patterns (e.g. <all_urls>, *://example.com/*).

In the v5 changelog, host_permissions is explicitly documented as part of Version Detail, confirming stability.

**Data-collection permission arrays (v5+):**

- file.data_collection_permissions[] (array of string): declared data-collection permission categories (added in 2025-06-26 per changelog; not yet detailed in extracted text but documented as part of Version Detail and add-on search).
- file.optional_data_collection_permissions[] (array of string): optional data-collection permissions (same changelog entry).
- file.is_mozilla_signed_extension (boolean): indicates signing by Mozilla internal certificate.
- file.status (string): file status; enums: public, disabled, unreviewed.
- license.*, release_notes, reviewed, is_strict_compatibility_enabled, source, version string: standard version metadata.

#### Presence and variants

- Permission arrays are empty (but present) for non-WebExtensions; for typical WebExtensions they contain manifest-driven permission strings.
- is_disabled is only present for authenticated developers/reviewers and should be ignored for Zima since only public listed versions will be queried.

#### Zima usage

For enrichment, call Version Detail for the current_version.id returned from Add-on Detail when fine-grained permissions or host patterns are needed beyond what is mirrored in current_version.

Cache file.permissions, file.optional_permissions, file.host_permissions, and data-collection-related arrays in enrichment, but do not infer user-tracking or PII exfiltration risk solely from these names without additional heuristics or cross-provider context.

### 4. GET /api/v5/addons/search/ – Add-on Search

#### Purpose and role

Searches public add-ons using a rich set of filters (query q, app, author, category, promotion, popularity, ratings, users). For Zima, this is primarily a utility endpoint to resolve identifiers when only partial data (name, author, etc.) is known.

#### Key query parameters

**Full-text / filters:** q, author, category, tag, type.

**Popularity / thresholds:** ratings, users, plus threshold-style __gt, __lt, __gte, __lte suffixes for numeric/date fields.

**App compatibility:** app, appversion.

**Promotion:** promoted (e.g. recommended, line, badged, sponsored, verified).

#### Response shape

Identical pagination wrapper as other list endpoints (count, next, previous, results).

results objects use the same Add-on Detail schema but omit heavy fields (current_version.license.text, current_version.release_notes, and authors.picture_url) for performance; they also include an elastically computed _score relevancy value.

#### Zima usage

Use as a fallback identifier resolution when the browser inventory provides only a human-readable name, partial slug, or GUID that might not be exact.

Once a unique match is resolved, Zima should pivot to the canonical Add-on Detail and optionally Version Detail endpoints rather than relying on search responses as a primary metadata source.

### 5. GET /api/v5/addons/autocomplete/ – Autocomplete Search

#### Purpose and role

Simplified search endpoint designed for autocomplete UI; always returns at most 10 results and a very small subset of fields.

#### Differences from /search/

- No pagination metadata (count, next, previous).
- page and page_size are ignored; always up to 10 results.
- sort parameter is unsupported; ordering is by relevance or the same default as search when q is absent.
- Result objects contain only: id, icon_url, icons, name, promoted, type, url.

#### Zima usage

Optional utility for quick resolution of ambiguous extension names from UI workflows; for backend correlation, /addons/search/ is generally more flexible.

### 6. GET /api/v5/addons/browser-mappings/ – Browser Mappings

#### Purpose and role

Provides mappings between non-Firefox extension identifiers and Firefox add-on GUIDs to support Firefox's extension import feature (e.g. mapping Chrome extension IDs to corresponding AMO entries).

#### Key parameters and response

- browser (string, required): currently documented value is chrome.
- page_size (int, optional): maximum results per page; default is documented as 100, which is higher than the usual 25 for other endpoints.

Response: `{ "results": [ { "extension_id": "<non-Firefox ID>", "addon_guid": "<Firefox GUID>" }, ... ] }`.

#### Zima usage

Can be used at the correlation layer to map Chrome (or other browser) extension ids to Firefox GUIDs and then reuse the same AMO metadata enrichment pipeline, but it does not by itself expose risk-related fields.

For Zima's firefox_addons_site_api provider, this endpoint is utility-only rather than core enrichment.

### 7. GET /api/v5/site/ – Site Status (optional utility)

#### Purpose and role

Provides a simple JSON indicator of whether AMO is in read-only mode and an optional human-readable notice.

#### Response fields

- read_only (boolean): whether the site is in read-only (maintenance) mode.
- notice (string|null): site-wide notice that clients should surface to users if relevant.

#### Zima usage

Optional health-check endpoint in the provider client; not needed for enrichment or risk modeling.

### 8. EULA / Privacy Policy Endpoint (optional)

The v5 changelog and related GitHub issues reference an /api/v5/addons/addon/(id|slug|guid)/eula_policy/ endpoint that exposes or manages EULA and privacy-policy text for non-theme add-ons. Public documentation extracted here does not fully describe the schema, but usage examples show it returning structured eula and privacy_policy content for a given add-on id.

#### Zima usage

Given that has_eula and has_privacy_policy booleans are already exposed via Add-on Detail, and policies themselves can be lengthy, Zima should treat this endpoint as out-of-scope for enrichment at this stage to avoid heavy text ingestion and policy-interpretation responsibilities.

### 9. Request / response behavior, CORS, and stability

All documented v5 endpoints expect Content-Type: application/json for JSON-based requests and return JSON bodies.

The overview explicitly notes that all APIs are available cross-origin (CORS-enabled) unless otherwise specified, which covers the add-ons endpoints detailed above.

v5 is the current default API and is "considered stable" but not frozen; v4 is explicitly frozen and more stable but lacks newer fields like data-collection permissions and browser mappings.

No explicit numeric rate limits are documented for read-only endpoints; community threads and documentation indicate that AMO uses throttling (e.g. 429 responses) mainly for submission and signing APIs and to prevent abuse, not regular metadata queries.

## Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|--------|---|---|---|---|---|---|---|---|
| extension_risk | enrichment_only | get_addon_detail | GET /api/v5/addons/addon/(id\|slug\|guid)/ | enrichment_only | extension (guid, slug, AMO id) | Only call when a Firefox extension identifier (GUID, AMO id, or known slug) is available from inventory or correlation; treat 404/401/403 for non-public add-ons as no-hit, not as a risk condition by itself. | https://dokk.org/documentation/mozilla-addons-server/2024.05.30/sources/topics/api/addons.rst.txt | Provides authoritative metadata (name, categories, popularity, ratings, promotion, status, experiment flag, privacy-policy/EULA presence) that feeds extension risk models but does not, on its own, indicate compromise or abuse. |
| extension_risk | enrichment_only | get_version_detail | GET /api/v5/addons/addon/(addon_id\|addon_slug\|addon_guid)/versions/(id\|version_number)/ | enrichment_only | extension version (AMO version id or version string) | Only call for the current_version id returned from Add-on Detail, and only for add-ons of type=extension; skip for themes, dictionaries, etc. | https://dokk.org/documentation/mozilla-addons-server/2024.05.30/sources/topics/api/addons.rst.txt | Used to enrich installed extensions with concrete WebExtension permission arrays, host permissions, file size/hash, and data-collection permission flags; Zima should treat these as risk features, not direct alerts. |
| extension_risk | enrichment_only | search_addon | GET /api/v5/addons/search/ | utility_only | extension (name, guid, slug, author) | Use only to resolve ambiguous or partial identifiers (name, author, approximate slug) into a unique AMO record; once resolved, switch to Add-on Detail for enrichment. | https://addons-server.readthedocs.io/en/stable/topics/api/addons.html | Convenience lookup; result objects are truncated compared to Add-on Detail and still do not justify standalone risk signals. |
| extension_risk | enrichment_only | autocomplete_addon | GET /api/v5/addons/autocomplete/ | utility_only | extension (name) | Optional; use for UI-facing autocomplete or fuzzy name resolution but not for back-end correlation where full search is preferable. | https://dokk.org/documentation/mozilla-addons-server/2024.05.30/sources/topics/api/addons.rst.txt | Limited fields (id, icon, name, promoted, type, url) make this unsuitable as a primary enrichment source. |
| extension_risk | enrichment_only | browser_mappings | GET /api/v5/addons/browser-mappings/ | utility_only | non-Firefox extension id → Firefox GUID | Optional correlation helper if Zima later correlates Chrome (or other) extensions to Firefox equivalents; currently non-essential for Firefox-focused enrichment. | https://dokk.org/documentation/mozilla-addons-server/2024.05.30/sources/topics/api/addons.rst.txt | Does not contain risk fields; just mapping rows {extension_id, addon_guid}. |
| extension_risk | enrichment_only | site_status | GET /api/v5/site/ | utility_only | n/a | Optional pre-flight check before bulk lookups; not required for correctness. | https://mozilla.github.io/addons-server/topics/api/overview.html | Can be used to short-circuit writes (out of scope for Zima) or explain temporary outages; not security-relevant. |
| browser_inventory | enrichment_only | get_addon_detail | GET /api/v5/addons/addon/(id\|slug\|guid)/ | enrichment_only | extension (guid, slug, AMO id) | Only call after a local Firefox inventory provider has detected an installed extension and produced its identifier; do not attempt to infer installation from AMO data alone. | https://dokk.org/documentation/mozilla-addons-server/2024.05.30/sources/topics/api/addons.rst.txt | Enriches inventory records with canonical name, categories, icon, addon URL, promotion status, and popularity metrics; no standalone risk semantics. |
| browser_inventory | enrichment_only | get_version_detail | GET /api/v5/addons/addon/(addon_id\|addon_slug\|addon_guid)/versions/(id\|version_number)/ | enrichment_only | extension version (AMO version id or version string) | Only for installed extensions where specific version information is known or resolvable via current_version; skip for stale or mismatched mapping. | https://dokk.org/documentation/mozilla-addons-server/2024.05.30/sources/topics/api/addons.rst.txt | Enriches inventory with installed version, compatibility, and size; permission arrays can be stored for later analysis but should not themselves create inventory signals. |
| browser_inventory | enrichment_only | search_addon | GET /api/v5/addons/search/ | utility_only | extension (name, guid, slug, author) | Optional when only name or partial slug is available from local inventory (e.g., user-installed sideloaded extensions pointing to AMO listing). | https://addons-server.readthedocs.io/en/stable/topics/api/addons.html | Same utility considerations as for extension_risk; should not be relied upon to prove installation. |
| browser_inventory | enrichment_only | autocomplete_addon | GET /api/v5/addons/autocomplete/ | utility_only | extension (name) | Optional fallback in UI or troubleshooting tools; not required in automated pipelines. | https://dokk.org/documentation/mozilla-addons-server/2024.05.30/sources/topics/api/addons.rst.txt | Limited schema; use only for hinting the operator, not as canonical metadata. |
| browser_inventory | enrichment_only | browser_mappings | GET /api/v5/addons/browser-mappings/ | utility_only | non-Firefox extension id → Firefox GUID | Only if Zima later wants to correlate cross-browser inventories; not required when focusing on Firefox-only inventories. | https://dokk.org/documentation/mozilla-addons-server/2024.05.30/sources/topics/api/addons.rst.txt | Out-of-band mapping table; should sit in correlation/normalization layer rather than module mappers. |
| browser_inventory | enrichment_only | site_status | GET /api/v5/site/ | utility_only | n/a | Optional; same as for extension_risk. | https://mozilla.github.io/addons-server/topics/api/overview.html | Operational only. |

**Why no direct_signal_input classifications**

All AMO endpoints used by this provider expose store metadata and developer-declared capabilities, not hostile behaviors or confirmed abuse events. None by itself meets Zima's severity definitions for direct breach, malware C2, stealer logs, or credential exposure, so every endpoint remains enrichment-only or utility-only at the module boundary.

## Signal Contracts Severity and Tags

No standalone Zima signals should be emitted directly from firefox_addons_site_api for either extension_risk or browser_inventory at this stage.

The AMO API exposes metadata (permissions, ratings, promotion, status) that are best consumed as features for higher-level risk scoring and policy engines, not as direct evidence of compromise or exposure. For example:

- An extension having <all_urls> host permission or powerful WebExtension APIs (tabs, cookies, webRequestBlocking) does not imply malicious behavior, only capability.
- A low rating average or high number of 1-star ratings indicates possible quality or trust issues but is not, by itself, a confirmed security incident.

Therefore, the Signal Contract Table is intentionally empty.

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|--------|--------|----------|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

**Rationale for no standalone signals**

Given Zima's severity calibration, AMO metadata should not directly produce critical or high severities because:

- It does not expose plaintext credentials, stealer logs, or active malware C2 infrastructure.
- It reflects store-level status and popularity, not direct attack telemetry or confirmed breaches.
- Even strong negative indicators (e.g. status=disabled by Mozilla, poor ratings, high-permission sets) still require correlation with actual installation and usage context and ideally additional threat intel (e.g. blocklists, malware feeds) to meet Zima's thresholds.

Any severity assignment should instead occur in:

- The extension_risk module's internal scoring logic (combining AMO metadata, local install context, and other providers).
- Higher-level detection rules that correlate an installed extension with known malware/blocklists (which may or may not also be backed by AMO data).

As a result, this provider remains strictly enrichment-only, and no severity rules are defined at the provider boundary.

## Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|--------|---|---|---|---|---|
| extension_risk | Enrich installed Firefox extensions with AMO metadata (detail + version) | AMO is Mozilla-operated and the canonical distribution channel for Firefox add-ons; identity fields (guid, slug, id) and store metadata (status, promotion, categories, tags, usage counts) are highly reliable, while descriptive text, homepage, support links, and tags are developer-supplied and should be treated as semi-trusted. | average_daily_users is updated daily and weekly_downloads reflects recent adoption, but last_updated may be stale for extensions that are stable; ratings can lag current user sentiment, and permission arrays reflect the published version, not necessarily what is installed if a client is on an older version. | Always corroborate AMO metadata with local browser inventory (to confirm installation and version), and with any available extension blocklists or threat-intel feeds; do not treat AMO status or ratings alone as proof of maliciousness or safety. | Empirically compare AMO-derived features (permissions, ratings, promotion, last_updated, popularity) across known-bad vs known-good extension sets to calibrate threshold-based risk scoring in extension_risk, and tune how much weight AMO metadata should have relative to other providers. |
| browser_inventory | Enrich Firefox extension inventory records with canonical AMO metadata | Same reliability profile: high confidence in identifiers and structural metadata; moderate confidence in developer-authored descriptions and external URLs (homepage, support, contributions). | Inventory records may lag AMO if users do not auto-update; treat current_version and its permissions as the latest available, not necessarily the installed version; if local inventory provides an explicit version string, prefer Version Detail for that version. | Cross-check AMO metadata with local extension manifests when available, especially permissions and version numbers; if there is a mismatch, prefer local manifest for ground truth while keeping AMO as a reference. | Measure how often AMO current_version diverges from locally installed versions in real fleets and adjust enrichment logic (e.g. always query explicit installed version when known) to avoid misleading risk assessments. |

## Implementation Notes

### 1. Field paths and parsing

**Translated fields:** name, summary, description, developer_comments, homepage, support_email, support_url, and license-related fields are returned as locale→value maps; with lang specified, only the most relevant locale plus metadata like _default may be returned. The mapper should:

- Either treat them as opaque objects stored verbatim in evidence/enrichment, or
- Extract a single preferred locale (e.g. en-US) while preserving the raw object in evidence.

**Outgoing links:** link-bearing objects (homepage, support_url, contributions_url) expose both url and outgoing (wrapped redirect) fields; Zima should store the original url for humans and use either as needed, but must avoid mis-classifying outgoing as a third-party domain.

**Permissions arrays:** ensure these arrays from Version Detail (file.permissions, file.optional_permissions, file.host_permissions, file.data_collection_permissions, file.optional_data_collection_permissions) are preserved exactly as strings; higher-level logic can then categorize them (e.g., powerful vs benign APIs) without lossy transformations.

### 2. No-hit and error handling

- Treat 404 (not found) as "no AMO listing" and return a clean enrichment miss rather than an error to the module; this may occur for sideloaded or self-hosted extensions.
- Treat 401/403 from Add-on Detail or Version List for non-public/unlisted extensions as "not publicly visible" rather than as risk indicators; do not log them as security events.
- For transient 503s (maintenance, read-only mode), retry with backoff or surface a provider health warning rather than failing silently; consider consulting /api/v5/site/ if repeated 503s occur.

### 3. Rate limits, robots, and undocumented-endpoint risk

AMO's v5 API is officially documented, CORS-enabled, and used by Mozilla's own frontend, so it is significantly more stable than scraping HTML or embedded JSON; using these endpoints aligns with Mozilla's intended integration model.

Documentation explicitly warns that v5 is not frozen; fields can change based on frontend requirements. Zima should:

- Avoid strict schema validation that would break on additive fields.
- Log unexpected fields but ignore them by default.
- Pin only to documented fields needed for enrichment.

There is no official numeric rate-limit policy for read-only metadata, but evidence from signing/review workflows shows throttling and 429 responses under high volume. The provider client should:

- Implement conservative client-side throttling and exponential backoff for 429/503 responses.
- Prefer caching and avoiding duplicate lookups for the same guid/id within a short time window.

Because these endpoints are first-party and well-documented, there is no need to rely on brittle scraping of HTML or internal JSON blobs; such scraping should be explicitly prohibited in the implementation.

### 4. Deduplication and natural identifiers

- Prefer the WebExtension guid as the primary deduplication key for extension records across modules and providers; it is globally unique within AMO and reflects the manifest id.
- Use AMO id plus type=extension as a secondary key when guid is missing or ambiguous.
- slug is stable but can be changed by developers; treat it as a human-friendly handle, not a primary key.

### 5. Evidence vs enrichment in Zima

**Evidence fields (typically stored verbatim for audit and deduplication):**

- Identifiers: guid, id, slug.
- Status and promotion: status, is_disabled, promoted.category, promoted.apps.
- Permissions: file.permissions, file.optional_permissions, file.host_permissions, data-collection permissions arrays from Version Detail.
- Popularity and ratings: average_daily_users, weekly_downloads, ratings.*.
- Lifecycle: created, last_updated, channel (from Version Detail), version string.

**Enrichment-only fields (stored as context but not driving deduplication):**

- Display name and summary, category tags, icon URLs, previews.
- Homepage, support links, contributions URLs.
- is_experimental, requires_payment, has_eula, has_privacy_policy, tags, categories.

### 6. Provider client vs module mapper vs correlation layer

**Provider client (for firefox_addons_site_api):**

- Handles HTTP requests, retries, pagination, and raw JSON extraction from AMO endpoints.
- Normalizes identifiers (guid/id/slug) and exposes a stable internal representation for add-on detail and version detail responses.
- Implements caching and rate-limit handling; no risk modeling here.

**Module mapper (extension_risk, browser_inventory):**

- Translates provider-native objects into Zima's normalized enrichment fields (e.g. extension.permissions, extension.promoted_category, extension.avg_daily_users).
- Ensures evidence vs enrichment separation is respected.
- Does not emit standalone signals for this provider.

**Correlation / risk engines:**

- Combine AMO metadata with local install data and other providers (blocklists, malware intelligence) to produce actual extension_risk signals when warranted.
- Owns all severity assignments and conditional logic.

### 7. What is safe to normalize now

Safe to normalize as stable enrichment fields (documented and widely used by Mozilla):

- guid, id, slug, type.
- status, is_disabled, promoted.category, promoted.apps.
- average_daily_users, weekly_downloads, ratings.*.
- created, last_updated, categories, tags.
- is_experimental, requires_payment, has_eula, has_privacy_policy.
- Version Detail's channel, compatibility, file.* including permission arrays and file.status.

Fields that are more presentation-oriented or heavier-weight (e.g. raw description HTML, full EULA or privacy-policy texts, screenshots, and outgoing redirect URLs) should be treated as secondary enrichment and stored if helpful, but not relied upon for stable logic beyond basic display.

## Provider Summary and Structured JSON

### Strongest enrichment uses

- Canonical identification of Firefox extensions via guid, id, and slug, plus categorization and promotion status.
- Popularity and quality signals (average_daily_users, weekly_downloads, ratings.average, ratings.count) for risk scoring heuristics.
- Version-level WebExtension permissions, host permissions, and data-collection permission flags that inform capability-based risk models.

### Standalone signal types

None are justified at this provider boundary; all AMO data should be consumed as enrichment for downstream modules rather than as direct, severity-bearing signals.

### What the provider should not be used for

- Detecting which extensions are installed in a browser (requires local inventory providers).
- Inferring compromise, credential exposure, or active malware solely from AMO metadata.
- Scraping HTML pages or internal JSON used by the AMO frontend when official API endpoints already cover the needed data.

### API/auth/rate-limit/licensing/undocumented-access cautions

- v5 is stable but not frozen; schemas can change, so mappers should tolerate additive changes and avoid assumptions about undocumented fields.
- Read-only metadata is publicly accessible for listed add-ons, but non-public and management endpoints require authentication and are out of scope.
- Rate limits for metadata are undocumented; implement defensive throttling and proper handling of 429/503 responses.
- Avoid undocumented endpoints, including any non-documented JSON payloads discovered through frontend inspection.

### Overall treatment in current Zima stage

firefox_addons_site_api should be treated as an enrichment-only extension metadata source for both extension_risk and browser_inventory.

No module-level signals or severities should be defined on top of this provider alone; all risk decisions must be made by higher-level logic that combines AMO enrichment with installation state and threat intelligence.

```json
{
  "provider": "firefox_addons_site_api",
  "provider_category": "cloud",
  "provider_role": "enrichment_only",
  "module_mappings": [
    {
      "module": "extension_risk",
      "provider_role": "enrichment_only",
      "provider_method": "get_addon_detail",
      "endpoint_or_artifact": "GET /api/v5/addons/addon/(id|slug|guid)/",
      "classification": "enrichment_only",
      "entity_types": ["extension"],
      "gating_logic": "Require a Firefox extension identifier (guid, AMO id, or slug) from inventory or correlation; treat 404/401/403 for non-public add-ons as no-hit.",
      "citation_refs": [
        "https://dokk.org/documentation/mozilla-addons-server/2024.05.30/_sources/topics/api/addons.rst.txt"
      ],
      "notes": "Primary enrichment source: metadata, popularity, ratings, promotion, flags such as is_experimental and has_privacy_policy."
    },
    {
      "module": "extension_risk",
      "provider_role": "enrichment_only",
      "provider_method": "get_version_detail",
      "endpoint_or_artifact": "GET /api/v5/addons/addon/(addon_id|addon_slug|addon_guid)/versions/(id|version_number)/",
      "classification": "enrichment_only",
      "entity_types": ["extension_version"],
      "gating_logic": "Only call for current_version.id from Add-on Detail and only when type=extension.",
      "citation_refs": [
        "https://dokk.org/documentation/mozilla-addons-server/2024.05.30/_sources/topics/api/addons.rst.txt"
      ],
      "notes": "Provides permission arrays, host permissions, and data-collection permission flags for capability-based risk heuristics."
    },
    {
      "module": "extension_risk",
      "provider_role": "enrichment_only",
      "provider_method": "search_addon",
      "endpoint_or_artifact": "GET /api/v5/addons/search/",
      "classification": "utility_only",
      "entity_types": ["extension"],
      "gating_logic": "Use only to resolve ambiguous names/guids; canonical enrichment should use Add-on Detail.",
      "citation_refs": [
        "https://addons-server.readthedocs.io/en/stable/topics/api/addons.html"
      ],
      "notes": "Search convenience; truncated schema compared to Add-on Detail."
    },
    {
      "module": "extension_risk",
      "provider_role": "enrichment_only",
      "provider_method": "autocomplete_addon",
      "endpoint_or_artifact": "GET /api/v5/addons/autocomplete/",
      "classification": "utility_only",
      "entity_types": ["extension"],
      "gating_logic": "Optional autocomplete-style lookup; do not rely on it for backend correlation.",
      "citation_refs": [
        "https://dokk.org/documentation/mozilla-addons-server/2024.05.30/_sources/topics/api/addons.rst.txt"
      ],
      "notes": "Very limited field set (id, icon_url, icons, name, promoted, type, url)."
    },
    {
      "module": "extension_risk",
      "provider_role": "enrichment_only",
      "provider_method": "browser_mappings",
      "endpoint_or_artifact": "GET /api/v5/addons/browser-mappings/",
      "classification": "utility_only",
      "entity_types": ["extension_id_mapping"],
      "gating_logic": "Use only when mapping non-Firefox extension ids (currently Chrome) into Firefox GUIDs.",
      "citation_refs": [
        "https://dokk.org/documentation/mozilla-addons-server/2024.05.30/_sources/topics/api/addons.rst.txt"
      ],
      "notes": "Correlation helper; returns {extension_id, addon_guid} rows."
    },
    {
      "module": "browser_inventory",
      "provider_role": "enrichment_only",
      "provider_method": "get_addon_detail",
      "endpoint_or_artifact": "GET /api/v5/addons/addon/(id|slug|guid)/",
      "classification": "enrichment_only",
      "entity_types": ["extension"],
      "gating_logic": "Only called for extensions already discovered by a Firefox inventory source.",
      "citation_refs": [
        "https://dokk.org/documentation/mozilla-addons-server/2024.05.30/_sources/topics/api/addons.rst.txt"
      ],
      "notes": "Adds canonical naming, categories, icons, and URLs to inventory records."
    },
    {
      "module": "browser_inventory",
      "provider_role": "enrichment_only",
      "provider_method": "get_version_detail",
      "endpoint_or_artifact": "GET /api/v5/addons/addon/(addon_id|addon_slug|addon_guid)/versions/(id|version_number)/",
      "classification": "enrichment_only",
      "entity_types": ["extension_version"],
      "gating_logic": "Optional if installed version is known and differs from current_version.",
      "citation_refs": [
        "https://dokk.org/documentation/mozilla-addons-server/2024.05.30/_sources/topics/api/addons.rst.txt"
      ],
      "notes": "Allows inventory to store installed version metadata and size."
    }
  ],
  "signal_contracts": [],
  "confidence_guidance": [
    {
      "module": "extension_risk",
      "signal_type_or_use_case": "AMO metadata enrichment for installed Firefox extensions",
      "source_reliability": "High for identifiers and structural metadata; moderate for developer-authored descriptions and external URLs.",
      "freshness_considerations": "Usage metrics and ratings update over time; version and permission data may lag if clients are not on the latest version.",
      "corroboration_rules": "Always confirm installation and version with local inventory; combine AMO data with blocklists and threat intel before emitting risk signals.",
      "calibration_todo": "Empirically evaluate how AMO-derived features distinguish known-good vs known-bad extensions and tune scoring thresholds."
    },
    {
      "module": "browser_inventory",
      "signal_type_or_use_case": "AMO metadata enrichment for Firefox extension inventory records",
      "source_reliability": "Same as above; authoritative for store state but not for local installation.",
      "freshness_considerations": "Installed versions may lag AMO current_version; version detail calls should prefer explicit installed version when available.",
      "corroboration_rules": "Cross-check permissions and version numbers against local manifests where possible.",
      "calibration_todo": "Measure divergence between AMO current_version and real-world installed versions to refine enrichment strategy."
    }
  ]
}
```
