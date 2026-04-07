---
title: "output / social / gravatar"
aliases: ["gravatar output", "gravatar signal registry"]
tags: [zima, research, outputs, signal-registry, social, gravatar, graph_exclude]
type: provider_research_output
provider: gravatar
provider_category: social
status: complete
prompt_note: prompt.md
provider_folder: gravatar.md
obsidianUIMode: preview
---

Gravatar provides avatar images and user profile metadata keyed by a hashed email address, primarily for user experience and identity portability across sites rather than for security or threat intelligence use cases. Its APIs expose whether an email hash corresponds to a public profile and, if so, return display name, avatar URL, basic biographical information, and verified social links the user has chosen to publish. For Zima, Gravatar should be integrated as an enrichment-only source for the username_exposure module, not as a standalone signal producer, because presence of a Gravatar profile is an intentional, benign disclosure rather than a breach or high‑risk exposure.

## API Surface Appendix

1. Identifier (Hash) Creation
Endpoint / Doc: Creating identifier (hash) documentation.

Purpose
Define the canonical way to derive the Gravatar identifier from an email address, used for both avatar and profile lookups.

Supported entity_type(s)

email (input) → SHA256 hash string (identifier).

Auth / execution requirements

No network call; this is a client‑side hashing procedure described by Gravatar.

Steps:

Trim leading and trailing whitespace from the email.

Lower‑case the email.

Hash with SHA256 to produce the identifier.

Key points

All URLs on Gravatar are based on the hashed value of an email address; the hash is considered the primary way of identifying an identity in the system.

Once the hash is generated, it can be used to request either an avatar image or a profile.

Response / behavior

Not an API endpoint; there is no response object. Output is a hex SHA256 string.

Notes for Zima

Implement hash generation once in the Gravatar client and share it across avatar/profile lookups.

This logic must be deterministic and Unicode‑safe; follow Gravatar's trim+lowercase+SHA256 rules exactly to ensure consistent matching with Gravatar's back end.

Evidence status: Documented (hashing rules are explicitly defined in Gravatar docs).

2. Profiles API: GET https://api.gravatar.com/v3/profiles/{profileIdentifier}
Purpose
Retrieve a user profile by SHA256 hash of the email address or by Gravatar profile URL slug.

Endpoint and method

Base URL: https://api.gravatar.com/v3.

Path: /profiles/{profileIdentifier}.

Method: GET.

Supported entity_type(s)

email (converted to SHA256 hash identifier).

username or profile_slug (via profile URL slug such as gravatar.com/{USERNAME}).

Auth / execution requirements

Header Authorization: Bearer <API_KEY> is supported and recommended for authenticated requests, giving higher rate limits and access to additional profile fields.

Some profile fields (links, registration and last edit timestamps, contact info, payment and wallet info, gallery images, languages, timezone, etc.) are only available to authenticated requests.

Rate limits

Profiles API is free to use.

Default limits:

Unauthenticated: 100 requests per hour.

Authenticated: 1000 requests per hour.

Error 429 Too Many Requests returned when limits are exceeded.

Avatar image API requests do not count towards these limits; rate limits apply only to Profiles endpoint.

Top‑level response (Profile schema)
Responses contain a JSON object representing a Profile with the following documented properties; Gravatar's schema marks many as "required", but some are only present if the user has set them or if the request is authenticated.

Required (per schema, may be empty in practice):

hash (string): SHA256 hash of user's primary email.

display_name (string): Display name shown on profile.

profile_url (string): Full URL to the user's Gravatar profile.

avatar_url (string): URL to the user's avatar image, if set.

avatar_alt_text (string): Alt text describing the avatar image.

location (string): User location.

description (string): About/biography section.

job_title (string): User's job title.

company (string): User's company name.

verified_accounts (array of VerifiedAccount): Verified external accounts added to profile; unauthenticated requests are limited to 4 entries.

pronunciation (string): Phonetic pronunciation of user's name.

pronouns (string): Pronouns used by the user.

Optional / authenticated‑only fields (subset):

timezone (string, optional, authenticated only): User's timezone (for example Europe/Bratislava).

languages (array of Language, optional, authenticated only): List of languages known to the user, each with code, name, is_primary, order.

first_name (string, optional, authenticated only).

last_name (string, optional, authenticated only).

is_organization (boolean, optional, authenticated only).

header_image (string, optional): URL/CSS specifying profile header image.

hide_default_header_image (boolean, optional).

background_color (string, optional): Profile background color.

links (array of Link, optional, authenticated only) with label and url.

interests (array of Interest, optional, authenticated only) with id and name.

payments (object, optional, authenticated only): Public payment information.

contact_info (object, optional, authenticated only, only if user has chosen to make it public).

gallery (array of GalleryImage, optional, authenticated only): Additional images user uploaded.

number_verified_accounts (integer, optional, authenticated only): Count of verified accounts, including hidden ones.

last_profile_edit (string or null, optional, authenticated only): UTC timestamp of last profile edit.

registration_date (string or null, optional, authenticated only): Account registration date.

Nested object schemas:

VerifiedAccount:

service_type (string): Service type (e.g., tumblr).

service_label (string): Human‑readable service label (e.g., Tumblr).

service_icon (string): URL to service icon.

url (string): URL to user's account on the service.

is_hidden (boolean): Whether the verified account is hidden from public profile.

GalleryImage:

url (string): URL to gallery image.

alt_text (string, optional): Alt text.

Interest:

id (integer): Unique ID of interest.

name (string): Interest name.

Language:

code (string): Language code (e.g., en).

name (string): Language name (e.g., English).

is_primary (boolean): Whether this is the primary language.

order (integer): Ordering index.

Link:

label (string): Label for the link.

url (string): URL value.

CryptoWalletAddress (authenticated docs, even if not in Profile root): label and address for a cryptocurrency wallet.

Presence / optionality

Gravatar distinguishes between required vs optional fields in the OpenAPI schema, but actual runtime responses may omit data if the user has not configured it or if the request is unauthenticated (for example, timezone, languages, contact_info).

Docs explicitly state that some profile attributes, such as languages, timezone, links, interests, payments, contact_info, gallery, number_verified_accounts, last_profile_edit, and registration_date, are only returned for authenticated API calls.

Response variants

Success with profile (hit): HTTP 200, body is a complete Profile JSON object.

No profile (no‑hit): HTTP 404, "No profile found for the given identifier."

Rate limited: HTTP 429, "API rate limit exceeded."

Server error: HTTP 500, internal server error.

Notes specific to primary email semantics

Profile requests will only resolve for the hash of the primary address on an account; users may have multiple email addresses, so an avatar image request may return a result, but a profile request for the same hash may not if that email is not primary.

Evidence status: Documented (endpoint, parameters, status codes, and field schemas are explicitly defined in official REST API docs and SDK profiles guide).

3. Legacy JSON Profile via https://gravatar.com/{hash}.json
Purpose
Provide a JSON document containing open profile data keyed by email hash, originally following Portable Contacts structure, and still documented as a simple way to access profile information.

Endpoint and method

Base pattern: https://gravatar.com/{hash}.json where {hash} is the email hash.

Method: GET.

Supported entity_type(s)

email (input), historically hashed with MD5; more recent docs emphasize SHA256 identifiers in REST API.

Auth / execution requirements

No authentication is documented for the .json pattern; the page is described as directly requestable via browser.

Supports optional callback query parameter for JSONP, wrapping the JSON in a JavaScript function call.

Top‑level response

Docs state that requesting the .json URL returns "a JSON document containing all open profile data."

Example JavaScript shows that the response is an object with at least entry[0].displayName accessible, implying a Portable Contacts‑like structure with an entry array of profile objects.

Exact field names and types are not fully detailed in current JSON docs, and Portable Contacts spec is referenced for further details.

Response variants

Successful profile hit: 200 with JSON body (shape as above). Actual field‑level schema is only inferred from examples and historical PoCo docs, not fully restated in current docs.

No‑hit behavior: Not clearly specified in current JSON doc page; it likely returns HTTP 404 or a JSON error but this is not explicitly documented.

JSONP variant: If callback=<fn> is supplied, response is fn(<json>) and executed when loaded as a <script>.

Evidence status: Partially documented, partially inferred (endpoint and usage documented; detailed field structure referenced to Portable Contacts but not included in current docs).

4. Avatar Image URLs: https://www.gravatar.com/avatar/{hash}
Purpose
Serve avatar images keyed by hashed email, with options for size, default image, and content rating.

Endpoint pattern

Base: http://www.gravatar.com/avatar/{md5_hash} or https://www.gravatar.com/avatar/{md5_hash}.

Optional .jpg extension allowed.

Supported entity_type(s)

email (input) → MD5 hash (identifier in this legacy image service).

Query parameters

s or size: Size between 1 and 512 pixels; default 80px.

r or rating: Content rating filter g, pg, r, x; default g.

d or default: Default image URL or special dynamic defaults (identicon, monsterid, wavatar, etc.); 404 can be used to cause HTTP 404 when no image found instead of returning a default image.

Auth / rate limits

No auth; avatars API requests do not count towards Profiles API rate limits.

Response / variants

On hit: Image payload (e.g., JPEG/PNG) with 200.

On no hit with d=404: HTTP 404.

Otherwise: Default or fallback image.

Evidence status: Documented in historical implementation docs and referenced in multiple official and third‑party implementation guides.

5. oEmbed API: GET https://api.gravatar.com/v3/oembed?url=...
Purpose
Provide an oEmbed description that allows embedding a Gravatar profile card via <iframe> on external sites.

Endpoint and method

URL: https://api.gravatar.com/v3/oembed.

Method: GET.

Parameters

url (required): Full profile URL to embed; examples include https://gravatar.com/{USERNAME}, or localized forms like https://es.gravatar.com/{USERNAME}.

Top‑level response

JSON object with fields typical for oEmbed:

version, type ("rich"), title, width, height, maxwidth, maxheight, html (iframe embed code), provider_name, provider_url, cache_age.

Response variants

On valid profile URL: 200 with oEmbed JSON.

On invalid or unknown URL: not explicitly documented; likely 404 or an oEmbed error, but unspecified.

Evidence status: Documented (endpoint, required parameter, and example response provided in Profiles SDK and REST docs).

## Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|
| username_exposure | signal_producer | lookup(email) | GET /v3/profiles/{profileIdentifier} (Profiles API) | enrichment_only | email | Require normalized email; compute SHA256 per Gravatar rules; call /profiles/{hash}; on 200 attach enrichment; on 404 treat as clean no-hit; never emit standalone signals from this provider. | web:1, web:7, web:15 | Presence of a Gravatar profile is an intentional public profile, not a breach or compromise; use as OSINT-style enrichment (name, location, verified accounts), not as a finding. |
| username_exposure | signal_producer | lookup(email) | https://gravatar.com/{hash}.json | enrichment_only (optional / fallback) | email | Only if Zima decides not to manage API keys; on 200 parse best-effort PoCo-like JSON; on errors or unknown shape, drop silently; still no signals, enrichment only. | web:2 | Prefer v3 Profiles API; .json is legacy and only partially specified; increases parsing fragility and makes future changes harder to track. |
| username_exposure | signal_producer | avatar(email) | https://www.gravatar.com/avatar/{md5_hash} | utility_only | email | Optional: only used to fetch/profile thumbnails for UI or analyst context; do not use hit/no-hit as a security signal; respect d/s/r parameters and d=404 behavior. | web:3, web:6, web:9 | Avatars are cosmetic, public by design, and not a risk driver; keep entirely out of scoring and detection logic. |
| username_exposure | signal_producer | embed_profile | GET /v3/oembed?url=... | out_of_scope | email, username | Only if some separate UI layer wants embedded cards; backend exposure detection should not depend on iframe HTML or oEmbed output. | web:1, web:5 | Ignore for core Zima backend; this is pure presentation tooling. |

## Signal Contracts, Severity, and Tags

Gravatar should not produce any standalone Zima signals for username_exposure at this stage. Everything is enrichment or utility.

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Design rationale:

No breach semantics: Gravatar's entire purpose is voluntary, user-configured profiles and avatars. Existence of a profile is not misconfiguration or leak, and does not meet any of your "critical/high/medium" definitions.

Pure OSINT: Fields like display_name, location, job_title, company, verified_accounts are essentially OSINT and only become actionable when correlated with real security events (breaches, stealer logs, phishing infra) from other providers.

Calibration fit: As a standalone fact, "this email has a Gravatar profile" is at best informational, with negligible risk. This matches your info bucket (pure context) rather than a dedicated finding.

If you later decide to introduce a very-low-value informational signal (e.g. gravatar_profile_found), you can derive it from the same mapper, but current recommendation is not to emit it to keep noise low.

## Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|
| username_exposure | gravatar_profile_enrichment | Infrastructure is mature and run by Automattic; data is stable, but all profile fields are self-reported and not externally verified. | Auth responses expose last_profile_edit and registration_date; otherwise no freshness field, so assume data may be stale and re-query only periodically within rate limits. | Cross-check display name, job title, company, and location with other social/professional sources; use verified_accounts to hint GitHub/Tumblr/etc. handles when other sources agree. | Measure how often Gravatar enrichment appears on identities that also have real high-severity events; check runtime behavior of "required" fields and 404 vs avatar-only cases. |
| username_exposure | avatar/UI_context_usage | Avatars are deterministic from email hash and highly reliable for "same email = same person" assertions in UX, but carry no threat intel value. | Avatars can change at user discretion; no timestamp is provided; treat as non-critical UI-only data, not something needing freshness tracking. | Do not use avatars as evidence in any security decision; only use as UI glyphs attached to already-confirmed entities from other signals. | None beyond standard UX QA; explicitly forbid avatar-only evidence paths in rules.py. |

## Implementation Notes

Provider client (transport + DTO)
Normalize and hash email strictly as Gravatar specifies: trim → lowercase → SHA256.

Implement lookup(email) that:

Produces {profileIdentifier, raw_email}.

Calls GET /v3/profiles/{profileIdentifier} with Bearer token when available.

Converts:

200 → GravatarProfileDTO (all Profile fields mapped 1:1 where present).

404 → explicit "no profile" result (not error).

429 → rate-limit error, with backoff metadata.

5xx → transient error.

Optionally implement a legacy lookup_legacy(email) using https://gravatar.com/{hash}.json if you want a no-key fallback, but keep it separate and lower priority.

Mapper (modules/username_exposure/mapper.py)
For a successful profile DTO:

Do not create a Zima signal.

Instead, map into your enrichment schema for the email entity, e.g.:

Evidence-like core:

gravatar.hash

gravatar.profile_url

gravatar.avatar_url, gravatar.avatar_alt_text

Context:

gravatar.display_name

gravatar.location

gravatar.description

gravatar.job_title, gravatar.company

gravatar.pronunciation, gravatar.pronouns

Linkage:

gravatar.verified_accounts[] (service_type, service_label, url, is_hidden)

Optionally: links[], interests[], languages[], timezone

Freshness:

gravatar.last_profile_edit

gravatar.registration_date

gravatar.number_verified_accounts

Handle missing/empty values gracefully; treat absent optional fields as "unknown", not as negatives.

Do not let any presence/absence of Gravatar data change severity on other signals; it should only enhance summaries / entity cards.

Rules (modules/username_exposure/rules.py)
Never use Gravatar as a rule trigger.

You may allow it to:

Add human-readable name / avatar / location to an existing username_exposure signal generated from, e.g., breach data or dark-web sources.

Help correlation: e.g., mapping verified_accounts service URLs to known identities in your graph, but these correlations should be scored conservatively.

Rate limits / reliability
Shared rate-limiting component for /profiles:

Separate buckets for authed vs unauthed (100 vs 1000 per hour).

Configurable backoff policy on 429.

Avatars may be fetched more liberally (do not count against profile limit), but keep this on a separate path that never touches detection.

Deduplication
Primary dedup key: Profile.hash (the SHA256 of primary email) returned by API, not just your locally computed hash.

Secondary: Profile.profile_url, which is stable even if primary email changes.

For legacy .json, fall back to {hash} in URL and any profile identifier present in PoCo if you choose to parse it.

## Provider Summary and Structured JSON

Strongest signal types (conceptually)

Strongest value is deterministic, identity-keyed enrichment: given an email you know whether there is a Gravatar identity and, if so, get stable profile fields and verified accounts that anchor OSINT linking.

What Gravatar should not be used for

Not for breach/credential/malware/dark-web/threat-intel signals; none of that is present in the API.

Not for security validation of account existence on third-party services—only for "has Gravatar profile" and linked accounts as declared by the user.

API/auth/rate-limit/licensing cautions

Respect Profiles API limits and handle 429s; use Bearer auth where possible for richer data.

Remember that avatars API is separate and not rate-limited by Profiles caps, but still subject to general responsible-use guidelines.

Follow hash-generation rules exactly and store keys centrally.

Role in Zima's current stage

Treat Gravatar as:

enrichment-only for username_exposure (Profiles API + optional legacy JSON).

utility-only for avatars (for UI and analyst context).

out-of-scope for oEmbed.

No standalone Gravatar-derived signals should be emitted; all value is at the enrichment and correlation layers.

```json
{
  "provider": "gravatar",
  "provider_category": "social",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "username_exposure",
      "provider_role": "signal_producer",
      "provider_method": "lookup(email)",
      "endpoint_or_artifact": "GET https://api.gravatar.com/v3/profiles/{profileIdentifier}",
      "classification": "enrichment_only",
      "entity_types": ["email"],
      "gating_logic": "Normalize and SHA256-hash email per Gravatar docs; call /profiles/{hash}; on 200 attach profile enrichment; on 404 treat as clean no-hit; never emit standalone signals.",
      "citation_refs": ["web:1", "web:7", "web:15"],
      "notes": "Presence of a Gravatar profile is intentional and benign; use as OSINT-style identity enrichment only."
    },
    {
      "module": "username_exposure",
      "provider_role": "signal_producer",
      "provider_method": "lookup(email)",
      "endpoint_or_artifact": "https://gravatar.com/{hash}.json",
      "classification": "enrichment_only",
      "entity_types": ["email"],
      "gating_logic": "Optional legacy fallback when API keys are unavailable; on 200 parse best-effort Portable Contacts-like JSON; no signals, enrichment only.",
      "citation_refs": ["web:2"],
      "notes": "Schema is only partially documented; prefer v3 Profiles API."
    },
    {
      "module": "username_exposure",
      "provider_role": "signal_producer",
      "provider_method": "avatar(email)",
      "endpoint_or_artifact": "https://www.gravatar.com/avatar/{md5_hash}",
      "classification": "utility_only",
      "entity_types": ["email"],
      "gating_logic": "Optional for UI thumbnails; do not use hit/no-hit as a signal; respect size/default/rating parameters and d=404 semantics.",
      "citation_refs": ["web:3", "web:6", "web:9"],
      "notes": "Purely cosmetic; must not affect scoring or detection."
    },
    {
      "module": "username_exposure",
      "provider_role": "signal_producer",
      "provider_method": "embed_profile",
      "endpoint_or_artifact": "GET https://api.gravatar.com/v3/oembed?url=...",
      "classification": "out_of_scope",
      "entity_types": ["email", "username"],
      "gating_logic": "Only used by separate UI layer if it wants embedded profile cards; not used in security pipeline.",
      "citation_refs": ["web:1", "web:5"],
      "notes": "Provides iframe HTML for profile card; no incremental security data beyond Profiles API."
    }
  ],
  "signal_contracts": [],
  "confidence_guidance": [
    {
      "module": "username_exposure",
      "signal_type_or_use_case": "gravatar_profile_enrichment",
      "source_reliability": "Profiles and avatars are stable infrastructure run by Automattic; data is self-reported and should be treated as descriptive OSINT rather than verified identity.",
      "freshness_considerations": "Use last_profile_edit and registration_date when available from authenticated API; otherwise assume profile may be stale and re-query sparingly within rate limits.",
      "corroboration_rules": "Cross-check display_name, job_title, company, and location with other identity providers; treat verified_accounts as hints to accounts on external services but not exhaustive.",
      "calibration_todo": "Measure how often Gravatar enrichment appears on identities with high-severity incidents; validate runtime presence/absence of 'required' fields and behavior of 404 vs avatar-only cases."
    },
    {
      "module": "username_exposure",
      "signal_type_or_use_case": "avatar_UI_context_usage",
      "source_reliability": "Avatar URLs are deterministic from hashed email and reliable for UI consistency but not for security decisions.",
      "freshness_considerations": "Avatars can change without notice and carry no timestamp; treat as cosmetic and not part of any detection logic.",
      "corroboration_rules": "Do not use avatars as evidence; only show alongside entities already confirmed via higher-signal sources.",
      "calibration_todo": "Ensure rules engine cannot depend on avatar presence; keep avatar usage confined to presentation layer."
    }
  ]
}
```
