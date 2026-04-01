---
title: "launch provider research plan"
tags: [zima, research, launch, providers, plan, graph_exclude]
type: launch_provider_research_plan
created: 2026-03-22
updated: 2026-03-22
---

[[../Zima|Zima]] · [[research|Research]] · [[launch-focus-providers|Launch Focus Providers]]

# Launch Provider Research Plan

This is the execution plan for the launch research phase.

The launch product direction is:

- guided consumer security audit
- passive identity and account discovery first
- local device and browser baseline second
- remediation, education, and tooling onboarding throughout

## Current State

- every launch-focus provider folder exists
- every launch-focus provider already has:
  - `<provider>.md`
  - `prompt.md`
  - `output.md`
- all audited launch-focus `output.md` files are still `status: not_started`
- API/search-oriented prompts are mostly already in the full implementation-grade format
- many launch-relevant `tools/*` and browser/cloud-enrichment prompts were still short-form and needed completion

## Research Goal

Before more implementation, finish research for the launch provider set so you can build:

1. a canonical launch signal registry
2. a first-wave implementation queue
3. the remediation and onboarding flows tied to real findings

## Success Criteria

For each launch-focus provider:

- `prompt.md` is implementation-grade
- `output.md` is completed
- target module(s) are explicit
- classification is explicit:
  - `direct_signal_input`
  - `enrichment_only`
  - `utility_only`
  - `out_of_scope`
- signal contracts are explicit where justified
- evidence fields are frozen
- rate-limit / auth / licensing constraints are captured

## Provider Waves

See [[launch-research-dashboard|Launch Research Dashboard]] for the current wave breakdown, per-provider status, and next actions.

## Exact Order To Work

Use this order unless a provider becomes blocked by licensing or docs access:

1. `hibp`
2. `accounts`
3. `osquery`
4. `browser_extension_detector`
5. `get_browser_extension_info`
6. `dehashed`
7. `leakcheck`
8. `breachdirectory`
9. `emailrep`
10. `epieos`
11. `holehe`
12. `maigret`
13. `whatsmyname`
14. `posture`
15. `macos_native`
16. `windows_native`
17. `linux_native`
18. `malicious_extension_sentry`
19. `hudson_rock`
20. `lynis`
21. `trivy`
22. `grype`
23. `chromium_enterprise_policies`
24. `firefox_enterprise_policies`
25. `crxcavator`
26. `emailformat`
27. `gravatar`
28. `skymem`
29. `emailcrawlr`
30. `truecaller`
31. `numverify`
32. `callername`
33. `ahmia`
34. `darksearch`
35. `chrome_web_store_api`
36. `firefox_addons_site_api`
37. `syft`

## Research Workflow Per Provider

For each provider:

1. Read `prompt.md`
2. Research using official docs first
3. Fill `output.md`
4. Set status:
   - `in_progress`
   - `complete`
   - or `deferred`
5. Extract:
   - API/tool surface
   - module mappings
   - signal contracts
   - confidence guidance
   - implementation cautions
6. Move only signal-worthy outputs into the future canonical `signal-registry.md`

## Classification Rules

Use these aggressively to control scope.

- `direct_signal_input`
  - provider output can directly justify a user-facing security signal
- `enrichment_only`
  - useful to add evidence, labels, metadata, or corroboration, but should not emit standalone signals on its own
- `utility_only`
  - collector/parser/inventory source that enables other logic but should not create findings directly
- `out_of_scope`
  - technically interesting but not worth using for launch

## What To Build Research Toward

The launch product should be able to answer:

1. Which owned identities are breached or exposed?
2. Which likely accounts/services should the user secure first?
3. What is weak about the local device baseline?
4. What is weak or risky in the browser setup?
5. What should the user do next, in order?

If a provider does not materially improve one of those outcomes, classify it down or defer it.

## Research Notes

- not every launch-focus provider needs to become a launch feature
- some providers will research as `utility_only` or `enrichment_only`
- local tools must be judged on:
  - installation burden
  - machine-readable output
  - output stability
  - cross-platform coverage
  - privilege requirements
- do not let “interesting OSINT” displace “actionable user outcomes”
