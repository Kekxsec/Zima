---
title: "output / social / accounts"
aliases: ["accounts output", "accounts signal registry"]
tags: [zima, research, outputs, signal-registry, social, accounts, graph_exclude]
type: provider_research_output
provider: accounts
provider_category: social
status: not_started
prompt_note: prompt.md
provider_folder: accounts.md
obsidianUIMode: preview
kind: artifact
llm_include: false
code_scope: backend
---
# Provider research: accounts for account_inventory

## API surface appendix

### Provider artefact availability and stability

The provider URL supplied for this integration, hosted on GitHub as `soxoj/accounts`, is currently not accessible and returns **HTTP 404 (Not Found)** when fetched (as of 23 March 2026). 

Because the primary/official repository is not accessible, the following implementation-critical items are **unavailable from official sources** for this research pass:

- confirmed CLI entrypoint names (if any)
- confirmed library import path and function signatures (e.g., `check(email, username)`)
- authenticated vs unauthenticated execution modes
- machine-readable output schema (JSON/CSV/text), exact field names, and error modes
- licensing terms and redistribution constraints

This repository unavailability is also consistent with the maintainer’s Python Package Index profile listing **only three published projects** (maigret, socid-extractor, osint-cli-tool-skeleton) and **no project named “accounts”**. 

### Confirmed endpoints, methods, or artefacts

Because the canonical repository/documentation is not accessible (404), there are **no confirmed endpoints/methods/artefacts** beyond the repository URL itself. 

|item|endpoint/method/artifact|purpose|supported entity_type(s)|auth/execution|response schema|response variants|field presence rules|citation_refs|
|---|---|---|---|---|---|---|---|---|
|Repository|`https://github.com/soxoj/accounts`|Unknown (repo not accessible)|unknown|unknown|unknown|unknown|unknown||

### Inferred interface pattern (not provider-specific; conditional)

The only implementation-grade, machine-readable schema that can be referenced from the maintainer’s ecosystem **without accessing the missing repo** is the output and optional server interface described in the maintainer’s “OSINT cli tool skeleton” template. This **does not prove** `accounts` used the same interface, but it provides a concrete pattern to reuse **if** you later recover `accounts` code and it matches this template.

The template documents:

- CLI mode that processes one-or-more “targets” and prints per-target results including “Value” and “Code”. 
- CSV output with headers `"Target","Value","Code"`. 
- JSON output as an array of objects, each with:
    - `input.value` (string)
    - `output` (array of `{ value: string, code: number }`) 
- A server mode that exposes an HTTP endpoint `/check` accepting a JSON body `{"targets": ["google.com", "yahoo.com"]}` and returning an array of the same `{input, output}` objects. 

If (and only if) `accounts` follows this pattern, then the _template-derived_ top-level schema would resemble:

- **Top-level**: JSON array
- **Per element**:
    - `input`: object
        - `value`: string (target)
    - `output`: array
        - items: object
            - `value`: string
            - `code`: integer (HTTP status or similar “result code”)

The template also implies common response variants:

- “hit”: `output` array length > 0 (at least one `{value, code}`)
- “no-hit”: `output` array empty (or “Results found: 0” in text output)
- network/service errors: may still yield an item with a non-2xx `code` (unclear how errors are represented beyond the numeric code) 

**Evidence status:** inferred (template only), not documented for `accounts`. 

### Reliability caveats relevant to “account existence” checkers

Even if `accounts` is restored, a key implementation risk for any account-existence checker is the prevalence of false positives and failure modes due to:

- naive verification (e.g., relying on redirects or status codes)
- bot protection, unexpected stubs, captchas, and regional restrictions/censorship
- frequent site changes that break checks unless the rules DB is kept current 

These caveats are discussed by the same maintainer in the context of username/account enumeration tooling generally; they should be treated as _risk assumptions_ until validated specifically for `accounts`. 

## Module mapping table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|account_inventory|signal_producer (stated), recommend “defer”|unknown (unverified; “check” is only a note)|`soxoj/accounts` repo URL (inaccessible, 404)|out_of_scope|unknown (notes suggest email, username)|**Hard gate:** do not integrate until (a) authoritative source code/docs are accessible and (b) deterministic machine-readable output schema is confirmed (JSON preferred). If recovered, additionally require per-site false-positive controls + retry/backoff + explicit “no-hit” representation.||As of 2026-03-23 the provider cannot be evaluated or consumed because the canonical repo is missing (404). No standalone signals should be emitted because no triggerable fields are documented/available.|

## Signal contract table

No standalone signals can be defined for this provider in the current state because the provider’s machine-readable outputs, field names, and “hit/no-hit/error” semantics are not available from official sources (repo returns 404). 

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Severity rules

Because there are **no signal contracts** (table is empty), there are no implementable severity rules for `modules/*/rules.py` in this pass. 

If the provider becomes available later, the severity calibration should follow your guidance that **account existence is usually not direct compromise** (often enrichment/low risk) unless the provider returns fields that directly evidence credential exposure, stealer logs, plaintext passwords, or similarly high-impact outcomes. This cannot be evaluated until the provider schema is known. 

## Confidence guidance

|module|signal_type_or_use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|account_inventory|account discovery enrichment (conceptual)|**Currently unusable**: canonical provider repo not accessible (404), so reliability cannot be assessed.  If restored, account discovery tools commonly face false positives due to stubs/captchas/geo restrictions and naive checks.|If restored, checks are highly per-site and decay quickly as websites change; require update cadence evidence (release cadence, rules DB updates, CI tests). General risk of staleness is described for namecheckers.|If restored: require corroboration by at least one independent method before elevating beyond enrichment (e.g., direct authenticated SaaS inventory, IdP logs, corporate email domain verification, or explicit account-ownership proof).|Re-run this research with accessible `accounts` docs/code. Extract exact JSON schema, enumerate error modes, define dedupe keys and safe gating. Add a “false positive suppression list” mechanism if the provider supports it (or implement at mapper layer).|

## Provider summary

### Strongest signal types

None can be asserted or implemented in this research pass because the provider’s official artefact (`soxoj/accounts`) is not accessible (404), preventing any field-level trigger logic or schema extraction. 

### What the provider should not be used for

Even if restored, an “account discovery” style provider should not be treated as evidence of:

- credential compromise
- breach/stealer-log presence
- authenticated account takeover

Unless (and only unless) the provider outputs **direct evidence fields** meeting your severity definitions (e.g., plaintext credentials), the appropriate use is typically inventory/enrichment rather than compromise signalling. At present, the provider’s fields are unknown. 

### API, auth, rate-limit, and licensing cautions

Auth, rate limits, and licensing are **unknown** because the repository is not available. 

Operationally, if the provider is later recovered and behaves like other public account/username checkers, expect:

- high susceptibility to false positives and transient failures from bot defences, captchas, censorship/geo-blocking, and site changes 
- the need for explicit retry/backoff and explicit “cannot determine” outcomes distinct from “no-hit” (design requirement; not currently documentable for `accounts`) 

### Recommended current Zima posture

Treat this provider as **deferred / out_of_scope for integration** in the current Zima stage, because there is no stable, machine-readable interface available to implement mappers and rules safely. 

If the repository is restored or you can supply an authoritative source snapshot (tagged release, commit archive, or internal mirror), this provider should likely be treated as **enrichment-first** for `account_inventory` unless its schema contains direct, high-severity evidence fields that match Zima’s calibration guide.

{
  "provider": "accounts",
  "provider_category": "social",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "account_inventory",
      "provider_method": "unknown",
      "endpoint_or_artifact": "https://github.com/soxoj/accounts",
      "classification": "out_of_scope",
      "entity_types": ["unknown"],
      "gating_logic": [
        "Do not integrate until official repository/docs are accessible and provide a deterministic machine-readable output schema (JSON preferred).",
        "If recovered and used, require explicit no-hit vs error semantics, retry/backoff, and local controls for false positives."
      ],
      "notes": [
        "As of 2026-03-23 the repository URL returns 404 (not accessible), so field-level triggers and evidence mapping cannot be derived."
      ]
    }
  ],
  "signal_contracts": [],
  "confidence_guidance": [
    {
      "module": "account_inventory",
      "signal_type_or_use_case": "account discovery enrichment (conceptual)",
      "source_reliability": "unknown (provider artefact not accessible as of 2026-03-23)",
      "freshness_considerations": "unknown (requires repo/docs). If restored, expect rapid staleness due to site changes and bot defences.",
      "corroboration_rules": [
        "If restored, corroborate any 'account exists' claim with an independent source before elevating beyond contextual enrichment."
      ],
      "calibration_todo": [
        "Re-run provider research when repo or an authoritative snapshot is available; extract exact schema, error modes, and safe mapper/rules logic.",
        "Implement a false-positive suppression mechanism if provider lacks one."
      ]
    }
  ]
}
