---
title: "output / social / emailcrawlr"
aliases: ["emailcrawlr output", "emailcrawlr signal registry"]
tags: [zima, research, outputs, signal-registry, social, emailcrawlr]
type: provider_research_output
provider: emailcrawlr
provider_category: social
status: complete
prompt_note: prompt.md
provider_folder: emailcrawlr.md
obsidianUIMode: preview
kind: reference
llm_include: true
code_scope: backend
---

# emailcrawlr Provider Integration Research for Zima

## API Surface Appendix

EmailCrawlr is a public-OSINT contact and deliverability API; for Zima’s username_exposure module it should be treated as a signal-producing source for “public email/PII exposure” based on where a monitored email appears on the web plus associated PII and social links, while verification and account endpoints are enrichment/utility only. It does not provide breach/credential-stealer data, so all signals are about open-source exposure and contact surface, not credential compromise.

### Get Email Endpoint
Name/path

Documented as “Get Email”.

Example request: curl "https://emailcrawlr.com/api/v2/[email protected]" -H "x-api-key: <Your API Key>" (email in path).

HTTP Request section states GET https://emailcrawlr.com/api/v2/email with an unnamed required parameter “The email address you want to receive information about.” (parameter name is not visible due to a docs formatting issue – likely query or path parameter, but undocumented).

Purpose

Retrieve rich information about a specific email address, including verification status, name, social profiles, job title, location, phone numbers, and web references where the email appears.

Supported entity_type(s)

email (primary input and key in response).

Auth / execution

API key in header: x-api-key: <Your API Key>.

Top-level response fields (per example) and types

email (string): the email address.

personal (boolean): whether the address is personal vs role-based.

domain (string): domain part of the email.

verified (boolean): whether EmailCrawlr marks the address as verified (exact semantics not further documented).

verify (string): relative path to verification endpoint for this email (e.g. "/v2/email/[email protected]").

linkedin (string or null): LinkedIn profile associated with the email (null in example).

twitter (object or null):

twitter (string): Twitter handle.

confidence (number): confidence in that handle association (e.g. 0.75).

name (object):

confidence (number): confidence in the name.

name (string): full name (e.g. "Professional Learning").

pattern (string): email pattern, e.g. "first.last".

references (array of objects): each reference where the email was observed. Example shows:

url (string): source URL.

timestamp (string, ISO 8601): discovery time.

job_title (object):

confidence (number).

job_title (string), e.g. "Organiser".

location (object):

city (string).

country (string).

numbers (array of strings): phone numbers, e.g. ["+441304244442"].

Presence / optionality

Example includes all above fields, but docs do not state which are guaranteed; social (linkedin, twitter), job_title, location, numbers, and references should be treated as optional/nullable.

Response variants

Successful hit: HTTP 200 with full JSON structure above.

Successful no-hit: not explicitly documented; likely 404 based on generic error table (404 “Not Found – The requested resource could not be found”).

Partial/limited: no explicit variant; optional fields may simply be missing or null.

Common error cases (all endpoints)

400: Bad Request – incorrect parameters.

401: Unauthorized – API key wrong.

403: Forbidden – account cannot query this endpoint.

404: Not Found – requested resource could not be found.

429: Too Many Requests – account limit reached.

500: Internal Server Error.

503: Service Unavailable / maintenance.

Notes

All schema details above are documented or directly lifted from the official example response.

### Find Email Endpoint
Name/path

“Find email”: GET https://emailcrawlr.com/api/v2/email/find.

Example: curl "https://emailcrawlr.com/api/v2/email/find?full_name=Professional%20Learning&domain=eastkent.ac.uk" -H "x-api-key: <Your API Key>".

Purpose

Given a full name and domain, attempt to find or infer the correct email address(es) and return enriched records with confidence.

Supported entity_type(s)

Input: email is inferred from full_name and domain (so primary entity is still email, but query is by person+domain).

Auth

x-api-key header required.

Query parameters

full_name (string, required): full name (first and last) of the person.

domain (string, required): person’s domain.

Response fields

Top-level:

domain (string).

name (string): echo of the full name.

emails (array): list of email objects; shape matches “Get Email” objects (fields: email, personal, domain, verified, verify, linkedin, twitter, name, references, job_title, location, numbers).

probability (number): documented in example as 0.8; exact semantics (top-level vs per-email) are not described but likely model confidence for the inferred address set (inferred from example only).

Presence / optionality

domain, name, emails are shown; probability appears in example but not described in text; treat as optional and inferred.

Response variants

Successful hit: 200 with non-empty emails array and probability field.

Successful no-hit: not explicitly shown; likely emails: [] or 404 based on error table (unclear).

Notes

This endpoint is inherently probabilistic – the presence of probability and per-field confidence scores means results are “educated guesses” rather than direct observations.

### Verify Email Endpoint
Name/path

“Verify email”: HTTP Request shown as GET https://emailcrawlr.com/api/v2/email/verify.

Example curl uses an email in the path (curl "https://emailcrawlr.com/api/v2/[email protected]" -H "x-api-key: <Your API Key>"), but the docs text describes GET .../email/verify with a required parameter “The email address you want to verify.” (parameter name and whether it is path vs query are not explicit – ambiguous).

Purpose

Verify email deliverability via MX checks and related signals (not breach; strictly deliverability/validity).

Supported entity_type(s)

email (input and subject).

Auth

x-api-key header.

Request parameters

One required parameter for the email to verify; name and encoding style are undocumented due to formatting; treat as “unknown / to be discovered by testing”.

Response fields

mx_set (boolean): whether MX records exist for the domain.

mx_records (array of objects):

priority (number/int).

address (string), e.g. "aspmx.l.google.com", "mxb.mailgun.org".

valid_mx (boolean): whether MX configuration is valid.

email_sendable (boolean): whether email is considered sendable by EmailCrawlr.

accepts_all_emails (boolean): catch-all behavior flag.

Presence / optionality

mx_set, mx_records, valid_mx, email_sendable, accepts_all_emails are all present in example; docs do not mark any as optional but treat them as core output when lookup succeeds.

Response variants

Successful hit: 200 with full verification object above.

Non-existent domain/email: likely 404 or email_sendable: false and/or valid_mx: false (semantics not fully documented – partially inferred).

### Get Domain Endpoint
Name/path

“Get Domain”: HTTP Request GET https://emailcrawlr.com/api/v2/domain.

Example curl: curl "https://emailcrawlr.com/api/v2/domain?domain=eastkent.ac.uk" -H "x-api-key: <Your API Key>".

SpiderFoot integration uses https://api.emailcrawlr.com/v2/domain?domain=<domain>; functionally equivalent API but different host (likely legacy/alternate base URL).

Purpose

Retrieve information about a domain, its email pattern, location, and all known associated email addresses (with the same enrichment as “Get Email”).

Supported entity_type(s)

Input: domain.

Output entities: list of email addresses under that domain, plus domain-level metadata.

Auth

x-api-key header.

Query parameters

domain (string, required): domain name to query.

Response fields

domain (string).

email_pattern (string): pattern like "first.last"; helpful for inferring unknown emails.

location (object):

city (string).

country (string).

emails (array of objects): each object uses same shape as Get Email:

email (string).

personal (boolean).

domain (string).

verified (boolean).

verify (string).

linkedin (string or null).

twitter (object with twitter and confidence).

name (object with name, pattern, confidence).

references (array of {url, timestamp}).

job_title (object).

location (object).

numbers (array of phone numbers).

Presence / optionality

domain, email_pattern, emails are core; location and all nested enrichment fields appear optional/nullable per examples and SpiderFoot code (plugin guards with .get() and null checks).

Response variants

Successful hit: 200 with populated emails array.

Successful no-hit: SpiderFoot checks for HTTP 404 in res['code'] and treats that as “No information found for domain”; it then returns None instead of a JSON structure, so 404 is a documented behavior via integration code.

Partial/limited: 200 with emails: [] is not explicitly documented but should be anticipated; plugin also logs “No emails found for domain” if emails is falsy.

### Get Account Endpoint
Name/path

“Get Account”: HTTP Request GET https://emailcrawlr.com/api/v2/account.

Example: curl "https://emailcrawlr.com/api/v2/account" -H "x-api-key: <Your API Key>".

Purpose

Retrieve account usage and rate-limit information.

Supported entity_type(s)

None (account-level utility).

Auth

x-api-key header.

Response fields

successful_calls (integer).

limit (integer): maximum calls allowed in current period.

failed_calls (integer).

remaining (integer): calls remaining.

Response variants

Successful: 200 with these counters.

Error: same error codes as generic table.

### Authentication, Host Variants, and Pricing
Auth model

Simple API key in x-api-key header across all endpoints.

Hosts

Official docs use https://emailcrawlr.com/api/v2/....

Third-party integrations (SpiderFoot) use https://api.emailcrawlr.com/v2/... with identical query parameters and JSON parsing; treat this as an alternate host mapping to same backend.

Limits/pricing (third-party)

OSINT API lists describe EmailCrawlr as “Get key information about company websites. Find all email addresses associated with a domain. Get social accounts associated with an email. Verify email address deliverability” with 200 free requests and paid tiers (e.g. “200 requests FREE, 5000 requests — $40”), but this is not present in official docs and should be treated as approximate.

## Module Mapping Table
module	provider_role	provider_method	endpoint_or_artifact	classification	entity_types	gating_logic	citation_refs	notes
username_exposure	signal_producer	get_email	GET https://emailcrawlr.com/api/v2/email (plus documented path-style variant)	direct_signal_input	email	Only query for emails that belong to monitored users or orgs; treat 200 response with at least one reference as a valid exposure; ignore 404 or missing/empty references as no-hit.	Official EmailCrawlr docs for Get Email and errors.
Primary way to get per-email OSINT (references, social, job, phones, location); requires x-api-key; some parameter details (path vs query) must be validated experimentally.
username_exposure	signal_producer	get_domain	GET https://emailcrawlr.com/api/v2/domain (or https://api.emailcrawlr.com/v2/domain)	direct_signal_input	domain → email	Only query for domains that are in tenant’s org list; create per-email exposures only for emails whose domain matches one of the tenant’s domains; treat HTTP 404 as no-hit; skip if emails is empty.	Official Domain docs plus SpiderFoot integration.
Used for bulk enumeration of exposed corporate emails; plugin code confirms emails array shape and that 404 indicates “no information found for domain”.
username_exposure	enrichment	find_email	GET https://emailcrawlr.com/api/v2/email/find	enrichment_only	email (inferred), domain	Use only when you have name + domain but no exact email; require probability above a configurable threshold and at least one email object; do not emit standalone signals from this endpoint alone, but treat found emails as candidates to pass into get_email for confirmation.	Official Find Email docs.
Endpoint is explicitly probabilistic with a probability score; safer to treat as helper for discovering candidate addresses and patterns, not a direct exposure signal.
username_exposure	enrichment/utility	verify_email	GET https://emailcrawlr.com/api/v2/email/verify	enrichment_only	email	Call only to enrich an existing exposure candidate; if email_sendable is false or valid_mx is false, down-rank or discard exposure as stale; never emit standalone signals from verification output.	Official Verify Email docs.
Pure deliverability check (MX, catch-all); useful for reducing noise and adjusting severity but not itself proof of exposure or compromise.
username_exposure	utility	get_account	GET https://emailcrawlr.com/api/v2/account	utility_only	none	Use in provider client for rate-limit and quota control; never exposed to detection logic or signals.	Official Account docs.
Helps control call volume and avoid 429s; should live in client/integration layer only.
## Signal Contracts, Severity, and Tags
Only EmailCrawlr email/domain endpoints should emit standalone signals; find/verify/account are enrichment or utility only.

module	source	provider	provider_method	signal_type	category	severity	severity_is_conditional	conditional_rule	entity_type	finding_kind	trigger_condition	evidence_fields	enrichment_fields	summary_template	evidence_status	citation_refs	notes
username_exposure	username_exposure	emailcrawlr	get_email (GET /api/v2/email)	email_public_exposure	identity_security	medium	yes	Start at medium when references is non-empty; raise to high if any of numbers, location, or job_title is present (exposed PII), lower to low if only email + domain with no name or social/PII; drop to low/info if subsequent verify shows email_sendable is false or valid_mx is false.	email	true_finding	HTTP 200 from Get Email for a monitored email, with references array containing at least one entry (any url) for that email.	email, personal, domain, verified, references[], name, job_title, location, numbers, twitter, linkedin	verify path, any provider confidence scores (e.g. name.confidence, job_title.confidence, twitter.confidence)	Public references were found for {email}, including name/role and contact details on external sites.	documented (fields), derived (trigger/severity rules)	Email endpoint schema and example response.
 Verify endpoint for deliverability checks.
This is an OSINT-based exposure signal: the email appears on public sites with associated attributes; not a credential breach. Treat presence of PII (phone, granular location, job_title, social handles) as justification for higher severity. Verify output should be used to de-prioritize obviously dead addresses.
username_exposure	username_exposure	emailcrawlr	get_domain (GET /api/v2/domain)	email_public_exposure	identity_security	medium	yes	Start at medium when a monitored-domain email in emails[] has at least one reference; raise to high if that email also has numbers, location, or job_title; drop to low if only the email string is known with no enrichment; reduce severity or suppress if domain-level pattern matches but there are no concrete references for that specific email.	email	true_finding	HTTP 200 from Get Domain for a monitored domain, and within emails[] at least one object whose email belongs to a monitored identity or tenant domain and has non-empty references.	domain, email_pattern, emails[].email, emails[].personal, emails[].domain, emails[].verified, emails[].references[], emails[].name, emails[].job_title, emails[].location, emails[].numbers	emails[].twitter, emails[].linkedin, any per-field confidence scores	Email {email} under domain {domain} is publicly exposed with associated contact information on external websites.	documented (fields), derived (trigger/severity rules)	Domain endpoint schema and example, including nested email objects.
 SpiderFoot plugin behavior for emails and related fields.
Domain lookups can enumerate a large set of corporate addresses. Gating must restrict to tenant domains and, ideally, monitored identities to avoid over-signalling. Use same severity logic as Get Email but applied per-email extracted from the domain result.
Notes on why other endpoints are not in the table:

email/find is excluded from standalone signals because results are probabilistic guesses (driven by probability and pattern inference) rather than direct observations; safest to route through get_email or get_domain before signalling.

email/verify has no exposure context – only deliverability and MX info – so it influences severity and confidence but not signal existence.

account is pure quota/account data.

## Confidence Guidance
module	signal_type_or_use_case	source_reliability	freshness_considerations	corroboration_rules	calibration_todo
username_exposure	email_public_exposure from get_email	Data is scraped/aggregated from public web; each email record includes concrete references URLs plus per-field confidence scores for name, job_title, and social handles, which supports moderate inherent reliability when references are present.
References include a timestamp, but docs do not state update cadence; treat very old timestamps as lower-confidence for current exposure and weigh with verified/verification status.
Require at least one references[].url and, for high-severity PII exposure, at least one PII field (numbers, location, or job_title) populated; optionally re-check the URL for 2xx/4xx status before emitting or at least periodically for stale data.	Empirically compare EmailCrawlr findings against internal email inventory and other OSINT/breach sources to estimate precision/recall; tune minimum reference count and PII field presence thresholds, and check how often verified/email_sendable mismatches reality.
username_exposure	email_public_exposure from get_domain	SpiderFoot’s integration and docs both show consistent domain schema, including emails[] and nested enrichment, indicating stable API behavior; however, coverage may be skewed toward more visible domains.
Domain data can age: email patterns and staff can change; use references[].timestamp and verified e.g. via verify endpoint to adjust trust in older exposures.	Only signal for domains explicitly mapped to tenants; per-email, require non-empty references; optionally verify deliverability via email/verify when raising severity to high, or when numbers/location are present but very old.	Log hit/miss rates per tenant domain and cross-check with other domain-enumeration and OSINT tools; calibrate severity downgrades when all references are older than a configurable threshold (e.g. >2–3 years) or email_sendable is false.
username_exposure	Use of email/find as enrichment	Inference is driven by patterns and probability field, not direct observation; risk of false positives if used alone is significant.
Pattern guesses don’t decay per se, but target orgs may change email formats; treat this as low-confidence input unless corroborated via get_email/get_domain or other sources.	Never emit signals directly from email/find; instead, feed its suggested addresses into get_email and require concrete references and/or further corroboration before signalling.	Gather empirical stats on how often email/find guesses match actual addresses (via internal directory or SMTP verification) and set a minimum probability threshold for even attempting follow-up lookups.
username_exposure	Use of email/verify for severity adjustments	MX/deliverability checks are typically reliable but do not prove inbox existence (catch-all, aliases, etc.); treat as a strong but not perfect indicator of current reachability.
MX configurations can change quickly; stale verifications should be refreshed periodically if used in severity decisions.	When email_sendable is false or valid_mx is false, consider lowering severity or marking exposure as historical; do not treat “sendable” as proof of active user ownership.	Benchmark verify results against real bounce data (where available) to quantify false-positive/-negative rates and tune how much weight to give this in severity/confidence scoring.
## Implementation Notes
1. Strongest signal types
Strongest value for Zima is OSINT-based public exposure of monitored email identities: where a user’s or corporate email address appears on third-party sites, along with name, job title, phone numbers, city/country, and social handles, all linked via explicit references URLs and timestamps.

Domain-level enumeration allows you to build a map of which corporate email identities are publicly advertised where, which is useful for spear-phishing risk and identity surface analysis, especially when combined with PII richness and recency.

2. What the provider should not be used for
It does not provide breach data, stealer logs, passwords, or hashes – nothing in the schema indicates credential theft or underground exposure, so it should not be used for credential_breach_found-style signals.

It is not a threat-intel or malware platform: no indicators of C2, malware samples, phishing kits, or infrastructure classification are present, so it should not be used for threat-intel or malware/C2 categories.

3. API/auth/rate-limit/licensing implementation cautions
Integration is straightforward API-key auth in the x-api-key header, but you should detect and handle HTTP 401, 403, 404, 429, 500, and 503 exactly as documented to avoid noisy failures in the module.

Official docs expose an /api/v2/account endpoint with remaining, limit, and call counters; use this in your provider client to throttle per-tenant call volumes and to adapt to free vs paid quotas rather than implementing hard-coded limits from third-party OSINT lists.

4. Overall role in current Zima stage
For the username_exposure module, EmailCrawlr should be treated as a signal-producing provider whose outputs create true-finding “email_public_exposure” signals when references and PII are present, with email/find and email/verify acting as enrichment/utility inputs for discovery and calibration.

Because its data is purely OSINT/public, its severities should cap at high (for strong PII exposure) and never reach critical under your current calibration scheme, since no credentials or active compromise are evidenced.

## Provider Summary and Structured JSON

```json
{
  "provider": "emailcrawlr",
  "provider_category": "social",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "username_exposure",
      "provider_role": "signal_producer",
      "provider_method": "get_email",
      "endpoint_or_artifact": "GET https://emailcrawlr.com/api/v2/email",
      "classification": "direct_signal_input",
      "entity_types": ["email"],
      "gating_logic": "Only query for monitored emails; require HTTP 200 with non-empty `references` for that email; treat 404 or missing/empty `references` as no-hit.",
      "citation_refs": ["https://emailcrawlr.com/documentation/ [web:16]"],
      "notes": "Primary per-email OSINT enrichment, including references, name, job_title, location, numbers, and social links."
    },
    {
      "module": "username_exposure",
      "provider_role": "signal_producer",
      "provider_method": "get_domain",
      "endpoint_or_artifact": "GET https://emailcrawlr.com/api/v2/domain (or https://api.emailcrawlr.com/v2/domain)",
      "classification": "direct_signal_input",
      "entity_types": ["domain", "email"],
      "gating_logic": "Only query domains mapped to the tenant; for each email in `emails[]`, emit exposures only if the email belongs to a monitored identity or tenant domain and has non-empty `references`.",
      "citation_refs": ["https://emailcrawlr.com/documentation/ [web:16]", "SpiderFoot module sfp_emailcrawlr [web:21]"],
      "notes": "Used for bulk enumeration of exposed corporate emails; yields same email object structure as get_email."
    },
    {
      "module": "username_exposure",
      "provider_role": "signal_producer",
      "provider_method": "find_email",
      "endpoint_or_artifact": "GET https://emailcrawlr.com/api/v2/email/find",
      "classification": "enrichment_only",
      "entity_types": ["email", "domain"],
      "gating_logic": "Use only when you have full_name + domain but no exact email; require sufficient `probability` before passing suggested emails into get_email; never emit standalone signals from this endpoint.",
      "citation_refs": ["https://emailcrawlr.com/documentation/ [web:16]"],
      "notes": "Probabilistic finder; supports pattern-based guesses and returns confidence scores; intended as helper for discovery."
    },
    {
      "module": "username_exposure",
      "provider_role": "signal_producer",
      "provider_method": "verify_email",
      "endpoint_or_artifact": "GET https://emailcrawlr.com/api/v2/email/verify",
      "classification": "enrichment_only",
      "entity_types": ["email"],
      "gating_logic": "Call only for emails already associated with a candidate exposure; use `email_sendable`, `valid_mx`, and `accepts_all_emails` to down-rank or suppress stale exposures, but do not create signals solely from this output.",
      "citation_refs": ["https://emailcrawlr.com/documentation/ [web:16]"],
      "notes": "Deliverability/MX check only; useful for severity and confidence adjustments."
    },
    {
      "module": "username_exposure",
      "provider_role": "signal_producer",
      "provider_method": "get_account",
      "endpoint_or_artifact": "GET https://emailcrawlr.com/api/v2/account",
      "classification": "utility_only",
      "entity_types": [],
      "gating_logic": "Use in provider client to monitor `remaining` against `limit` and backoff before hitting 429; never surfaced to detection rules.",
      "citation_refs": ["https://emailcrawlr.com/documentation/ [web:16]"],
      "notes": "Quota/rate-limit information only."
    }
  ],
  "signal_contracts": [
    {
      "module": "username_exposure",
      "source": "username_exposure",
      "provider": "emailcrawlr",
      "provider_method": "get_email",
      "signal_type": "email_public_exposure",
      "category": "identity_security",
      "severity": "medium",
      "severity_is_conditional": "yes",
      "conditional_rule": "Medium when `references` is non-empty; upgrade to high if any of `numbers`, `location`, or `job_title` is present; downgrade toward low/info if verification shows `email_sendable` is false or `valid_mx` is false and all references are old.",
      "entity_type": "email",
      "finding_kind": "true_finding",
      "trigger_condition": "HTTP 200 from Get Email for a monitored email AND `references` array contains at least one entry for that email.",
      "evidence_fields": [
        "email",
        "personal",
        "domain",
        "verified",
        "references",
        "name",
        "job_title",
        "location",
        "numbers",
        "twitter",
        "linkedin"
      ],
      "enrichment_fields": [
        "verify",
        "name.confidence",
        "job_title.confidence",
        "twitter.confidence"
      ],
      "summary_template": "Public references were found for {email}, including name/role and contact details on external sites.",
      "evidence_status": "documented_fields_derived_logic",
      "citation_refs": [
        "https://emailcrawlr.com/documentation/ (Get Email and Verify Email sections) [web:16]"
      ],
      "notes": "Signal represents OSINT-based exposure of an email identity, not a breach. Use verification output for recency/validity and adjust severity based on richness of PII in the record."
    },
    {
      "module": "username_exposure",
      "source": "username_exposure",
      "provider": "emailcrawlr",
      "provider_method": "get_domain",
      "signal_type": "email_public_exposure",
      "category": "identity_security",
      "severity": "medium",
      "severity_is_conditional": "yes",
      "conditional_rule": "Medium when a tenant-domain email in `emails[]` has at least one `reference`; upgrade to high if that email also has `numbers`, `location`, or `job_title`; downgrade to low if only the email string is populated with no enrichment; optionally suppress if only email pattern is known with no references.",
      "entity_type": "email",
      "finding_kind": "true_finding",
      "trigger_condition": "HTTP 200 from Get Domain for a tenant domain AND within `emails[]` at least one entry whose `email` belongs to a monitored identity or tenant domain AND has non-empty `references`.",
      "evidence_fields": [
        "domain",
        "email_pattern",
        "emails[].email",
        "emails[].personal",
        "emails[].domain",
        "emails[].verified",
        "emails[].references",
        "emails[].name",
        "emails[].job_title",
        "emails[].location",
        "emails[].numbers"
      ],
      "enrichment_fields": [
        "emails[].twitter",
        "emails[].linkedin",
        "emails[].name.confidence",
        "emails[].job_title.confidence",
        "emails[].twitter.confidence"
      ],
      "summary_template": "Email {email} under domain {domain} is publicly exposed with associated contact information on external websites.",
      "evidence_status": "documented_fields_derived_logic",
      "citation_refs": [
        "https://emailcrawlr.com/documentation/ (Domain section) [web:16]",
        "SpiderFoot sfp_emailcrawlr module (parsing of domain endpoint) [web:21]"
      ],
      "notes": "Same conceptual signal as get_email but sourced from bulk domain enumeration. Strong gating on tenant domains and identities is critical to avoid over-signalling; pattern-only knowledge without concrete references should be treated as enrichment, not a signal."
    }
  ],
  "confidence_guidance": [
    {
      "module": "username_exposure",
      "signal_type_or_use_case": "email_public_exposure via get_email",
      "source_reliability": "Moderate to high when `references` are present and enrichment fields are populated; per-field confidence scores for name, job_title, and social support nuanced weighting.",
      "freshness_considerations": "Use `references[].timestamp` and optional verification results to assess whether exposure is current vs historical.",
      "corroboration_rules": "Require at least one reference URL; consider re-validating the URL or cross-checking with other OSINT providers before treating PII-rich records as high severity.",
      "calibration_todo": "Measure false-positive rate across tenants; tune minimum reference count, PII presence, and reference age thresholds; empirically evaluate the usefulness of `verified` and verification outputs."
    },
    {
      "module": "username_exposure",
      "signal_type_or_use_case": "email_public_exposure via get_domain",
      "source_reliability": "Stable schema and integration via SpiderFoot suggest reliable parsing; coverage may vary by domain and web footprint.",
      "freshness_considerations": "Staff turnover and domain email patterns can change; use timestamps and deliverability checks to adjust trust in older entries.",
      "corroboration_rules": "Limit to tenant domains; require non-empty `references` for each email; optionally corroborate with get_email or alternate OSINT sources.",
      "calibration_todo": "Track coverage per tenant domain; compare enumerated addresses to internal inventories; tune suppression rules for pattern-only emails with no explicit references."
    },
    {
      "module": "username_exposure",
      "signal_type_or_use_case": "Using email/find as enrichment",
      "source_reliability": "Lower, as it is fundamentally probabilistic and pattern-based, indicated by `probability` and lack of direct references in docs.",
      "freshness_considerations": "Patterns may remain valid, but staff and address schemes can change; avoid long-lived assumptions without re-checking.",
      "corroboration_rules": "Only use to propose addresses to then query via get_email; never treat its output alone as evidence of exposure.",
      "calibration_todo": "Collect metrics on how often suggested addresses resolve to real users and have references; set safe `probability` thresholds."
    },
    {
      "module": "username_exposure",
      "signal_type_or_use_case": "Using email/verify to tune severity",
      "source_reliability": "Deliverability results are typically quite reliable for MX existence and gross sendability, but do not guarantee inbox ownership.",
      "freshness_considerations": "MX and catch-all configurations can change; re-verify periodically if severity depends on this data.",
      "corroboration_rules": "Use verification as a down-weighting factor, not as sole evidence; tie to reference recency and presence of PII.",
      "calibration_todo": "Compare verification fields against actual bounce stats (if accessible) to calibrate how much to reduce severity for non-sendable or invalid-mx addresses."
    }
  ]
}
```
