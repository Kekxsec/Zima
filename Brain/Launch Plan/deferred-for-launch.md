---
title: "deferred for launch"
tags: [zima, research, providers, launch, deferred]
type: provider_launch_deferred
created: 2026-03-22
updated: 2026-04-15
---

[[./_index|Provider Launch Plan]] · [[../Research/Providers/_index|Provider Hubs]]

# Deferred For Launch

These provider groups should stay out of the main launch track unless a narrow exception clearly supports the consumer audit flow.

## Defer As Default

- [[../Research/Providers/domain/domain|domain]]
- [[../Research/Providers/ip/ip|ip]]
- [[../Research/Providers/threat_intel/threat_intel|threat_intel]]
- [[../Research/Providers/cloud/cloud|cloud]]
- [[../Research/Providers/crypto/crypto|crypto]]
- [[../Research/Providers/content_analysis/content_analysis|content_analysis]]

## Defer Most Tooling In These Areas

- network and Wi-Fi inspection
- broad web and domain exposure discovery
- infrastructure and cloud posture
- secrets and sensitive data exposure
- attack-surface enumeration for unmanaged external assets

## Post-Launch AI Features

### Local LLM Classification Layer

A private self-hosted model (Llama 3.x 8B or similar via Ollama) as a confidence and disambiguation layer inside the email account identifier pipeline.

**Intended role (narrow):**
- Is this sender a true account service or newsletter/marketing?
- Do these domains belong to the same product/vendor?
- Is this message stream transactional or promotional?
- Is this service safe to treat as a password-manager candidate?

**Not the sole authority.** Acts as a rescoring layer on top of: rules -> headers -> service knowledge base -> model -> human review.

**Why deferred:**
- Cannot tune or evaluate the model before real-world misclassification data exists
- The rule-based pipeline must ship first and accumulate edge cases
- Infrastructure overhead (Ollama on Railway CPU: 3-10s inference, acceptable for background but unnecessary pre-launch)
- Shipping a classification model before knowing what it needs to fix is backwards

**Prerequisites before building:**
1. Rule-based pipeline is live and producing account inventory
2. At least one batch of real inbox data has been processed
3. Misclassification examples are catalogued
4. Confidence score gaps are identified from production output

**Architecture note:** implement as a pipeline component in the module layer, not a provider. The rule pipeline should emit confidence scores and an `ambiguous` flag to give the model clean, scoped inputs.

**Poor use cases (never):** fully autonomous destructive actions, unsubscribing without review, changing login identities without supervision, irreversible account actions from low-confidence evidence.

## Exception Rule

Pull a deferred provider into launch only if it directly improves one of these:

1. owned identity exposure detection
2. likely account and service discovery
3. device baseline findings
4. browser baseline findings
5. user-facing remediation guidance
