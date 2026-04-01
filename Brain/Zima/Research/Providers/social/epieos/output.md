---
title: "output / social / epieos"
aliases: ["epieos output", "epieos signal registry"]
tags: [zima, research, outputs, signal-registry, social, epieos, graph_exclude]
type: provider_research_output
provider: epieos
provider_category: social
status: not_started
prompt_note: prompt.md
provider_folder: epieos.md
obsidianUIMode: preview
---


# Zima provider research for epieos

## API Surface Appendix

### Executive constraint

Across the publicly accessible epieos pages, there is **no published API reference, OpenAPI/Swagger spec, request/response schema, or example API payloads** suitable for implementation-grade field mapping. The only official, explicit indication that a programmatic API exists is the **“API access”** inclusion in the **custom (enterprise) plan**. 

Separately, the epieos General Terms and Conditions explicitly prohibit using “a robot or automatic query system” when accessing and using the platform, which is a significant constraint for any attempt to integrate by scraping or reverse-engineering the interactive web product. 

Because your requirements demand “exact trigger condition using actual API field names” and “do not invent field names”, **no signal contracts can be safely finalised** until you obtain the official custom-plan API documentation (or a signed integration contract that defines schema). 

### Relevant endpoints, methods, and artefacts (as documented publicly)

**1) Web platform capability — reverse lookup (email)**

- **Endpoint / path:** unknown (interactive web platform; no public API base URL or path published). 
- **Purpose:** reverse lookup “email” to uncover social network profiles and associated OSINT context. 
- **Supported entity_type(s):** email (explicit); phone is also a first-class search input in the platform marketing and terms, but is a separate capability. 
- **Auth / execution requirements:**
    - The Terms define “Visitor Services” (usable without signing in), “Member Services” (requires sign-in), and “Subscription Services” (paid; requires sign-in). 
    - The sign-in flow is a passwordless email “magic link” flow. 
- **Documented output content (UI-level, not API field names):**
    - epieos states that when an email (or phone) is searched, it “displays information obtained from certain publicly available sources” and performs “no verification”. 
    - The Maltego Transform Hub description claims the reverse-email lookup can surface items such as a person’s username, location, Google Maps reviews, name, activity history, profile creation date, and PGP key. 
- **Always-present vs optional fields:** unknown (no schema published). 
- **Response variants:** (all unknown; no official payloads published)
    - successful hit: unknown structure; described as “display” of OSINT results. 
    - successful no-hit: unknown.
    - partial/limited result: likely exists in free/visitor tiers (“limited results” vs subscription), but no field-level mechanism is documented publicly. 
    - errors: interactive experience includes CAPTCHA considerations (“Eased captcha”, “Lightest captcha”), suggesting automation friction; no error schema documented. 
- **Implementation caution:** do **not** automate by scraping; the Terms prohibit robot/automatic query systems. 

**2) Web platform capability — reverse lookup (phone)**

- **Endpoint / path:** unknown (interactive web platform). 
- **Purpose:** reverse lookup “phone number” in the same platform. 
- **Supported entity_type(s):** phone. 
- **Auth / execution requirements:** same tiering model (visitor/member/subscription) as above. 
- **Output fields:** unknown (no published schema). 

**3) Platform module — “Email Checker” (account existence / registration check)**

- **Endpoint / path:** unknown. 
- **Purpose:** verify whether an email address exists / is registered across multiple websites. 
- **Supported entity_type(s):** email. 
- **Documented mechanics / provenance:**
    - Maltego’s description states epieos “integrates an improved Holehe” to search over “120 websites” and verify whether an email is registered. 
    - epieos’ own pricing page lists “Email Checker (+200 sites)”. These two public sources imply coverage but conflict on exact counts; treat coverage as **tier/version dependent** until confirmed in official API docs. 
- **Response shape and field names:** unknown (no published schema). 
- **Notes on usage constraints:** automated checking can be interpreted as high-volume querying; the Terms explicitly require “reasonable volume” and prohibit robot/automatic query systems for platform access. 

**4) Platform module — “Phone Checker”**

- **Endpoint / path:** unknown. 
- **Purpose:** not described in public docs beyond being listed as a module (“Phone Checker”). 
- **Supported entity_type(s):** likely phone, but not documented beyond the module name. 
- **Response shape and field names:** unknown. 

**5) Enterprise artefact — custom plan “API access”**

- **Endpoint / path:** unknown (no base URL, auth scheme, or schema publicly documented). 
- **Purpose:** programmatic integration and “private module access” for enterprise-scale requesters. 
- **Auth requirements / rate limits / error model:** unknown (must be obtained from vendor documentation delivered under the custom plan). 

**6) Authentication endpoint — sign-in**

- **Endpoint / path:** `https://epieos.com/auth/signin` (interactive web sign-in). 
- **Purpose:** passwordless sign-in using an emailed “magic link”. 
- **Requirements:** the sign-in form includes confirmations that the user is of legal age and acting in a professional/business capacity, and acceptance of Terms. 

**7) Legal / compliance artefacts relevant to implementation**

- **Terms / usage constraints:** includes (a) business-only use positioning, (b) no-robot/automatic query restriction, (c) “not logged” searches/results statement, and (d) lack of verification and lack of warranty on displayed information. 
- **Privacy policy:** states the controller is “EPIEOS SAS” (registered office in Paris) and notes data transfers can occur outside the European Economic Area for anti-bot purposes (hCaptcha). 
- **DPA:** enumerates categories of processed data including “magic link history” and “search results,” and lists subprocessors including OVHcloud and Brevo, and hCaptcha’s operator. 

## Module Mapping Table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|username_exposure|signal_producer|email_checker|Web platform module “Email Checker” (interactive; path unknown)|out_of_scope|email|Do **not** automate via scraping or reverse-engineered endpoints; only integrate once official custom-plan API schema is obtained.||Public docs describe existence-checking using an “improved Holehe” and coverage claims (“120 websites” vs “+200 sites”) but provide no field-level schema. Treat as non-integratable until API is contracted.|
|username_exposure|signal_producer|email_checker_api|Custom plan API (exact endpoint unknown)|direct_signal_input|email, phone|Require custom-plan contract + official API docs that specify: request params, per-site result objects, and “limited results” indicators (tier/credit enforcement).||The only official, explicit API mention is “API access” in the custom plan. Without docs, mapper/rules cannot be written safely.|
|alias_correlation|signal_producer|reverse_lookup_email|Web platform reverse email lookup (interactive; path unknown)|out_of_scope|email|Do **not** scrape; obtain official API contract first.||UI-level claims include discovering usernames and social profiles; however, epieos also disclaims verification of displayed data. No API schema available publicly.|
|alias_correlation|signal_producer|reverse_lookup_email_api|Custom plan API (exact endpoint unknown)|direct_signal_input|email, phone|Only emit correlation outputs if API returns stable identifiers (e.g., per-platform profile URLs/IDs) and includes enough evidence to deduplicate reliably.||Terms also state epieos does not log queries/results; Zima should persist raw results for audit/dedup if integration proceeds.|

## Signal Contract Table

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

No standalone signal contracts are emitted in this research pass because **epieos does not publish a usable API schema publicly**, and your requirements prohibit guessing field names or trigger conditions. The only official reference to an API is “API access” in the custom plan, with no documented endpoints or response fields. 

## Confidence Guidance

|module|signal_type_or_use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|username_exposure|Email Checker results used to identify where an email may be registered|Vendor-adjacent description claims “improved Holehe” and email registration verification, but there is no public schema and epieos disclaims verification of displayed info; treat as “useful lead” until validated per-site.|epieos marketing emphasises “real-time” social network sourcing; however, account existence can change rapidly and “limited results” may differ by subscription tier.|Corroborate high-impact sites by direct confirmation via first-party workflows (enterprise admin logs, IdP/SaaS discovery, or user attestation). Only accept as “confirmed” after second-source confirmation.|Measure per-site false-positive and false-negative rates; require epieos API docs to surface per-module evidence. Track deltas over time to detect drift.|
|alias_correlation|Reverse email/phone lookup results used to link discovered usernames to an email/phone entity|epieos positions results as pulled from publicly available sources and Maltego’s listing asserts direct sourcing from social media platforms, but epieos explicitly states no verification and no warranty.|Claimed “fresh and unaltered” sourcing suggests low staleness for profiles that still exist, but correlation can decay (renames, deleted profiles). Require timestamps if provided by API; otherwise treat as time-unknown.|Corroborate by verifying profile URL accessibility and matching stable platform identifiers (profile IDs) when possible. Use additional providers for cross-platform pivoting rather than trusting a single correlation.|Require the API to return: per-platform profile URL/ID, match basis, and a confidence/quality indicator. Implement dedup on stable IDs, not usernames.|

## Provider Summary

1. **Strongest signal types (practically: strongest module use-cases)**
    epieos is strongest as a **pivot/enrichment provider** for identity/OSINT investigations starting from an email address or phone number, where the value is discovering associated social profiles and identity artefacts (usernames, profile creation date, etc.) and discovering where an email may be registered. 

2. **What the provider should not be used for**
    epieos should not be treated as a definitive source of compromise, breach, credential exposure, or malicious infrastructure by itself: the Terms explicitly state epieos performs **no verification** of displayed information and provides **no warranty** about truthfulness/accuracy/completeness or source availability. 
    For Zima specifically, avoid promoting “profile discovered” or “account exists” into high-severity signals without additional evidence of abuse/compromise, because the publicly described outputs are primarily OSINT presence and linkage, not incident indicators. 

3. **API/auth/rate-limit/licensing implementation cautions**

    - **API availability is plan-gated:** the pricing page lists “API access” only for the custom plan; public docs do not provide endpoints or schemas. 
    - **Automation constraint:** the Terms prohibit using “a robot or automatic query system” for platform access; do not ship a scraper-based connector. 
    - **Quota and friction indicators:** the Osinter plan is described as “30 full-access requests / month,” and the plans mention CAPTCHA/watermark differences, implying operational friction and hard rate/credit controls. 
    - **Evidence retention:** epieos states requests/results are “not logged” by epieos; Zima must persist raw responses for audit, deduplication, and remediation workflows when you have a sanctioned API feed. 
    - **Data processing and subprocessors:** the DPA indicates “search results” and “magic link history” are processed and lists subprocessors (notably hosting/email/auth providers). This matters for your procurement and DPIA posture. 

    **Mapper/rules build notes (actionable despite schema gaps):**

    - **Provider client vs module mapper:** keep an `epieos_client` thin and schema-agnostic until you have the official API; store the full raw JSON blob returned by API calls (verbatim) and pass it into module mappers. 
    - **Null/no-hit behaviour:** treat “no results” and “partial results due to tier/credits” as distinct states; this requires explicit API fields (unknown today). Until provided, do not emit signals—only attach enrichment under an “unknown completeness” flag. 
    - **Deduplication:** plan to deduplicate on stable per-platform identifiers (profile IDs/URLs) if the API provides them; avoid dedup on usernames alone due to rename churn. (API requirement; not publicly documented). 
4. **How epieos should be treated in the current Zima stage**
    epieos should be treated as **deferred for automated signal production** until you have sanctioned custom-plan API access and its official schema; without that, it is effectively an interactive OSINT tool whose use is constrained by anti-automation terms. 
    Once the API schema is obtained, epieos can become **a signal-producing feed** for low-severity, context-first identity/alias findings (and/or a correlation input), but that cannot be implemented safely without field-level documentation.

{
  "provider": "epieos",
  "provider_category": "social",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "username_exposure",
      "provider_method": "email_checker",
      "endpoint_or_artifact": "web_platform_email_checker_module",
      "classification": "out_of_scope",
      "entity_types": ["email"],
      "gating_logic": "Do not scrape or automate the web platform; integrate only with official custom-plan API documentation that specifies request/response schema and completeness indicators.",
      "citation_urls": [
        "https://epieos.com/pricing",
        "https://epieos.com/terms",
        "https://www.maltego.com/transform-hub/epieos/"
      ],
      "notes": "Public sources describe existence-checking and large coverage counts, but no API payload schema is publicly available. Terms prohibit robot/automatic query systems for platform use."
    },
    {
      "module": "username_exposure",
      "provider_method": "email_checker_api",
      "endpoint_or_artifact": "custom_plan_api_unknown",
      "classification": "direct_signal_input",
      "entity_types": ["email", "phone"],
      "gating_logic": "Requires enterprise custom plan contract and official API docs. Must include per-site results, evidence basis, tier/credit limitation flags, and stable identifiers for dedup.",
      "citation_urls": [
        "https://epieos.com/pricing"
      ],
      "notes": "Only official public indication of API is 'API access' in the custom plan."
    },
    {
      "module": "alias_correlation",
      "provider_method": "reverse_lookup_email",
      "endpoint_or_artifact": "web_platform_reverse_lookup_email",
      "classification": "out_of_scope",
      "entity_types": ["email"],
      "gating_logic": "Do not automate the interactive platform; require official API. If used manually, treat outputs as analyst enrichment only (no automated signals).",
      "citation_urls": [
        "https://epieos.com/",
        "https://epieos.com/terms",
        "https://www.maltego.com/transform-hub/epieos/"
      ],
      "notes": "UI-level descriptions mention usernames/profile attributes but no public schema. Terms disclaim verification and prohibit automation."
    },
    {
      "module": "alias_correlation",
      "provider_method": "reverse_lookup_email_api",
      "endpoint_or_artifact": "custom_plan_api_unknown",
      "classification": "direct_signal_input",
      "entity_types": ["email", "phone"],
      "gating_logic": "Requires official API docs that provide per-platform profile identifiers/URLs, match basis, and completeness flags to support safe correlation and dedup.",
      "citation_urls": [
        "https://epieos.com/pricing"
      ],
      "notes": "No public endpoint paths or response fields are available; cannot write mapper/rules until contract docs are received."
    }
  ],
  "signal_contracts": [],
  "confidence_guidance": [
    {
      "module": "username_exposure",
      "signal_type_or_use_case": "email_checker (account registration presence)",
      "source_reliability": "Mixed: third-party integration description asserts verification mechanics, but epieos terms disclaim verification/warranty; treat as investigative lead pending corroboration.",
      "freshness_considerations": "Account existence changes; free vs paid tiers may mask results. Prefer API fields that expose timestamps and completeness flags.",
      "corroboration_rules": "Confirm important findings via first-party evidence (IdP/SaaS admin logs, user attestation, or platform-specific stable identifiers).",
      "calibration_todo": "Measure per-site accuracy; require API to return evidence basis and limitation flags."
    },
    {
      "module": "alias_correlation",
      "signal_type_or_use_case": "reverse email/phone lookup (email/phone -> social profiles/usernames)",
      "source_reliability": "Useful for linkage but not authoritative without verification; epieos explicitly does not verify displayed data.",
      "freshness_considerations": "Profiles can be deleted/renamed; correlation should be timestamped where possible.",
      "corroboration_rules": "Validate profile URLs/IDs directly; cross-check with at least one additional provider before treating as confirmed identity linkage.",
      "calibration_todo": "Require stable identifiers (profile IDs/URLs) and match basis; dedup on stable IDs, not usernames."
    }
  ]
}
