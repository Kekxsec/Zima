---
tags: [zima, mvp, signal-registry, stage-06, handoff]
created: 2026-03-21
updated: 2026-03-21
---

← [[../Zima|Zima]] · [[MVP Next Steps|Next Steps]] · [[stage-06-jobs-api-orchestration|Stage 6]]

# Pre-Stage-6 Signal Registry Handoff

This note defines the full bridge between provider research and Stage 6. Research output is not the final handoff by itself. Stage 6 should begin only after the research has been synthesized into a canonical signal contract that the codebase can implement.

---

## Goal

Turn provider-level research outputs into a single implementation-ready handoff for:

- provider client work
- module `rules.py` decisions
- module `mapper.py` signal creation
- correlation rule planning
- score calculator planning
- remediation mapping
- Stage 6 orchestration registration

---

## Exit Criteria

Stage 6 is ready to begin when all of the following are true:

- priority provider research packets are complete for the current build tier
- a canonical `signal-registry.md` exists and is no longer a loose collection of provider notes
- signal names, categories, entity types, and source modules are normalized
- conditional severity logic is frozen for known edge providers
- confidence has a documented temporary implementation policy
- the implementation queue for providers and modules is explicit

If those conditions are not met, the project is still in research synthesis, not Stage 6 readiness.

---

## Phase 1: Finish Priority Research Packets

Complete the provider research outputs in build order.

### Tier 1 first

- `breach/` providers feeding `breach_monitor`, `credential_exposure`, and `stealer_log_exposure`
- `reputation/emailrep`
- `social/epieos`
- `social/accounts`

### Required output per provider

- API surface appendix
- module mapping table
- signal contract table
- confidence guidance
- implementation notes with citations

### Rules

- do not research all 150+ providers before synthesis
- do not create standalone signals for utility-only or deferred providers
- keep module-level decisions separate when a provider feeds multiple modules

---

## Phase 2: Synthesize the Canonical Signal Registry

This is the immediate next step after the deep research runs.

Create or update a single `signal-registry.md` that consolidates all provider outputs into one master registry.

### What the canonical registry must contain

- `module`
- `source`
- `provider`
- `provider_method`
- `signal_type`
- `category`
- `severity`
- `severity_is_conditional`
- `conditional_rule`
- `entity_type`
- `trigger_condition`
- `evidence_fields`
- `summary_template`
- `citation_refs`
- `notes`

### Synthesis tasks

- merge duplicate signals emitted by different providers
- choose one canonical signal name per concept
- split signals that look similar but have materially different severity or meaning
- remove enrichment-only rows from the canonical signal list
- mark utility-only and deferred providers as non-signal sources
- normalize category names to the architecture domains
- normalize `source` to the module name, never the endpoint name

### Specific reviews to perform

- naming review for duplicates and antipatterns
- category review against the domain breakdown
- entity-type review against the signal model
- summary review: every signal should be describable in one sentence

---

## Phase 3: Freeze Decision Rules

Before implementation starts, freeze the rules the code will rely on.

### Severity decisions

Lock the final severity logic for all signals in the current tier.

### Conditional providers

These require explicit final rules before coding:

- `breachdirectory`
- `greynoise`
- `virustotal`
- `threatjammer`
- `honeypot`

### Confidence policy

Do not block implementation on perfect confidence calibration.

Adopt a temporary policy such as:

- use provider confidence only as an input, not as final truth
- map authoritative, well-documented sources to provisional `high`
- map noisy or stale feeds to provisional `medium` or `low`
- add calibration notes for later adjustment after real scan volume exists

### Evidence contract

Freeze which raw provider fields must survive into signal `evidence` for:

- deduplication
- remediation context
- auditability
- future confidence calibration

---

## Phase 4: Build the Implementation Queue

Convert the canonical registry into a concrete coding queue.

### For each provider

- provider folder path
- endpoints to implement
- schema models required
- rate-limit and billing cautions
- authentication requirements
- test fixtures needed

### For each module

- module path
- required entity types
- signal rows it owns
- severity rule helpers needed
- mapper logic needed
- evidence payload shape
- open questions blocking implementation

### For downstream layers

- correlation rules to add after new signals land
- score calculators to update
- remediation playbooks to map
- Stage 6 orchestrator registration requirements

---

## Phase 5: Prepare the First-Wave Build Plan

Do not try to schedule every researched provider at once.

### Start with the highest-value additions

- identity and breach expansion beyond HIBP
- the next module/provider pairs that materially improve the Core tier

### Build-plan output

For the first implementation wave, define:

1. provider client and schema work
2. module rules work
3. module mapper work
4. tests for signal creation
5. correlation updates
6. scoring updates
7. remediation updates

This preserves the architecture rule:

`providers -> modules -> signals -> correlation -> scoring -> remediation`

Actual coding can then begin in parallel with, or immediately after, the Stage 6 kickoff depending on what is most efficient.

---

## Phase 6: Stage 6 Readiness Check

Before beginning Stage 6 orchestration work, confirm:

- the canonical signal registry exists
- first-wave module ownership is clear
- signal types and categories are stable enough not to churn the API contract immediately
- remediation mappings for new critical/high signals are known
- score categories for the first-wave modules are defined

If those checks pass, Stage 6 can start with confidence.

---

## Deliverables Before Stage 6

Minimum required artifacts:

- provider research outputs for current priority providers
- canonical `signal-registry.md`
- frozen conditional severity decisions
- provisional confidence policy
- implementation queue for providers/modules
- first-wave build plan
- list of follow-on correlation, scoring, and remediation changes

Recommended artifacts:

- `implementation-matrix.md` or equivalent ticket list
- per-module test cases derived from the registry
- naming review log for merged or renamed signals

---

## What Happens Immediately After Research

The next step after deep research is:

`provider research outputs -> canonical registry synthesis -> implementation queue -> Stage 6-ready handoff`

Not:

`provider research outputs -> immediately start Stage 6`

Stage 6 is an orchestration and API stage. It needs a stable enough signal contract underneath it.

---

## See Also

- [[MVP Next Steps]] — live project priorities
- [[../Research/Signal Research Guide|Signal Research Guide]] — methodology for designing signals
- [[../Research/Provider Module Map|Provider Module Map]] — provider to module ownership
- [[../Research/Extending the Platform|Extending the Platform]] — implementation sequence after the handoff
- [[stage-06-jobs-api-orchestration]] — the next MVP stage once the handoff is complete
