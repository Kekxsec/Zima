---
title: "output / phone / truecaller"
aliases: ["truecaller output", "truecaller signal registry"]
tags: [zima, research, outputs, signal-registry, phone, truecaller, graph_exclude]
type: provider_research_output
provider: truecaller
provider_category: phone
status: complete
prompt_note: prompt.md
provider_folder: truecaller.md
obsidianUIMode: preview
---

Truecaller's only officially documented, supported APIs today are the "Verified Business APIs," which manage and personalize your own outbound business numbers; they do not expose spam risk, community reports, or reverse lookup data for arbitrary numbers, so for a phone_exposure module you should currently treat Truecaller as enrichment/utility for your own numbers, not as a standalone signal source.

Below I map the current API surface, classify it for phone_exposure, and deliberately leave the signal table empty because no response field meets your severity definitions for a true phone-exposure finding under the official APIs.

## API Surface Appendix

1) Generate Access Token
Endpoint

POST /clients/{clientAccountId}/token on https://enterprise-portal-noneu.truecaller.com.

Purpose

Exchange an API key + key ID pair for a short‑lived access token used in Authorization headers for all Verified Business APIs.

Auth / execution

Path parameter: clientAccountId (UUID, required).

Headers:

X-Public-Access (required; documented as string, semantics not further described).

Accept (optional; example application/vnd.api+json; version=1.0).

Content-Type: application/json.

Body (JSON):

api_key (UUID, required).

key_id (UUID, required).

Response

On 200 success, JSON with at least:

created_at (ISO8601 timestamp).

token (string, bearer token).

Error responses documented for 400, 401, 500 but without detailed schema.

Rate limits / quotas

"A maximum of 10 tokens can be created every 30 minutes."

A maximum of 5 API keys per customer account at any time.

Notes for Zima

Classification: utility_only (auth plumbing).

Token lifetime and exact expiry field are not documented → you will need to track expiry empirically or treat non‑401 as valid.

Evidence status: documented.

2) Number Management – Feature Set ID
Endpoint

GET {{BaseURL}}/clients/{clientAccountId}/number_management/feature_sets (BaseURL as above).

Purpose

Retrieve feature‑set IDs needed to list/delist business numbers and to group them by process/department/label.

Supported entity types

Effectively: phone numbers owned by the business; feature sets themselves are configuration objects, not entities.

Auth / execution

Uses the access token from the token endpoint via Authorization: Bearer <token> (inferred from other endpoints; not shown explicitly on this page but referenced generically in the "Authentication" docs and other endpoints).

Top‑level response fields

feature_sets – array of objects, each including at least:

id (UUID, feature set ID).

name (string).

status (string, e.g. "draft").

process_id (UUID).

client_account_id (UUID).

label_id (UUID).

call_reason_id (UUID).

department_id (UUID).

calling_operation_id (UUID).

calling_operation_name (string, e.g. "Sales" in example).

process_name (string).

sub_process_name (string, may be empty).

created_at, updated_at (ISO8601 timestamps).

Presence / optionality

Some fields (like sub_process_name) appear as empty strings in examples → treat as optional. Exact "required" vs "optional" status not fully specified.

Variants / errors

No explicit "no‑hit" variant documented; expect empty feature_sets array. Error schema not detailed.

Notes for Zima

Only configuration metadata about how your numbers will be presented (label, call reason etc.), not Truecaller's community risk perception.

Classification for phone_exposure: utility_only (used to drive other API calls).

Evidence status: documented.

3) Number Management – List Numbers (Publish)
Endpoint

POST {{BaseURL}}/clients/{clientAccountId}/number_management/feature_sets/{featureSetId}/numbers/publish.

Purpose

Associate up to 10,000 phone numbers with a feature set so they will show as verified business caller IDs under that configuration.

Supported entity types

Phone numbers (business‑owned).

Auth / execution

Headers:

Content-Type: application/json.

Authorization: Bearer <token>.

Path parameters: clientAccountId, featureSetId.

Body:

phone_numbers – documented as "string" but text says "numbers to be added to feature set"; example body is truncated, so exact shape (single string vs array) is unclear.

Response / variants

The "Number details" page shows two example fragments that appear to be related to listing/delisting attempts:

A successful case returning:

numbers: array of number objects (see Number Details below).

pagination_information: total_page_count.

A failed case returning:

client_account_id.

phone_type (empty string in example).

processing_numbers, new_numbers, other_phonetype_numbers, existing_numbers, others_numbers, invalid_numbers, other_feature_set_numbers: all arrays of strings.

status: "failed".

However, the docs do not explicitly tie these examples to numbers/publish vs some other list/delist endpoint → treat mapping as inferred from examples only.

Notes for Zima

This is a provisioning call, not an inspection call; it does not return spam scores or exposure, only whether your numbers were accepted into a feature set.

For phone_exposure, you might log provisioning failures as operational events, but they are not external‑risk signals per your severity model.

Classification: utility_only.

Evidence status: response fields documented; linkage to this exact endpoint partially inferred.

4) Number Details (Number Management)
Endpoint / method

Section title "Number details | Verified Business APIs"; HTTP method and full path are not shown in the snippet. Likely some GET .../number_management/.../numbers variant, but this is not documented in the captured text, so treat path as unknown.

Purpose

Retrieve metadata about listed business numbers under a client account and (presumably) feature set.

Supported entity types

Phone numbers owned by the business.

Response – successful case

Top‑level:

numbers: array of objects.

pagination_information.total_page_count (integer).

Each number object (fields as shown):

phone_number (string; appears as concatenated country code + national digits).

phone_type (string; example "verified").

status (string; example "listed").

client_account_id (UUID).

created_by_email (string email).

department (string).

operation (string; e.g. "Collections").

process (string).

subprocess (string, often empty).

feature_set_name (string).

call_me_back (string flag, e.g. "enabled").

created_at, updated_at (ISO8601 timestamps).

label_name (string).

Response – "failed" case

Separate example shows:

client_account_id (UUID).

phone_type (string, empty in example).

processing_numbers, new_numbers, other_phonetype_numbers, existing_numbers, others_numbers, invalid_numbers, other_feature_set_numbers: arrays of phone numbers grouped by status.

status: "failed".

This looks like a bulk listing/delisting status response, possibly linked to numbers/publish.

Optionality

subprocess often empty; treat as optional. Others appear consistently present in examples but not explicitly marked required.

Notes for Zima

Fields describe your own configuration (department, operation, feature set, "call me back" flag), not how Truecaller's user community perceives the number (no spam stats or risk in the API).

Could be used as enrichment for your internal phone‑inventory and call‑routing metadata when correlating with other exposure data.

Classification for phone_exposure: enrichment_only.

Evidence status: documented (schema from official example; endpoint path unknown).

5) Call Personalisation – Real‑time (to be deprecated)
Endpoint

POST /clients/{clientAccountId}/dynamic_call_record.

Purpose

Push a single real‑time "dynamic caller ID" record so Truecaller can display a customized label and call reason for a specific caller–receiver pair within a defined time window.

Supported entity types

Caller and receiver phone numbers (string digits, no "+").

Auth / headers

Authorization: Bearer YOUR_OAUTH2_TOKEN.

Content-Type: application/json.

Optional Accept.

Request body fields (all documented as plain JSON):

call_reason (string, optional; min length 10, max 100).

caller (string, required; caller phone number without "+").

receiver (string, required; receiver phone number).

label_id (UUID, required; must be a dynamic label belonging to the client).

label_name (string, optional; max 40 chars; if absent, defaults to label's configured name).

starts_at (integer int64, required; epoch ms when dynamic caller ID becomes active).

ends_at (integer int64, required; epoch ms when it should expire; must not be before current time; starts_at–ends_at not more than 24 hours apart).

Response & rate limits

Response body: "No content" on success (no schema given).

Rate limits:

Each token can handle 100 requests per second.

Maximum of 10 tokens can be created in every 30 minutes.

Notes for Zima

This endpoint only sends data; returns no insight into spam risk or external perception.

For phone_exposure, this is about shaping exposure, not measuring it, and better belongs in a future "telephony_delivery"/"customer_contact" module.

Classification: utility_only for phone_exposure; potential out_of_scope.

Evidence status: documented.

6) Call Personalisation – Batch v2
Endpoint

POST {{BaseURL}}/v2/clients/{clientAccountId}/dynamic_call_records.

Purpose

Batch variant of call personalization; send up to 500 dynamic call records in one request.

Auth / headers

Authorization: Bearer <token>, Content-Type: application/json.

Request body fields (top‑level):

call_records (array of objects, required, min 1, max 500).

Each call record object includes:

dynamic_call_reason (string, optional; min 10, max 100).

caller_number (string, required).

receiver_number (string, required).

dynamic_label_name (string, required; min 3, max 40).

label_id (string, optional; if absent, caller ID name defaults to the label name).

starts_at (int64 epoch ms, required; not more than 24 hours before ends_at).

ends_at (int64 epoch ms, required; not before current time; starts_at–ends_at max 24 hours).

Rate limits

60 requests per minute per token; batch size up to 500 call records per API call.

Response / status

Separate "Call Personalization Batch v2 Status" endpoint returns status for these records, with fields including:

id (UUID).

label_id (UUID).

dynamic_label_name (string, e.g. "Centro Bank KYC Department").

dynamic_call_reason (string, e.g. "Calling you for KYC Verification").

starts_at, ends_at (epoch ms).

status_info.status (e.g. "success").

created_at (timestamp).

Exact status endpoint path is not visible in the snippet → treat path as unknown.

Notes for Zima

Again, this configures content; it does not surface spam metrics or community flags.

For phone_exposure, these APIs could be used upstream (telephony system) but do not themselves produce "exposure" signals.

Classification: utility_only for phone_exposure.

Evidence status: documented.

7) Spam Management – Console & Emails (Non‑API)
Artifacts

Spam Management knowledge base and related FAQs; not an API.

Purpose

Explain how Truecaller's spam classification works and how verified business numbers will be marked and notified when they cross spam thresholds.

Key documented behaviors

Spam lists and spam threshold are built using a proprietary ML algorithm based on user feedback (spam reports), call recency, call frequency, average duration, pickup rate, etc.

The Truecaller for Business self‑serve portal is "updated live with the status of all onboarded numbers" and sends an automated email when a number crosses the spam threshold.

When the spam threshold is breached, an "additional tag showing the spam score shall be displayed," and the number is demoted for some call‑priority use cases.

Programmatic access

No official API path or JSON schema is documented for spam score or spam status; all references are to UI and email behavior.

Notes for Zima

This is exactly the kind of intelligence you would want for phone_exposure (numbers marked spam, spam score), but as of the available docs it is not exposed through Verified Business APIs.

Any scraping or email‑parsing would be non‑official and TOS‑sensitive.

Classification: out_of_scope for official integration; potential future feature if Truecaller adds an API.

Evidence status: documented at conceptual level, but no API schema.

8) Reverse Phone Lookup – Web UI (Non‑API)
Artifact

Reverse phone number lookup web tool at truecaller.com/reverse-phone-number-lookup.

Purpose

Human‑facing reverse lookup: show caller name, general location, line type, spam/scam warning, a "Spam Risk Rating," and spam statistics like "Calls Made," "Spam Reports," "Look‑ups," "Pick‑up rate," "Top Countries," "Peak Calling Hours" for a searched number.

Access

Browser UI only; requires sign‑in; rate‑limited in volume from the web; docs explicitly emphasize the app for unlimited lookups.

Programmatic status

No JSON/REST interface documented; prior REST API is explicitly described by third‑party catalogues as "defunct as of March 2017."

Notes for Zima

Conceptually defines the fields you'd want (spam risk rating and stats) but is non‑programmatic today.

Any API implied via mobile/web scraping or internal endpoints would be unofficial.

Classification: out_of_scope for compliant integration; potential future mapping if a supported API appears.

Evidence status: documented (UI description) but not as API.

9) Truecaller SDK (Verification)
Artifacts

Truecaller SDK docs (docs.truecaller.com/truecaller-sdk), including Android/iOS and Mobile Web integration guides.

Purpose

Verify a user's mobile number and fetch profile details using an OAuth‑like flow; primarily for login/identity verification in apps and mobile websites.

Key data objects

OAuth token at https://oauth-account-noneu.truecaller.com/v1/token, then user profile via /v1/userinfo, with scopes such as profile, phone, openid.

Android TrueProfile object exposes fields like first name, last name, company name, and a boolean isTrueName indicating whether the user profile is verified.

Notes for Zima

These flows are per‑user, consented, and used to verify the authenticity of the user's own phone number, not to rate it for spam or perform arbitrary reverse lookups.

For a future identity_verification or account_security module you could use these SDK outputs as strong identity signals; however, they are mobile‑app centric, not a back‑office batch API.

For phone_exposure, SDK outputs are largely out_of_scope.

Evidence status: documented.

10) Legacy / Unofficial Reverse Lookup APIs (Out‑of‑scope)
Legacy REST API

Third‑party API directories and Q&A note a historical Truecaller REST API that allowed reverse number lookup and returned a spam score and "True score," accessible with an APPKEY, but also report it is no longer available and was limited to "handpicked" developers.

Catalogues explicitly flag the REST API as "Defunct as of March, 2017."

Unofficial wrappers

Libraries like truecallerjs, truecallerpy, and various GitHub projects demonstrate reverse lookup by emulating the mobile app and scraping internal endpoints; they expose methods like search(number, countryCode, installationId) and response helpers getName(), getAddresses(), getEmailId(), etc.

Notes for Zima

These are explicitly unsupported and would almost certainly violate Truecaller's terms at scale; they are not suitable as a core provider integration for Zima.

Classification: out_of_scope for production; you may study them for field naming inspiration only, but must not rely on them.

Evidence status: third‑party; used only to confirm that official, documented APIs do not currently expose the same capabilities.

## Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|
| phone_exposure | signal_producer | generate_access_token | POST /clients/{clientAccountId}/token | utility_only | unknown (auth token) | Only call from provider client when token is expired/absent; do not tie to any entity; never emit signals from this endpoint. | | Rate‑limited to 10 tokens per 30 minutes; cache token centrally; handle 400/401/500 as auth/usage failures, not security events. |
| phone_exposure | signal_producer | list_feature_sets | GET /clients/{clientAccountId}/number_management/feature_sets | utility_only | phone (indirect) | Use only to discover featureSetId for subsequent number‑management calls; no risk data; do not emit signals. | | Treat feature sets as configuration objects; changes here might be audited in a separate "telephony configuration" module, not in phone_exposure. |
| phone_exposure | signal_producer | number_details | Number details API under Number Management (path not fully documented) | enrichment_only | phone | Only query for numbers you already manage in Truecaller Business; use metadata (department, feature_set_name, label_name, call_me_back, status) to enrich your own phone inventory; do not interpret any field as spam/risk. | | Use status strictly as enrollment status ("listed" vs failure) in the Verified Business program, not as spam/abuse state (no spam fields are documented here). |
| phone_exposure | signal_producer | list_numbers_publish | POST .../number_management/feature_sets/{featureSetId}/numbers/publish | utility_only | phone | Only use during provisioning workflows; treat "failed" responses as operational errors; no signals. | | Bulk grouping arrays like invalid_numbers are useful to surface back to admins via your own UI, but do not constitute security exposures. |
| phone_exposure | signal_producer | call_personalisation_realtime | POST /clients/{clientAccountId}/dynamic_call_record | utility_only | phone | Use only in outbound dialer / contact‑center integration to set call reason and label; never read it for risk; no signals. | | Rate‑limited to 100 RPS per token; more appropriate for a "call_delivery" integration layer than phone_exposure. |
| phone_exposure | signal_producer | call_personalisation_batch_v2 | POST /v2/clients/{clientAccountId}/dynamic_call_records and status endpoint | utility_only | phone | Same as above; write‑only personalization plus batch status; no spam metrics. | | Use status for delivery monitoring (success/failure) only; integration mostly operational. |
| phone_exposure | signal_producer | spam_management_console | Web console + automated spam‑threshold emails | out_of_scope (no official API) | phone | May be consumed manually by ops teams; do not build polling/scraping integration; any future API would warrant a new design. | | Today this is your only way to see Truecaller spam scores for your numbers; integration would require either email processing or UI scraping, both undesirable. |
| phone_exposure | signal_producer | reverse_phone_lookup_web | Reverse phone lookup website | out_of_scope | phone | Strictly human interactive; do not automate; do not rely for machine‑scale enrichment. | | Defines conceptual spam metrics ("Spam Risk Rating," spam stats) you might want if a formal API emerges in future. |
| phone_exposure | signal_producer | truecaller_sdk_verification | SDK OAuth + userinfo endpoints | out_of_scope (for this module) | phone / account | Might be used in an identity_verification module to assert that a user controls a number; no direct relationship to phone exposure/spam risk. | | Mobile/OAuth‑centric; requires user consent; not a batch data‑broker feed. |
| phone_exposure | signal_producer | legacy_rest_api | Historical reverse lookup REST API | out_of_scope | phone | Do not attempt to use; clearly marked defunct; keys unlikely to be issued. | | Historical docs and third‑party posts confirm this API was limited and has been shut down; treat any current use as unsupported. |

Implication: for the only mapped module (phone_exposure), all officially documented endpoints are enrichment_only or utility_only. There is no supported, documented API field today that directly encodes spam risk, reputation, or exposure in a way that matches your severity model.

## Signal Contracts, Severity, and Tags

There are no standalone signals that can be safely and cleanly emitted from Truecaller's official APIs for the phone_exposure module as of the current documentation. The spam status and spam score you would normally want are limited to UI and email surfaces without a published API schema.

Per your instructions, the table is therefore empty:

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Design note: if Truecaller later publishes a spam‑status/score API for business numbers or arbitrary numbers, you could introduce signal types such as phone_number_marked_as_spam or phone_number_high_spam_risk for phone_exposure, with severity high/medium according to your calibration, driven by those documented fields. That cannot be specified today without guessing field names and enums.

## Confidence Guidance

Because no signal rows are defined, no binding severity rules are attached in this pass. Conceptually:

Any future phone_number_marked_as_spam signal driven by a Truecaller spam status field would likely be at least medium severity (reputation degradation, potential loss of contactability) and could be high if combined with other evidence of abuse or impersonation. This would hinge on official documentation of spam‑status enums and thresholds.

Configuration‑level events like "number listing failed" or "number not listed" would generally be low (misconfiguration) in your model, not security exposures, and sit more naturally in a telephony ops module.

Until there is a documented spam/status field, you should resist assigning any Zima severity to Truecaller's internal scores.

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|
| phone_exposure | Use Number Management "number details" to enrich your own outbound numbers (department, process, label, call_me_back, status) | Data originates from your own Truecaller for Business configuration and backend; high reliability for what is stored, but it says nothing about external user perception or spam. Changes in feature sets or number status propagate as you call the API; staleness is mostly about how often you sync vs how often ops change configs in the Truecaller console. | When correlating phone exposure findings from other providers (e.g., carrier feedback, CNAM), require that the same E.164 phone number appears in your Truecaller numbers list before attaching Truecaller metadata; never infer spam vs non‑spam from status or phone_type. | Benchmark sync frequency and cache invalidation strategy; decide whether you want near‑real‑time config mirrors or periodic imports; define exact mapping of department/operation/process fields into Zima's own phone‑inventory model. | |
| phone_exposure | Future: spam / negative reputation feed if Truecaller exposes spam status / spam score via API | Spam classification is community‑driven but backed by large user base and ML; spam lists are created by users reporting unsolicited calls/SMS and refined using call behavior metrics, so signal quality is likely high but not perfect. Portal is "updated live" with spam status; current spam reports in the last 60 days are factored into risk and statistics (calls made, reports, look‑ups, pickup rate, top countries, peak hours), implying that risk is time‑sensitive and can decay if behavior changes. | For high‑impact actions (blocking numbers, altering dialing strategy, or raising security incidents), require corroboration from at least one additional source (carrier reputation feeds, other apps like Hiya, customer complaints) before treating Truecaller spam as high severity; consider requiring stability of spam status over multiple days. | If and when an API appears, calibrate severity buckets (critical/high/medium/low) based on a mix of Truecaller's numeric or categorical spam fields, trend indicators (increasing vs decreasing reports), and your own false‑positive studies on customer numbers; define recency windows (e.g. "spam in last 60 days") that matter for Zima. | |

## Implementation Notes

1. Strongest potential signal types
Spam classification and spam statistics for specific phone numbers:

Truecaller clearly maintains rich per‑number metrics (Spam Risk Rating, spam reports, calls made, pick‑up rate, top countries, peak calling hours) surfaced in their app and reverse‑lookup website.

Their spam algorithm uses community reports and behavioral signals (recency, frequency, duration, pickup rate), and the Verified Business console actively tracks when your numbers cross a spam threshold, tagging them with a spam score and demoting their call priority.

However, none of these fields are currently exposed via the documented Verified Business APIs; they remain UI‑only.

If a formal API for spam status, spam score, or spam trend metrics appears, these would become strong phone_exposure signals.

2. What the provider should not be used for (in Zima, today)
Not a general reverse‑lookup or spam‑score API:

The only documented public REST API for reverse lookup is explicitly marked "defunct as of March, 2017," and current official docs provide no replacement.

Unofficial wrappers that simulate the Truecaller app are out‑of‑scope for a compliant, maintainable integration.

Not a breach/PII exposure or dark‑web source:

Truecaller's role is caller ID, spam blocking, and verified business identity; there is no evidence it publishes credential leaks, dark‑web data, or content matching your breach, stealer_log, plaintext_password, etc. tags.

Not an identity‑only provider for phone_exposure:

The SDK's user verification is powerful but tailored to app logins; for phone_exposure you care more about the phone number's reputation in the wild, which is currently non‑API.

3. API/auth/rate‑limit/licensing cautions
Verified Business is a paid, account‑scoped product:

You must onboard as a Truecaller for Business customer, manage API keys via the business console, and operate within per‑account limits (max five API keys active, max ten tokens per 30 minutes).

Access tokens and rate limits:

Access tokens are created via POST /clients/{clientAccountId}/token and should be cached in your provider client; exceeding token generation or per‑endpoint rate limits will cause throttling.

Call Personalisation real‑time: 100 RPS per token, up to 10 tokens per 30 minutes.

Call Personalisation Batch v2: 60 RPM per token, up to 500 call records per batch.

Terms and scraping:

The reverse‑lookup site and app are explicitly user‑facing; no sanctioned API is documented. Using them programmatically (e.g., scraping, headless browsers) likely violates ToS; similarly, unofficial libraries that emulate the app are not appropriate for a production integration.

4. How to treat this provider in Zima today
Effective role for phone_exposure

Despite being labelled "signal_producer" in your map, Truecaller's official APIs currently behave as enrichment/utility for phone_exposure: they help you manage and annotate your own business numbers but do not emit direct security or exposure signals under your severity model.

Recommended stance

Treat Truecaller as:

Utility‑only for provisioning and call personalisation (access tokens, feature sets, list numbers).

Enrichment‑only for augmenting your own number inventory with labels, departments, processes, and call‑me‑back flags.

Deferred signal‑producer for spam/reputation metrics, pending a documented API.

Do not define production signals or severities until Truecaller exposes spam data in a documented, supported way.

## Provider Summary and Structured JSON

```json
{
  "provider": "truecaller",
  "provider_category": "phone",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "phone_exposure",
      "provider_role": "signal_producer",
      "provider_method": "generate_access_token",
      "endpoint_or_artifact": "POST /clients/{clientAccountId}/token",
      "classification": "utility_only",
      "entity_types": ["unknown"],
      "gating_logic": "Only used by the provider client to obtain a bearer token; do not emit signals or associate with entities.",
      "citation_refs": ["https://docs.truecaller.com/truecaller-for-business/verified-business-api-documentation/getting-started/authentication", "https://docs.truecaller.com/truecaller-for-business/verified-business-api-documentation/getting-started/post-generate-access-token"],
      "notes": "Rate-limited to 10 tokens per 30 minutes; store token centrally and treat HTTP 4xx/5xx as auth or usage issues, not phone-exposure findings."
    },
    {
      "module": "phone_exposure",
      "provider_role": "signal_producer",
      "provider_method": "list_feature_sets",
      "endpoint_or_artifact": "GET /clients/{clientAccountId}/number_management/feature_sets",
      "classification": "utility_only",
      "entity_types": ["phone"],
      "gating_logic": "Call from provider client to discover featureSetId for number management; do not generate signals.",
      "citation_refs": ["https://docs.truecaller.com/truecaller-for-business/verified-business-api-documentation/number-management", "https://docs.truecaller.com/truecaller-for-business/verified-business-api-documentation/number-management/feature-set-id"],
      "notes": "Feature sets are configuration objects describing how your numbers are grouped and labeled; no spam or risk fields are present."
    },
    {
      "module": "phone_exposure",
      "provider_role": "signal_producer",
      "provider_method": "number_details",
      "endpoint_or_artifact": "Number details API (path not fully documented)",
      "classification": "enrichment_only",
      "entity_types": ["phone"],
      "gating_logic": "Only query for numbers that belong to your Truecaller for Business account; use results to enrich internal number inventory, not as direct exposure signals.",
      "citation_refs": ["https://docs.truecaller.com/truecaller-for-business/verified-business-api-documentation/number-management/number-details"],
      "notes": "Provides fields like phone_number, phone_type, status, department, process, feature_set_name, call_me_back, label_name and timestamps; status here is enrollment status (e.g. 'listed'), not documented as spam or abuse status."
    },
    {
      "module": "phone_exposure",
      "provider_role": "signal_producer",
      "provider_method": "list_numbers_publish",
      "endpoint_or_artifact": "POST /clients/{clientAccountId}/number_management/feature_sets/{featureSetId}/numbers/publish",
      "classification": "utility_only",
      "entity_types": ["phone"],
      "gating_logic": "Use during provisioning flows to add numbers to a feature set; treat failures as operational; no direct signals.",
      "citation_refs": ["https://docs.truecaller.com/truecaller-for-business/verified-business-api-documentation/number-management/list-number", "https://docs.truecaller.com/truecaller-for-business/verified-business-api-documentation/number-management/number-details"],
      "notes": "Bulk responses group numbers into arrays like invalid_numbers or other_feature_set_numbers; helpful for admin feedback but not security exposures."
    },
    {
      "module": "phone_exposure",
      "provider_role": "signal_producer",
      "provider_method": "call_personalisation_realtime",
      "endpoint_or_artifact": "POST /clients/{clientAccountId}/dynamic_call_record",
      "classification": "utility_only",
      "entity_types": ["phone"],
      "gating_logic": "Only used to push dynamic caller ID data (label, call reason, time window) for specific caller/receiver pairs; never queried for risk.",
      "citation_refs": ["https://docs.truecaller.com/truecaller-for-business/verified-business-api-documentation/call-personalisation/call-personalisation-real-time-to-be-deprecated"],
      "notes": "Write-only personalization API with 100 RPS per token; out of scope for exposure detection, better suited to telephony-delivery integration."
    },
    {
      "module": "phone_exposure",
      "provider_role": "signal_producer",
      "provider_method": "call_personalisation_batch_v2",
      "endpoint_or_artifact": "POST /v2/clients/{clientAccountId}/dynamic_call_records and Batch v2 Status endpoint",
      "classification": "utility_only",
      "entity_types": ["phone"],
      "gating_logic": "Use for batch personalization in outbound dialers; track status for delivery health; do not treat any field as a spam or risk indicator.",
      "citation_refs": ["https://docs.truecaller.com/truecaller-for-business/verified-business-api-documentation/call-personalisation/call-personalisation-batch-v2", "https://docs.truecaller.com/truecaller-for-business/verified-business-api-documentation/call-personalisation/call-personalisation-batch-v2-status"],
      "notes": "Supports up to 500 records per request at 60 RPM per token; status objects include dynamic_label_name, dynamic_call_reason, starts_at, ends_at, status_info.status."
    },
    {
      "module": "phone_exposure",
      "provider_role": "signal_producer",
      "provider_method": "spam_management_console",
      "endpoint_or_artifact": "Truecaller for Business spam management portal + email notifications",
      "classification": "out_of_scope",
      "entity_types": ["phone"],
      "gating_logic": "Can only be consumed manually or via non-official means (e.g., parsing spam-alert emails); do not build scraping integration.",
      "citation_refs": ["https://truecaller.zohodesk.in/portal/en/kb/truecaller/spam-management", "https://truecaller.zohodesk.in/portal/en/kb/articles/how-is-spam-calculated", "https://truecaller.zohodesk.in/portal/en/kb/articles/how-will-the-spam-update-happen-how-will-i-know-which-numbers-are-spam"],
      "notes": "Portal shows spam status and spam score tags when numbers cross a spam threshold and sends alert emails; no official API schema for this data exists yet."
    },
    {
      "module": "phone_exposure",
      "provider_role": "signal_producer",
      "provider_method": "reverse_phone_lookup_web",
      "endpoint_or_artifact": "https://www.truecaller.com/reverse-phone-number-lookup",
      "classification": "out_of_scope",
      "entity_types": ["phone"],
      "gating_logic": "Human-facing tool; do not automate; use only for manual validation during investigations.",
      "citation_refs": ["https://www.truecaller.com/reverse-phone-number-lookup"],
      "notes": "UI exposes Spam Risk Rating and detailed spam stats for a number, but no associated REST/JSON API is documented; prior public API is defunct."
    },
    {
      "module": "phone_exposure",
      "provider_role": "signal_producer",
      "provider_method": "truecaller_sdk_verification",
      "endpoint_or_artifact": "Truecaller SDK OAuth endpoints and userinfo",
      "classification": "out_of_scope",
      "entity_types": ["phone", "account"],
      "gating_logic": "Requires explicit end-user consent inside apps; use only in a dedicated identity/verification module, not for phone exposure.",
      "citation_refs": ["https://docs.truecaller.com/truecaller-sdk", "https://docs.truecaller.com/truecaller-sdk/android/oauth-sdk-3.0.0/integration-steps/integrating-with-your-backend/fetching-user-token"],
      "notes": "Provides verified user profile and phone ownership signals via OAuth; not designed as a bulk reputation or spam-intel feed."
    },
    {
      "module": "phone_exposure",
      "provider_role": "signal_producer",
      "provider_method": "legacy_rest_api",
      "endpoint_or_artifact": "Historical Truecaller REST reverse lookup API",
      "classification": "out_of_scope",
      "entity_types": ["phone"],
      "gating_logic": "Do not integrate; documented by third parties as defunct and unsupported.",
      "citation_refs": ["https://findapis.com/en/api/truecaller", "https://stackoverflow.com/questions/72457697/is-there-any-api-from-trucaller-to-get-user-details"],
      "notes": "Historical REST API returned name, spam score, and True score for a number but has been shut down; modern integrations should ignore it."
    }
  ],
  "signal_contracts": [],
  "confidence_guidance": [
    {
      "module": "phone_exposure",
      "signal_type_or_use_case": "Enrich owned numbers with Number Management 'number details' metadata",
      "source_reliability": "High for configuration state (department, process, feature set, label, call_me_back, status) because it comes directly from your Truecaller for Business account; does not encode community spam perception.",
      "freshness_considerations": "Staleness depends on how often internal ops change number configurations vs how often you sync; API returns current database state each time it is called.",
      "corroboration_rules": "When correlating with exposure data from other providers, only attach Truecaller metadata when the exact E.164 phone number appears in the number-details response; never assume 'status' implies spam or safety.",
      "calibration_todo": "Define mapping from Truecaller metadata fields into your internal phone inventory model; decide sync frequency and caching; ensure number formatting is normalized before correlation."
    },
    {
      "module": "phone_exposure",
      "signal_type_or_use_case": "Future spam/reputation signals if Truecaller exposes spam status or score via official API",
      "source_reliability": "Likely strong because spam lists are built from large-scale user reports and behavioral metrics, but subject to normal community-intel noise and potential regional bias.",
      "freshness_considerations": "Spam metrics and stats described in the reverse-lookup UI use 60-day windows (calls made, spam reports, lookups, pickup rate) and live updates in the business console, implying that risk changes over days to weeks.",
      "corroboration_rules": "For high-severity decisions (blocks, security incidents), require at least one independent reputation source plus stability of spam status over a defined period; only treat a number as clearly abusive if spam indicators are high and consistent.",
      "calibration_todo": "If/when API fields become available, run a calibration study: map Truecaller spam scores and trends to your severity bands, measure false positives on customer-owned numbers, and tune time windows and thresholds before enabling automated alerts."
    }
  ]
}
```
