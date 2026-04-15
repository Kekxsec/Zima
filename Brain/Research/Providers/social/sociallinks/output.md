---
title: "output / social / sociallinks"
aliases: ["sociallinks output", "sociallinks signal registry", "social links api"]
tags: [zima, research, outputs, signal-registry, social, sociallinks]
type: provider_research_output
provider: sociallinks
provider_category: social
status: complete
prompt_note: prompt.md
provider_folder: sociallinks.md
obsidianUIMode: preview
kind: reference
llm_include: true
code_scope: backend
---

# Social Links API

**Source:** https://github.com/soxoj/sociallinks-api
**Author:** soxoj (same author as maigret and socid-extractor)
**Type:** Commercial REST API — trial access on request
**Docs:** Postman collection + Read The Docs reference
**Auth:** API key (`API_KEY` env var) + API domain (`API_DOMAIN` env var)
**Coverage:** 500+ data sources — social media, blockchains, messengers, Dark Web

Social Links is a **commercial intelligence API** built on the same OSINT expertise as the soxoj open-source ecosystem. It provides deep cross-platform identity resolution including face/name-based account discovery, social media post analysis with LLM preprocessing, and geolocation-based collection.

**Important:** This is a paid/enterprise product. Trial access requires contacting Social Links directly. No public pricing or free tier. Do not treat as a launch-day provider — classify as **post-launch / enterprise tier**.

---

## A. API Surface Appendix

### Authentication

```python
import os
API_DOMAIN = os.environ["API_DOMAIN"]  # e.g. api.sociallinks.io
API_KEY = os.environ["API_KEY"]
```

All requests use API key authentication. Exact header name not documented publicly — refer to Postman collection provided at trial activation.

### Endpoint Categories

#### 1. Face/Name-Based Account Discovery

```python
# face_search_example.py (from repo)
# Search for accounts by name and optionally a photo
# across 500+ social media platforms
```

- Input: person name, optional photo
- Output: matched social media accounts with profile URLs
- Use case: find all social accounts for a person using name + photo correlation

#### 2. Post Analysis

```python
# post_analysis_example.py (from repo)
# Retrieve posts by username, hashtag, or keyword
# Optional LLM preprocessing: sentiment, translation, summarization
```

- Input: username, hashtag, or keyword
- Output: post metadata and content with optional LLM-processed fields
- Use case: threat monitoring, content analysis, geolocation extraction

#### 3. Data Sources

- Social media: 500+ platforms
- Blockchains: cryptocurrency address/transaction data
- Messengers: chat platform data
- Dark Web: onion site data

### Output Schema

Not publicly documented. Structured JSON responses (inferred from repo examples). Schema requires official API documentation provided at trial activation.

### Rate Limits

Not publicly documented. Trial plan likely has conservative limits.

---

## Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|
| username_exposure | enrichment_only | face_name_account_discovery | REST API — face/name search endpoint | enrichment_only | username, person_name | Requires trial/commercial API contract. Gate behind enterprise feature flag. Not available for standard launch. | github.com/soxoj/sociallinks-api | Post-launch only. Requires signed contract and DPA. |
| account_inventory | enrichment_only | post_analysis | REST API — post retrieval endpoint | enrichment_only | username | Same gating. | github.com/soxoj/sociallinks-api | LLM preprocessing (sentiment, translation) is an add-on cost. |

---

## Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| — | — | sociallinks | — | — | — | — | — | — | — | — | — | — | — | — | — | — | No signal contracts definable without official API schema. Defer until trial documentation obtained. |

---

## Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|
| username_exposure | cross-platform_account_discovery | Unknown — no published accuracy data. Commercial product with incentive to overstate coverage. | Unknown — depends on platform data freshness in their index. | Corroborate found accounts with independent maigret/whatsmyname results. | Evaluate during trial: precision/recall vs maigret on known test identities. |

---

## Provider Summary

### Strongest Potential Use Cases

- **Face-based identity correlation** — Finding accounts across platforms using a photo. No open-source equivalent at this quality level.
- **Enterprise identity graph** — 500+ platform coverage far exceeds open-source tools.
- **Dark web + blockchain cross-referencing** — Natively includes sources that require separate tools in the open-source stack.

### What Not To Use It For

- Do not use for standard Zima launch — requires commercial contract, trial approval, and unknown pricing.
- Do not define signal contracts until official API schema is obtained.
- Do not treat as a drop-in replacement for maigret/whatsmyname — different capability tier and cost model.

### Implementation Cautions

- **No public API schema** — Cannot implement until trial documentation received.
- **Commercial contract required** — Must negotiate DPA/data processing terms before use.
- **Cost model unknown** — Per-query pricing or monthly subscription; unknown at research time.
- **GDPR/DPA considerations** — Cross-platform identity aggregation at this depth requires careful legal review.
- **soxoj ecosystem fit** — Same author as maigret/socid-extractor. Likely shares OSINT methodology; commercial tier with broader coverage.

### Current Zima Stage Fit

- **Phase:** Post-launch / enterprise tier
- **Classification:** `enrichment_only` (pending schema)
- **Action required:** Contact Social Links for trial access and API documentation before any implementation work.

---

# Structured JSON

```json
{
  "provider": "sociallinks",
  "provider_category": "social",
  "provider_role": "enrichment_only",
  "source": "https://github.com/soxoj/sociallinks-api",
  "requires_api_key": true,
  "api_access": "trial_on_request",
  "coverage": "500+ sources including social, blockchain, messengers, dark web",
  "launch_fit": "post_launch_enterprise",
  "module_mappings": [
    {
      "module": "username_exposure",
      "provider_role": "enrichment_only",
      "provider_method": "face_name_account_discovery",
      "classification": "enrichment_only",
      "entity_types": ["username", "person_name"],
      "gating_logic": "Enterprise feature flag; requires commercial contract",
      "notes": "Post-launch only"
    }
  ],
  "signal_contracts": [],
  "confidence_guidance": [
    {
      "module": "username_exposure",
      "signal_type_or_use_case": "cross_platform_account_discovery",
      "source_reliability": "Unknown — evaluate at trial",
      "freshness_considerations": "Unknown",
      "corroboration_rules": "Cross-check with maigret/whatsmyname",
      "calibration_todo": "Run precision/recall evaluation during trial period"
    }
  ]
}
```
