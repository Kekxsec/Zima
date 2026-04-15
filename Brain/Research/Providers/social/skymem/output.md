---
title: "output / social / skymem"
aliases: ["skymem output", "skymem signal registry"]
tags: [zima, research, outputs, signal-registry, social, skymem]
type: provider_research_output
provider: skymem
provider_category: social
status: complete
prompt_note: prompt.md
provider_folder: skymem.md
obsidianUIMode: preview
kind: reference
llm_include: true
code_scope: backend
---

# skymem Provider Integration Research for Zima

## API Surface Appendix
Skymem is a web-based email discovery service that finds email addresses associated with companies and people, primarily by crawling the public web and exposing the results through browser-based search interfaces on skymem.info and an email extractor on skymem.com. There is no publicly documented, official JSON API; OSINT tools interact with Skymem by fetching HTML search result pages and extracting email addresses from the page content, sometimes referring to this as a "free API" even though only HTML endpoints are documented indirectly. Given this, Skymem should be treated as an unauthenticated HTML search source for public email enumeration, suitable for enrichment and graph-building rather than primary breach/credential-exposure alerts.

This report scopes Skymem strictly as an input to Zima’s username_exposure module. It focuses on API surface as observable from official pages and well-known OSINT integrations, module mapping, signal contracts, severity and confidence guidance, implementation notes, and a structured JSON summary.

### Overview
1. skymem.com – Web Email Extractor (manual HTML interface)
Official description and purpose
The skymem.com site describes itself as a service to extract data (emails, domains, phones and other data) from plain text, and the main page provides a "Free web based email address extractor from text" where a user pastes arbitrary text and clicks a button to extract email addresses. This is clearly a browser-oriented utility for human users, not a documented HTTP API.

Endpoint / artifact

UI path: http://www.skymem.com/default.aspx (may redirect to equivalent default page).

Interaction model: HTML form where the user pastes arbitrary text and clicks "Start Extracting Emails"; the result is rendered in the page as an email list.

Purpose and supported entities

Purpose: Extract email addresses (and possibly related tokens such as domains or phone numbers) from arbitrary plain text pasted by the user.

Input entity type: Free-form text (not a discrete Zima entity such as email/domain).

Output entity types (derived by the client, not exposed as structured fields): email, domain (embedded in the emails), phone (per FAQ wording, but not schema-documented).

Auth and execution requirements

Authentication: None for basic use; page is publicly accessible.

Execution: Intended for manual use in a browser. There is no official statement that automated posting/scraping of this form is supported or allowed.

Top-level response and fields

Response format: HTML page with form elements and, after submission, extracted email addresses rendered in the document body.

Documented fields: None; there is no published JSON/XML schema. The FAQ only states that the site extracts "emails, domain, phone... and other data" from plain text.

Because no structured API responses are documented, all field-level details (IDs, CSS selectors, element structure) would have to be reverse-engineered from HTML and are inherently unstable. Those details are intentionally not fixed here.

Presence / optionality

Always present: HTML wrapper and form controls.

Conditional: Result section with extracted emails appears only after submission, based on the pasted input.

Optional / premium-only: Not documented; some marketing material mentions CSV export and advanced features, but these are described at a product level, not as an API.

Response variants

Successful hit: HTML page with a populated list of extracted email addresses (and possibly other tokens) rendered under the form; exact DOM structure not documented.

No-hit: Likely the same page with an empty or absent result section; behavior not explicitly documented.

Partial / limited: Not documented; any truncation or limits (e.g., maximum addresses) are unspecified.

Errors: Standard HTTP-level errors (e.g. 4xx/5xx) may occur, but there is no documented, structured error schema.

Classification for Zima

This interface requires manual text pasting and has no documented machine-to-machine contract. It should be treated as out_of_scope for automated Zima ingestion.

### skymem.info – Email Search by Domain / Person (HTML search interface)
Official / marketing descriptions
Multiple descriptions consistently state that skymem.info lets users find email addresses of companies and people, particularly by company domain, and can rapidly discover large numbers of email addresses associated with a given domain or individual. Various OSINT tool lists and frameworks categorize Skymem under "Email & Username OSINT" or specifically as a tool for finding employees’ emails by company domain.

Observed / inferred endpoints from OSINT tooling
SpiderFoot and OSINT packaging reference a "Skymem" module implemented as a free, unauthenticated API that looks up email addresses for a domain on Skymem. The module description and metadata clarify that:

Skymem is used to "Look up e-mail addresses on Skymem".

The model is described as FREE_NOAUTH_UNLIMITED or "Free API" in module listings, but no official key or rate-limit docs are cited.

From that module’s behavior (and supporting OSINT write‑ups), the following HTML endpoints can be inferred:

Search endpoint (inferred)

Path: GET http://www.skymem.info/srch?q={query} (query normally set to a domain name in OSINT tools).

Purpose: Return an HTML search result page listing email addresses related to the given query, most commonly all addresses Skymem associates with a corporate domain.

Supported query entities (functional, not schema-enforced):

Domain (primary use in OSINT tools).

Possibly personal name or other free-text, per marketing descriptions and user tutorials, but this is not API-documented.

Auth: None; treated as a public search endpoint by OSINT tools.

Response: HTML page containing matching email addresses and, for domain searches, links to domain-specific result pages.

Domain results pagination endpoint (inferred from OSINT module behavior)

Path: GET http://www.skymem.info/domain/{domain_id}?p={page}.

Purpose: Enumerate pages of email results tied to an internal domain_id for the queried domain.

Input entity type: Domain (indirectly; the caller first searches by domain string and extracts domain_id from the HTML, then paginates).

Auth: None; accessed as regular HTML pages.

Response: HTML pages that contain email addresses for the domain; SpiderFoot iterates multiple pages and extracts emails via text scraping.

Supported entity types (from Zima’s perspective)

Input entity types:

domain for the main Zima integration (username_exposure); queries are issued by domain.

Output entities (derived by the client):

email – addresses belonging to the queried domain appear throughout the HTML in plain text or mailto links.

Indirectly, username – the local part of each email is commonly used as a username in other systems; OSINT guides explicitly treat email and username OSINT as overlapping.

Top-level response fields and types

Response body type: HTML document, not JSON/XML.

Documented schema: None. All structured information (emails, domain identifiers, pagination parameters) must be parsed from HTML using regex or DOM parsing.

Key inferred data elements for a domain search:

List of discovered email addresses as text on the search and domain pages.

Internal domain_id value embedded in links, used for constructing domain pagination URLs.

Pagination links encoding ?p={page} parameters for subsequent pages.

These elements are deduced from how OSINT modules operate, not from official Skymem documentation, and therefore must be treated as inferred from examples only and subject to change.

Presence / optionality

Always present:

HTML shell and branding for the search and domain pages.

Conditional / optional:

Email list content, domain_id links, and pagination controls appear only when the query matches data Skymem has indexed for that domain or person.

Premium-only:

Product marketing mentions bulk search, larger lists, and CSV export as value propositions, implying that some larger result sets or convenience exports may be behind paid plans, but exact cutoffs and parameters are not described as an API.

Response variants

Successful hit (domain has known emails):

Search result page shows one or more email addresses associated with the input domain or query and links to domain-specific pages listing more results.

Domain pages expose additional pages of addresses; SpiderFoot limits itself to a certain number of pages (e.g., up to around 100 addresses in its description), which implies Skymem can hold more but the integration is conservative.

Successful no-hit:

The search returns an HTML page with no email addresses and likely a "no results" or empty-results view; this behavior is not explicitly documented, but OSINT tools handle this case implicitly by failing to extract any email addresses.

Partial / limited results:

Some OSINT documents phrase Skymem as "up to 100 e-mail addresses" for a target, suggesting either hard or soft per-target limits in free usage, but these are not formally documented by Skymem itself.

Error cases:

Not documented as an API; integrations depend on HTTP status codes and the presence or absence of HTML content. There is no known structured error payload.

Classification for Zima

GET /srch?q={domain} + GET /domain/{id}?p={page} (HTML): direct_signal_input into Zima’s Skymem client, but enrichment_only for the username_exposure module (see Module Mapping Appendix).

## Module Mapping Table

| provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|
| signal_producer (provider) / enrichment-only (this module) | search_domain_emails (internally: GET http://www.skymem.info/srch?q={domain} plus paginated GET /domain/{id}?p={page}) | HTML search result pages listing emails for a given corporate domain on skymem.info | enrichment_only | Input: domain; derived output: email and localpart-as-username | Only run for non-free-mail corporate domains; de-duplicate by (domain, email); do not emit standalone alerts—store discovered emails/usernames as OSINT enrichment for correlation with breach, phishing, and credential-stuffing findings; respect conservative rate limits and ToS, and disable if Skymem layout changes break parsing | Official FAQ and main site describe Skymem as text/email extractor and email finder, not as a structured API. OSINT tools and documentation (SpiderFoot, Kali package, OSINT lists) show Skymem being used as a free, unauthenticated HTML source to enumerate email addresses for a given domain. | Treated as a low-noise way to expand the graph of known corporate email addresses and likely usernames; not strong enough by itself to justify alerting about a "breach" or credential exposure. Future modules (e.g., phishing_surface) might emit signals from this enrichment. |
## Signal Contracts, Severity, and Tags
No standalone Zima signals are recommended for Skymem at this stage. The provider surfaces public, OSINT-discoverable email addresses without indicating compromise, stealer logs, dark‑web presence, or other direct evidence of a breach; as such, it is better modeled as enrichment for username/email graphs and downstream modules that reason about riskier data sources.

### Signal Contract Details
module	source	provider	provider_method	signal_type	category	severity	severity_is_conditional	conditional_rule	entity_type	finding_kind	trigger_condition	evidence_fields	enrichment_fields	summary_template	evidence_status	citation_refs	notes
(Intentionally left with no data rows. Skymem contributes enrichment only for username_exposure.)

## Confidence Guidance
Because Skymem does not expose breach evidence, passwords, or clear compromise indicators, there is no direct Zima signal tied solely to this provider in the username_exposure module.

If, in a future iteration, Zima decides to emit a dedicated signal such as public_email_address_enumerated from Skymem data, the recommended severity baseline would be low (or info if used purely as context) because:

The emails are already public by definition; Skymem explicitly focuses on finding addresses from the open web and public profiles.

The risk is secondary and indirect—enumerated corporate emails raise phishing and credential‑stuffing exposure but do not by themselves confirm a breach.

Conditional elevation (to medium) could be considered only if Skymem results are combined with:

Confirmed breach data containing the same addresses (e.g., password dumps, stealer logs) from other providers.

Additional OSINT context showing those addresses in high‑risk locations (paste sites, cracking forums), which Skymem itself does not natively expose.

For the current design, however, Skymem remains enrichment-only, so no severity is directly assigned.

## Implementation Notes
Even as enrichment, Skymem’s data quality and coverage matter for how Zima uses it. The table below provides module-level guidance.

### Confidence Guidance Table
module	signal_type_or_use_case	source_reliability	freshness_considerations	corroboration_rules	calibration_todo
username_exposure	OSINT email enumeration for corporate domains (no standalone signal)	Medium. Skymem is widely referenced in OSINT and sourcing communities as a free tool to find employees’ emails by domain and as part of email/username OSINT workflows, which supports basic reliability, but it has no formal guarantees on completeness or accuracy.
 False negatives are expected (many valid emails will never be crawled), and occasional false positives may arise from outdated or catch‑all addresses.	Skymem continuously crawls the open web, but there is no documentation of crawl cadence or "last seen" timestamps per address; results should be considered long‑lived OSINT rather than real‑time telemetry.
 Treat findings as potentially stale and do not infer that an address is currently active solely because Skymem lists it.	Use Skymem‑discovered emails primarily to expand the graph of candidate usernames/emails, then cross‑check with: (1) breach data providers for password exposure; (2) phishing/malware telemetry that targets those addresses; (3) internal login, MFA, and email‑security logs where available; and (4) other OSINT email sources (e.g., alternative email-finder tools) to confirm that an address is real and used in practice.
Measure overlap between Skymem results and other email-intel sources for a sample of customer domains, and track: (1) match rate against corporate identity inventories; (2) deliverability status via trusted email validation (separate provider); and (3) observed downstream alert usefulness when Skymem emails appear in breach or phishing findings. Use this to decide whether any Skymem-derived signal type (e.g., public_email_address_enumerated) should ever be promoted from enrichment to low/medium severity alerts.
## Appendix: Field Parsing and Storage
### Field paths and parsing
HTML-only responses: All programmatic integration must treat Skymem as an HTML source; there is no JSON schema or stable field layout documented by Skymem.

Minimal parsing contract: Zima’s Skymem client should aim to extract only:

The set of email addresses appearing in the search results and domain pages for the queried domain.

Optionally, the internal domain_id used for pagination, if available.

Avoid overfitting to layout: Do not rely on specific CSS classes, table structures, or surrounding labels beyond what is minimally required to find email-like strings; OSINT tools typically use general email-extraction helpers instead of DOM‑tight selectors for this reason.

Null / no‑hit behavior: Treat a response that yields no parseable emails as a clean no‑hit. Do not treat this as an error unless the HTTP response code or body is clearly invalid or blocked.

### Rate limits, billing, licensing, and ToS
No documented rate limits: Third‑party OSINT modules label Skymem as a "Free API" with a FREE_NOAUTH_UNLIMITED model, but this is a classification by those projects, not an official guarantee from Skymem.

Commercial features: Product descriptions mention bulk search, CSV export, and advanced filters as part of Skymem’s value proposition, implying paid or plan‑based usage tiers.

Legal / ethical considerations: Because Skymem is a web service with advertising and likely its own Terms of Service, automated large‑scale scraping may be restricted even if technically possible. Before production use, Zima should (a) review Skymem’s ToS and robots.txt, (b) consider contacting Skymem for explicit permission or a commercial arrangement, and (c) implement a very conservative rate limit and cache to minimize traffic.

### Deduplication and identifiers
Natural keys: For enrichment storage, use (provider = skymem, input_domain, email_address) as the primary key. This is stable and independent of any internal domain_id that Skymem uses in its URLs.

Versioning: Optionally track first_seen_at and last_seen_at timestamps in Zima’s own datastore to understand when an email was first and last observed from Skymem. This is a Zima-level field; Skymem does not provide it.

Avoid storing internal IDs: Skymem’s internal domain_id is not stable or meaningful outside their system; it should be considered an implementation detail useful only for pagination.

### Evidence and storage
Evidence to keep (per enriched email address):

email string itself (primary evidence).

input_domain used in the query.

provider = skymem, source = username_exposure (or dedicated Skymem client) for provenance.

collection_time (Zima time of retrieval).

What not to store:

Full HTML snapshots of Skymem pages, to reduce PII overcollection, storage size, and potential ToS friction.

Any cookies or tracking tokens from Skymem or its ad partners, which are irrelevant to security analytics and may be privacy‑sensitive.

### Client vs mapper vs correlation layer
Provider client:

Implements HTML fetching with robust retry, backoff, and user‑agent handling.

Contains the HTML‑to‑email extraction logic (using a generic email-extraction helper shared across providers where possible).

Outputs a normalized internal record: { input_domain, email, provider: 'skymem', collected_at }.

Module mapper (username_exposure):

Consumes the client’s normalized emails and maps them to Zima entities: entity_type = email, plus username = localpart(email) as an attribute for correlation.

Does not generate standalone signals from Skymem alone; instead, enriches Zima’s user/identity graph.

Correlation layer:

Joins Skymem-derived email/username nodes with higher‑risk data (credential dumps, stealer logs, phishing targets, login anomalies) to generate higher‑severity signals in other modules.

May, in future, gate a low‑severity public_email_address_enumerated signal based on cross‑provider corroboration and empirically measured usefulness.

## Provider Summary and Structured JSON
Strongest signal types / contributions

High‑coverage OSINT enumeration of corporate email addresses associated with a given domain, which can materially improve Zima’s knowledge of employee email and username space for attack-surface mapping and later correlation.

What Skymem should not be used for

Direct breach or credential‑exposure detection (no passwords, no stealer logs, no dark‑web context).

Attribution of threat actors or malware infrastructure (Skymem indexes legitimate public web content, not malicious C2 or botnet telemetry).

High‑confidence email validation; while marketed as including validation, it fundamentally reports presence of emails on the web, not SMTP‑level deliverability or security posture.

API/auth/rate‑limit/licensing cautions

There is no public, vendor-maintained API specification; what OSINT tools call a "Free API" is essentially scripted access to HTML search pages.

Rate limits, data-use terms, and paid‑tier boundaries (e.g., CSV export, bulk search) are only described at a marketing level and not documented as hard API quotas.

Zima should explicitly validate compliance with Skymem’s Terms of Service and privacy policy before large‑scale, automated use.

Role in current Zima stage

For the username_exposure module, Skymem should be treated as enrichment-only: it feeds additional public emails and derived usernames into Zima’s identity graph but does not directly produce standalone alerts.

At the provider level, Skymem is still a signal_producer in the sense that it introduces new entities (emails, usernames) into the environment, but those signals are currently confined to internal graph enrichment rather than surfaced as customer-facing alerts.

```json
{
  "provider": "skymem",
  "provider_category": "social",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "username_exposure",
      "provider_role_for_module": "enrichment_only",
      "provider_method": "search_domain_emails (GET http://www.skymem.info/srch?q={domain} plus paginated GET /domain/{id}?p={page})",
      "endpoint_or_artifact": "HTML search result and domain pages listing emails for a given domain on skymem.info",
      "classification": "enrichment_only",
      "entity_types": {
        "input": ["domain"],
        "derived_output": ["email", "username"]
      },
      "gating_logic": "Only run for non-free-mail corporate domains; backoff and cache responses to respect Skymem's ToS; de-duplicate by (domain, email); do not emit standalone alerts from Skymem alone.",
      "notes": "Used to expand OSINT knowledge of corporate email addresses and likely usernames; currently no direct Zima signals are emitted solely from Skymem results."
    }
  ],
  "signal_contracts": [],
  "confidence_guidance": [
    {
      "module": "username_exposure",
      "signal_type_or_use_case": "OSINT email enumeration for corporate domains (no standalone signal)",
      "source_reliability": "Medium: widely referenced OSINT tool with reasonable coverage but no formal guarantees; expect false negatives and some stale or generic addresses.",
      "freshness_considerations": "Treat findings as long-lived OSINT; crawl cadence and address 'last seen' times are undocumented, so results may be stale.",
      "corroboration_rules": "Use Skymem-derived emails primarily as candidates; require corroboration from breach data, phishing telemetry, or other email-finder sources before treating them as high-value identities.",
      "calibration_todo": "Measure overlap with internal identity inventories and other email-intel providers; track downstream alert usefulness when Skymem emails participate in higher-risk findings to decide whether to promote any Skymem-derived signals."
    }
  ]
}
```
