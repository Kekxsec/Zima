---
title: "prompt / threat_intel / intelx"
tags: [zima, research, providers, threat_intel, intelx]
type: provider_research_prompt
provider: intelx
status: complete
kind: artifact
llm_include: false
code_scope: backend
---

# Research Prompt: Intelligence X

Research the Intelligence X API (https://intelx.io) as a breach context enrichment and dark web monitoring provider for Zima.

Focus on: Official Python SDK, search API (selectors: email, domain, IP, username, phone, bitcoin), phonebook API, bucket types (pastes, leaks, darknet, whois, documents, web), free tier limits (90 results), response schema, data sensitivity handling.

Classification target: enrichment_only (breach context), direct_signal_input (dark web mentions)
Module target: breach_monitor, darkweb_identity_monitor, username_exposure
Signal targets: breach_context_found, darkweb_mention_found
