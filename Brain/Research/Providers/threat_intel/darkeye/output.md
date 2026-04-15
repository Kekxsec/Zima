---
title: "output / threat_intel / darkeye"
aliases: ["darkeye output", "darkeye signal registry"]
tags: [zima, research, outputs, signal-registry, threat_intel, darkeye]
type: provider_research_output
provider: darkeye
provider_category: threat_intel
status: complete
prompt_note: prompt.md
provider_folder: darkeye.md
obsidianUIMode: preview
kind: reference
llm_include: true
code_scope: backend
---

# DarkEye (Dark Web Mention Search API)

**Service:** https://darkeye.org
**CLI wrapper (Ringmast4r):** https://github.com/Ringmast4r/DarkEye
**Author:** DarkEye (service) / Ringmast4r (wrapper)
**Language:** Python
**Auth:** Unknown — API key details not documented in wrapper
**Free tier:** Appears to be free but severely limited (10 results max)

DarkEye is a **lightweight dark web mention search service** that checks if a URL or email address appears in dark web threat logs and forum mentions. The Ringmast4r CLI wrapper queries the darkeye.org API and returns tabulated results.

**Assessment:** This is the **weakest candidate** from the Ringmast4r portfolio. The 10-result limit, sparse documentation, and unclear API terms make it unreliable as a primary provider. Intelligence X covers the same ground with better coverage, documentation, and a proper SDK.

---

## A. Tool/API Surface Appendix

### CLI Interface

```bash
python darkeye.py -target url_or_email
```

**Input:** URL or email address as `-target` parameter.

### API Surface (inferred from code)

- Queries darkeye.org backend (exact endpoints undocumented)
- Returns up to 10 results
- Result categories: "Threat and logs" and "Mentions on the dark web"
- Output: Tabulated text (using `tabulate` library)

### Dependencies

```
requests
colorama
tabulate
```

### Known Limitations

- **10 results maximum** — severely limits coverage
- **No JSON output** — tabulated text only
- **No official API documentation** — no rate limits, no schema, no versioning
- **darkeye.org service stability unknown** — no SLA, no status page, no uptime history
- **No official SDK** — only Ringmast4r's wrapper

---

## Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|
| darkweb_identity_monitor | enrichment_only | dark_web_mention_search | darkeye.org API (undocumented) | enrichment_only | email, url | Requires email or URL. Only use if IntelX is unavailable or as a secondary corroboration source. | github.com/Ringmast4r/DarkEye README | 10-result limit severely constrains utility. |

---

## Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| darkweb_identity_monitor | darkweb_identity_monitor | darkeye | dark_web_mention_search | `darkweb_mention_found` | identity_exposure | medium | yes | High if result category is "Threat and logs" (active threat). Medium for general "mentions." | email | enrichment_finding | `results.length > 0` | `target`, `mention_type`, `result_text` | — | "Dark web mention found for {target}: {mention_type}." | inferred (no official schema) | README | Low-confidence signal due to sparse output and undocumented API. |

---

## Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|
| darkweb_identity_monitor | darkweb_mention_found | Low-Medium: darkeye.org is not a well-known or peer-reviewed OSINT service. Coverage, accuracy, and false positive rates are unknown. No published methodology. | Unknown: No timestamp data in results. No information on how frequently darkeye.org updates its index. | MUST corroborate with Intelligence X or HIBP before surfacing to user. Do not use DarkEye findings alone as evidence. | Evaluate: run parallel searches against IntelX and compare hit rates. If DarkEye consistently returns subset of IntelX results, it adds no value. |

---

## Provider Summary

### What It Could Do

- Quick, lightweight dark web mention check for an email/URL
- Potential secondary corroboration source alongside Intelligence X

### Why It's Weak

- **10-result cap** — unusable for any serious investigation
- **No documentation** — API schema, rate limits, terms of service all unknown
- **No SDK** — only a basic CLI wrapper with text output
- **Unknown service reliability** — darkeye.org has no public SLA or track record
- **Fully superseded by Intelligence X** — IntelX has official SDK, documented API, 90-result free tier, dark web bucket filtering, and is a known/trusted OSINT platform

### Recommendation

**Defer.** Intelligence X covers everything DarkEye does, with better documentation, higher limits, and a proper SDK. Only revisit DarkEye if darkeye.org publishes an official API with structured output and improved coverage.

### Current Zima Stage Fit

- **Phase:** Deferred / not recommended
- **Classification:** `enrichment_only` (weak)
- **Action:** Do not implement. Use Intelligence X for dark web monitoring instead.

---

# Structured JSON

```json
{
  "provider": "darkeye",
  "provider_category": "threat_intel",
  "provider_role": "enrichment_only",
  "source": "https://darkeye.org",
  "requires_api_key": "unknown",
  "requires_network": true,
  "result_limit": 10,
  "launch_fit": "deferred",
  "superseded_by": "intelx",
  "module_mappings": [
    {
      "module": "darkweb_identity_monitor",
      "provider_role": "enrichment_only",
      "provider_method": "dark_web_mention_search",
      "classification": "enrichment_only",
      "entity_types": ["email", "url"],
      "gating_logic": "Only use if IntelX is unavailable",
      "notes": "10-result limit. No official API docs. Superseded by Intelligence X."
    }
  ],
  "signal_contracts": [
    {
      "signal_type": "darkweb_mention_found",
      "severity": "medium",
      "severity_is_conditional": true,
      "finding_kind": "enrichment_finding",
      "evidence_status": "inferred"
    }
  ],
  "confidence_guidance": [
    {
      "source_reliability": "Low-Medium (unknown service, no published methodology)",
      "corroboration_rules": "MUST corroborate with IntelX or HIBP before surfacing",
      "calibration_todo": "Evaluate parallel hit rate against IntelX"
    }
  ]
}
```
