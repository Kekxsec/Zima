---
title: "prompt / threat_intel / leakix"
tags: [zima, research, providers, threat_intel, leakix]
type: provider_research_prompt
provider: leakix
status: complete
---

# Research Prompt: LeakIX

Research the LeakIX API (https://leakix.net) as an exposed-services and data leak search provider for Zima.

Focus on: REST API endpoints (search, host lookup, subdomains), query scopes (leak, service), response schema, free tier limits, official Python client, domain ownership gating, stale data risks.

Classification target: direct_signal_input (infrastructure exposure)
Module target: infrastructure_exposure, data_exposure
Signal targets: exposed_service_found, exposed_service_no_auth
