---
title: "output / social / emailformat"
aliases: ["emailformat output", "emailformat signal registry"]
tags: [zima, research, outputs, signal-registry, social, emailformat]
type: provider_research_output
provider: emailformat
provider_category: social
status: complete
prompt_note: prompt.md
provider_folder: emailformat.md
obsidianUIMode: preview
kind: reference
llm_include: true
code_scope: backend
---

# emailformat Provider Integration Research for Zima

## API Surface Appendix
Provider overview
Email Format (email-format.com) is an OSINT-style service that aggregates publicly visible corporate email addresses from the web (search engines and general websites) and infers common email address formats per domain, exposing these formats via a simple API. The service focuses on discovering patterns such as first.last@domain, first_initiallast@domain, etc., not on validating individual inboxes or reporting security events.

Authentication
Mechanism: Private API key in HTTP Authorization header (note: the docs say Authentication in prose but the curl examples use Authorization).

Header: Authorization: api_private_key (value is the account’s private key).

Key lifecycle: API private key is assigned when the account is provisioned; accessible via the “Account” link in the Email Format UI.

Security note from provider: Never share the API key; legitimate Email Format staff will never ask for it.

No additional auth headers or signatures are documented.

Endpoint: GET /api/v2/ping
Purpose

Connectivity and auth sanity check: validates that the API server is reachable and the Authorization header is accepted for the provided key.

Classification: utility_only at Zima (diagnostics only).

Endpoint & method

Method: GET

Path: https://www.email-format.com/api/v2/ping

Supported entity types

No business entity input; purely diagnostic.

Auth / execution requirements

Requires Authorization header with the private API key, despite returning only a static success object.

Request parameters

GET parameters: none (explicitly documented).

Body: none.

Response schema (success)

Documented JSON structure:

json
{"message": "success"}
message (string): always "success" on a successful ping.

Response variants

Successful hit: 200 with {"message":"success"} as shown.

No-hit semantics: not applicable; this is not a lookup endpoint.

Errors: Not explicitly documented, but standard behaviours can be inferred:

Invalid key / missing Authorization: likely 401/403 with some error body (not documented; inferred from common practice, not guaranteed by docs).

Server errors: likely 5xx (not documented; inferred).

Billing / metering

Calls to ping are explicitly not metered and not billed.

Important notes

Use exclusively to validate keys and connectivity from Zima’s provider client.

Endpoint: GET /api/v2/get_formats
Purpose

Returns all known email address formats for a given domain, with relative scores and an example address for each format. This is the primary data source for discovering per-domain patterns.

Classification: enrichment_only for alias correlation (no direct security event).

Endpoint & method

Method: GET

Path: https://www.email-format.com/api/v2/get_formats

Supported entity types

domain (string): Corporate / organizational domain for which to infer email patterns, e.g., citrix.com.

Optional name context to show realistic examples:

first_name (string)

last_name (string)

These are used only to render human-meaningful sample addresses in the response; they do not change the underlying pattern detection logic according to docs.

Auth / execution requirements

Requires Authorization: api_private_key header.

Request parameters (GET query)

Documented fields:

domain (required, string): domain to query.

first_name (optional, string): first name to plug into example addresses. If omitted, "John" is used as part of the default "John Smith" placeholder.

last_name (optional, string): last name to plug into example addresses. If omitted, "Smith" is used.

Example documented parameters

domain=citrix.com

first_name=Jane

last_name=Doe

Response schema (success, documented)

Example from docs:

json
{
  "results": 3,
  "formats": [
    {
      "format": "first_name . last_name ",
      "example": "jane.doe@citrix.com",
      "score": 56
    },
    {
      "format": "last_name ",
      "example": "doe@citrix.com",
      "score": 4
    },
    {
      "format": "first_initial last_name ",
      "example": "jdoe@citrix.com",
      "score": 4
    }
  ]
}
Documented top-level fields:

results (integer): number of formats returned.

formats (array of objects): ordered list of discovered patterns.

formats[] object fields:

format (string): tokenized representation of the email pattern using descriptor placeholders like first_name, last_name, first_initial, combined with separators like . or nothing.

example (string): concrete email address example for the given domain constructed from the (optionally supplied) first_name and last_name.

score (integer): relative score representing confidence / prevalence of the pattern for that domain (higher is better). The exact scoring algorithm and range are not documented.

Presence / optionality

results and formats appear mandatory when there is at least one format (as in example).

For zero-format cases, docs only state that "If there are no formats available you will not be billed" but do not show a response example; likely behaviours include:

results = 0 and formats = [] (most probable, inferred from the presence of these fields in the non-zero case); or

Some other minimal JSON error/empty indicator.
Because no explicit schema for the zero-results case is documented, this must be handled defensively in the client.

Response variants

Successful hit (one or more formats): JSON as shown above with results > 0 and non-empty formats.

Successful no-hit: undocumented; must be treated as unclear. Only guarantee is that it will not be billed.

Partial/limited result: not applicable at the API layer; however, Email Format’s about page indicates that underlying data is based on public email scraping and user voting, so completeness will vary by domain.

Common error cases: not documented; need to infer from HTTP code and best-effort parsing.

Billing / metering

Calls are metered and billed only if at least one format is returned (i.e., results > 0).

Calls with no formats incur no billable usage.

Endpoint: GET /api/v2/get_best_format
Purpose

Returns the single best-known email format for a given domain (instead of all candidates), again with a score and example address. This is a convenience variant for clients that only need the top pattern.

Classification: enrichment_only for alias correlation.

Endpoint & method

Method: GET

Path: https://www.email-format.com/api/v2/get_best_format

Supported entity types

Same as get_formats:

domain (required, string)

first_name (optional, string)

last_name (optional, string)

Auth / execution requirements

Same as get_formats: Authorization: api_private_key.

Request parameters

Identical semantics to get_formats:

domain (required)

first_name (optional)

last_name (optional)

Response schema (success, documented)

Example from docs:

json
{
  "results": 1,
  "format": {
    "format": "first_name . last_name ",
    "example": "jane.doe@citrix.com",
    "score": 56
  }
}
Top-level fields:

results (integer): number of formats returned; expected to be 0 or 1 for this endpoint.

format (object): single best pattern object when results = 1.

format object fields (same shape as elements in formats[] for get_formats):

format (string): tokenized pattern descriptor.

example (string): example email address.

score (integer): top pattern score.

Presence / optionality

For results = 1: both results and format are present as shown.

For zero-format cases: not shown in docs; likely results = 0 and missing or null format, but this is inferred and must be handled cautiously.

Response variants

Successful hit: results = 1 and format object populated.

Successful no-hit: undocumented; behaviour is unclear.

Error cases: not specified; likely standard HTTP errors if domain is missing or auth fails (inferred).

Billing / metering

Same model as get_formats: metered and billed only when at least one format is returned.

Data provenance and OSINT context
The provider states that it "combs through public sources" such as search engines and general websites to identify publicly visible email addresses and aggregates them, including user voting to up/down-rank addresses. This means:

Data is OSINT-based, not verified by direct cooperation with target companies.

Coverage and correctness vary by domain; popular companies tend to have better coverage.

The presence of a format in Email Format is evidence that such pattern has been observed publicly, not that all employees follow it or that personal mailboxes are validated.

These characteristics are important for confidence guidance and alias-correlation usage.

## Module Mapping Table
module	provider_role	provider_method	endpoint_or_artifact	classification	entity_types	gating_logic	citation_refs	notes
alias_correlation	signal_producer (in map) but effectively enrichment	get_formats	GET /api/v2/get_formats	enrichment_only	domain	Only call for organizational domains where alias graph building is needed; skip obvious free-mail providers (gmail.com, outlook.com, yahoo.com) as patterns are user-specific rather than corporate. (inferred)	https://www.email-format.com/i/api_v2/	Provides all observed patterns with scores; primary feed for pattern-based alias expansion. No inherent "event" semantics, just OSINT enrichment.
alias_correlation	signal_producer (in map) but effectively enrichment	get_best_format	GET /api/v2/get_best_format	enrichment_only	domain	Prefer for latency-sensitive paths where only the top pattern is needed; optionally fall back to get_formats if results is 0 or low-confidence. (inferred)	https://www.email-format.com/i/api_v2/	Convenience wrapper returning only the best pattern object. Same billing semantics as get_formats.
alias_correlation	n/a	ping	GET /api/v2/ping	utility_only	none	Use in provider client health checks and onboarding flows to validate stored API key; never used inside correlation logic.	https://www.email-format.com/i/api_v2/	Not metered or billed. No security/identity semantics.
Why no standalone signals?

Email Format exposes inferred address patterns per domain, not events, compromises, or misconfigurations. These patterns are best used to enrich Zima’s alias graph (e.g., generating candidate corporate email aliases from a known name and domain) rather than to emit independent security findings.

## Signal Contracts, Severity, and Tags
There are no standalone security or risk signals that should be emitted purely from Email Format data for the alias_correlation module. All usage is enrichment/utility around identity alias inference.

Given this, the signal contract table is intentionally left with headers only.

module	source	provider	provider_method	signal_type	category	severity	severity_is_conditional	conditional_rule	entity_type	finding_kind	trigger_condition	evidence_fields	enrichment_fields	summary_template	evidence_status	citation_refs	notes
Rationale:

No direct evidence of breaches, credentials, PII, malware, or active infrastructure is provided by this API; it is purely pattern OSINT.

Severity calibration guide indicates that such data is informational context at best (info), not a standalone risk.

Emitting a separate signal for "email pattern discoverable" would be noisy and of marginal actionability; the same information is better consumed internally by alias-correlation logic.

## Confidence Guidance
Because no standalone signals are defined, there are no per-signal severity rules. Instead, treat Email Format’s data as contextual enrichment used at query/correlation time.

If Zima later decides to create a generic OSINT exposure signal such as corporate_email_pattern_publicly_discoverable, the following guide would apply (not implemented in this pass, and marked as future design):

Candidate severity: low or info because it merely confirms that the corporate email pattern is visible in public data, which is common for many organizations; it does not by itself indicate compromise or active abuse.

Conditional logic: higher interest if combined with other social-engineering OSINT indicators (e.g., presence in breach corpuses, exposed internal email aliases), but that cross-provider aggregation belongs in a higher-level correlation module, not in the Email Format mapper.

Current decision: no severity-bearing signals from this provider in the alias_correlation module.

## Implementation Notes
Source reliability
Email Format’s about page explicitly states that it collects "publicly available information" from search engines and general web sites.

It aggregates observed email addresses and infers formats; thus data quality depends on how representative the sampled addresses are and how accurate the pattern-mining algorithm is.

The score field per format indicates relative prevalence or confidence, but its scale and cutoff semantics are undocumented.

Freshness / staleness
Data is refreshed as the crawler and aggregators update their view of public web content; there is no per-domain timestamp in the API responses to indicate last-seen recency.

For large, stable organizations, email formats change infrequently, so staleness is usually not critical; for rebranding/merger scenarios, patterns may lag reality.

Corroboration opportunities
Within Zima, confidence can be improved by:

Cross-checking Email Format’s inferred pattern against:

Email aliases already seen in other providers (breach corpuses, CRM exports, internal identity providers), when available.

Other OSINT pattern tools if integrated in the future (e.g., Hunter-like sources).

Verifying that generated aliases created from a known name and Email Format’s pattern match addresses already seen in correlated datasets; this is particularly useful when the same person appears under variations of the pattern (e.g., j.doe@ vs john.doe@).

Calibration TODOs
Empirically evaluate how often the top get_best_format pattern actually matches verified employee addresses for a sample of known domains.

Develop a heuristic mapping from Email Format score into Zima’s internal confidence scale for enrichment edges (e.g., alias edge strength in graph), not for standalone signals.

Decide minimum score threshold (and/or minimum results value) below which patterns are ignored to avoid overfitting on noisy or sparsely observed domains.

## Provider Summary and Structured JSON
Since no standalone signals are defined for this provider in the alias_correlation module, no Zima signal tags are currently applied.

If a future OSINT-exposure signal were created, likely tags would include:

breach / pii_exposure: not appropriate here, as no breach/PII is directly surfaced.

phishing, threat_actor, etc.: may be indirectly relevant (email patterns help attackers craft plausible phishing), but Email Format alone does not indicate active abuse.

A non-listed tag category such as osint or identity_osint would be more accurate, but that lies outside the provided tag vocabulary.

For now, no tags are attached to alias-correlation enrichments derived from Email Format.

## Note on Tags and Signals
Mapper vs provider client
Provider client responsibilities:

Implement low-level HTTP GET to /api/v2/ping, /api/v2/get_formats, and /api/v2/get_best_format with Authorization header injection.

Handle standard network errors, HTTP error codes, and JSON decoding.

Expose a clean Python (or other language) client surface for Zima modules:

ping() → returns boolean or raw {message: "success"}.

get_formats(domain, first_name=None, last_name=None) → normalized object list.

get_best_format(domain, first_name=None, last_name=None) → single normalized object or None.

Manage retry/backoff around transient 5xx responses (behaviour not documented but expected).

Module mapper responsibilities (alias_correlation):

Decide when to call get_best_format vs get_formats.

Interpret format strings and translate them into internal pattern tokens used by the alias engine (e.g., first_name.last_name, first_initiallast_name).

Map Email Format’s score into internal edge weights or confidence hints for alias relationships, not into Zima signal confidence.

Ensure no standalone Zima signals are emitted; instead, emit or update internal alias-correlation records.

Field paths that must survive parsing
From get_formats / get_best_format responses:

Top-level:

results

formats (array) or format (object)

Pattern object:

format

example

score

All of these should be preserved in the raw evidence blob associated with any alias-correlation enrichment, for audit and debugging.

Null / empty / no-hit behaviour
results = 0 or missing/empty formats / format should be treated as "no pattern available"; Zima should not create aliases or enrichment edges for that domain.

Because zero-result schema is undocumented, the client must handle:

results present but 0, formats empty array.

results present but missing formats or format.

HTTP 2xx responses with malformed JSON (defensive parsing and logging).

Rate limits, billing, licensing
API docs explicitly mention metering and billing tied to whether any formats are returned but do not provide numeric rate limits or quota values.

The pricing page hints at bulk web or API access behind a membership model but provides no concrete plan tiers or per-request pricing breakdowns in publicly scraped content.

Implementation guidance:

Treat Email Format as a paid OSINT source and assume a per-successful-hit billing model.

Implement client-side rate limiting and batching (e.g., queue domain lookups and cache results aggressively) to control costs.

Cache discovered patterns per domain with long TTL (days to weeks), invalidated only when business logic deems it necessary.

Deduplication / natural identifiers
Natural key for caching and dedup within Zima:

domain + normalized format string.

Within a domain, patterns can be sorted by score descending; duplicates across multiple calls should be merged.

When emitting alias-correlation enrichment, dedupe on (domain, format_tokenization) to avoid repeatedly re-attaching the same pattern with slightly different example values.

Raw evidence to store
For each alias-correlation enrichment using Email Format:

Domain queried.

Full raw response for the domain (either from get_best_format or get_formats).

Timestamp of lookup.

Any internal normalization (e.g., parsed tokens, error handling notes).

This supports:

Future replays when Email Format scoring or output changes.

Auditability if alias graph behaviour needs to be explained.

Out-of-scope uses
Do not use Email Format for:

Email deliverability checks, mailbox validation, or bounce prediction (no such data exposed).

Breach detection, credential exposure, or stealer log detection.

Reputation scoring, spam detection, or malware infrastructure detection.

These are explicitly outside the documented API surface.

## Appendix: Confidence Guidance Table
This section maps directly to Zima’s confidence guidance requirements.

module	signal_type_or_use_case	source_reliability	freshness_considerations	corroboration_rules	calibration_todo
alias_correlation	Use Email Format patterns to expand alias graph for corporate domains	OSINT-based; patterns inferred from publicly visible addresses and may be incomplete or biased toward highly visible staff. Treat score as relative prevalence, not ground truth.
No per-domain timestamps. Email formats are stable for many orgs but can lag in rebrand/merger scenarios; cache with long TTL but allow manual/periodic re-checks for high-value domains.
When generating aliases from a pattern, prefer edges where generated addresses are also observed in other datasets (internal auth logs, breach corpuses, contact lists). Down-weight or ignore patterns that never match known addresses for that domain.	Empirically measure top-pattern accuracy using a labeled set of domains; define score thresholds for using a pattern at all; map Email Format score plus cross-dataset corroboration into Zima’s internal alias edge confidence scale, without creating standalone signals.
## Appendix: Provider Summary
Strongest signal types / contributions

High-value contribution is corporate email pattern detection per domain (e.g., first.last@domain, first_initiallast@domain) via get_formats and get_best_format.

This is especially useful for the alias_correlation module to:

Generate plausible aliases for known people at a company.

Normalize and correlate multiple observed addresses that share a pattern.

What the provider should not be used for

Do not use Email Format for any of the following, as the API does not expose relevant fields:

Breach or credential exposure detection.

PII leakage detection.

Malware, C2, spam, or phishing infrastructure detection.

Email deliverability or validation.

Reputation scoring or spam classification.

API/auth/rate-limit/licensing cautions

Auth uses a single private API key via Authorization header; keep it tightly scoped and rotated per environment.

Calls to get_formats/get_best_format are billed only when formats are returned; this encourages caching and minimizing redundant lookups.

Public docs do not specify formal rate limits or quotas; treat the service as a paid OSINT API and implement conservative rate limiting and aggressive domain-level caching.

Overall treatment in current Zima stage

Despite being labelled as a signal_producer in the provider map, Email Format should operationally be treated as enrichment-only / utility in the alias_correlation module:

It produces no direct security signals by itself.

Its outputs enrich identity graphs and alias relationships.

Any future security findings based on this data will likely be composite OSINT signals from higher-level correlation logic, not direct emissions from this provider.

{
  "provider": "emailformat",
  "provider_category": "social",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "alias_correlation",
      "provider_role": "signal_producer_enrichment",
      "provider_method": "get_formats",
      "endpoint_or_artifact": "GET https://www.email-format.com/api/v2/get_formats",
      "classification": "enrichment_only",
      "entity_types": ["domain"],
      "gating_logic": "Only call for organizational/business domains where alias graph building is needed; skip obvious freemail providers (e.g., gmail.com, outlook.com, yahoo.com) because patterns are user-specific rather than corporate. (inferred)",
      "citation_refs": [
        "https://www.email-format.com/i/api_v2/"
      ],
      "notes": "Primary feed for all observed email address patterns per domain (format, example, score). Used to enrich alias-correlation logic, not to emit standalone security signals."
    },
    {
      "module": "alias_correlation",
      "provider_role": "signal_producer_enrichment",
      "provider_method": "get_best_format",
      "endpoint_or_artifact": "GET https://www.email-format.com/api/v2/get_best_format",
      "classification": "enrichment_only",
      "entity_types": ["domain"],
      "gating_logic": "Use when only the top pattern is needed (latency- or cost-sensitive paths). Optionally fall back to get_formats if results == 0 or patterns appear low-confidence. (inferred)",
      "citation_refs": [
        "https://www.email-format.com/i/api_v2/"
      ],
      "notes": "Convenience endpoint returning a single best pattern object, with same schema fields (format, example, score) as entries in get_formats."
    },
    {
      "module": "alias_correlation",
      "provider_role": "signal_producer_utility",
      "provider_method": "ping",
      "endpoint_or_artifact": "GET https://www.email-format.com/api/v2/ping",
      "classification": "utility_only",
      "entity_types": [],
      "gating_logic": "Use only for provider client health checks and onboarding key validation; never called from alias-correlation signal logic.",
      "citation_refs": [
        "https://www.email-format.com/i/api_v2/"
      ],
      "notes": "Connectivity/auth sanity check; returns a static success message and is explicitly not metered or billed."
    }
  ],
  "signal_contracts": [],
  "confidence_guidance": [
    {
      "module": "alias_correlation",
      "signal_type_or_use_case": "emailformat_alias_enrichment",
      "source_reliability": "OSINT-based; patterns are inferred from publicly visible email addresses on the web and may be incomplete or biased toward highly visible employees. Treat the score field as a relative prevalence/confidence indicator rather than ground truth.",
      "freshness_considerations": "API responses do not include per-domain timestamps. Corporate email formats are relatively stable but may lag during rebrands or mergers. Cache patterns with long TTL and periodically re-check for high-value domains.",
      "corroboration_rules": "When generating aliases from a domain pattern, prefer or up-weight patterns that also match addresses observed in other datasets (internal auth logs, breach corpuses, contact lists). Down-weight or ignore patterns that never match any known addresses for the same domain.",
      "calibration_todo": "Empirically evaluate the accuracy of the top get_best_format pattern against verified employee addresses for a labeled domain set; define a minimum score threshold for using a pattern; map the provider score plus cross-dataset corroboration into Zima’s internal alias edge confidence scale without turning these enrichments into standalone signals."
    }
  ]
}
