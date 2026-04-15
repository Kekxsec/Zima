---
title: "launch research dashboard"
tags: [zima, research, launch, dashboard]
type: research_execution_dashboard
created: 2026-03-22
updated: 2026-03-22
kind: canonical
status: active
llm_include: true
code_scope: cross_repo
---

[[../Zima|Zima]] · [[research|Research]]

# Launch Research Dashboard

This is the working dashboard for the current research phase.

## Objective

Build the launch-ready provider research set for:

- passive identity and account audit
- local device baseline
- local browser baseline
- remediation and onboarding flows

## Start Here

- [[../Launch Plan/wave-1-core-launch-providers|Launch Focus Providers]] — the shortlist to build against
- [[../Launch Plan/_index|Launch Provider Plan]] — the exact wave plan and provider order
- [[provider-research-protocol|Provider Research Protocol]] — the standard output format for all provider research
- [[launch-provider-matrix|Launch Provider Matrix]] — the full inventory and where everything sits

## What To Do Next

### Wave 0: Do Now

Finish these first. They define the launch trust model and the first real signal slice.

1. [[Providers/breach/hibp/hibp|hibp]]
2. [[Providers/social/accounts/accounts|accounts]]
3. [[Providers/tools/osquery/osquery|osquery]]
4. [[Providers/tools/browser_extension_detector/browser_extension_detector|browser_extension_detector]]
5. [[Providers/tools/get_browser_extension_info/get_browser_extension_info|get_browser_extension_info]]

### Wave 1: Core Launch Providers

Do these immediately after Wave 0.

1. [[Providers/breach/dehashed/dehashed|dehashed]]
2. [[Providers/breach/leakcheck/leakcheck|leakcheck]]
3. [[Providers/breach/breachdirectory/breachdirectory|breachdirectory]]
4. [[Providers/reputation/emailrep/emailrep|emailrep]]
5. [[Providers/social/epieos/epieos|epieos]]
6. [[Providers/tools/holehe/holehe|holehe]]
7. [[Providers/tools/maigret/maigret|maigret]]
8. [[Providers/tools/whatsmyname/whatsmyname|whatsmyname]]
9. [[Providers/tools/posture/posture|posture]]
10. [[Providers/tools/macos_native/macos_native|macos_native]]
11. [[Providers/tools/windows_native/windows_native|windows_native]]
12. [[Providers/tools/linux_native/linux_native|linux_native]]
13. [[Providers/tools/malicious_extension_sentry/malicious_extension_sentry|malicious_extension_sentry]]
14. [[Providers/breach/hudson_rock/hudson_rock|hudson_rock]]
15. [[Providers/social/serus/serus|serus]] *(API existence unconfirmed — may defer)*

### Wave 2: Hardening And Enrichment

Useful after the core launch slice is stable.

1. [[Providers/tools/lynis/lynis|lynis]]
2. [[Providers/tools/trivy/trivy|trivy]]
3. [[Providers/tools/grype/grype|grype]]
4. [[Providers/tools/chromium_enterprise_policies/chromium_enterprise_policies|chromium_enterprise_policies]]
5. [[Providers/tools/firefox_enterprise_policies/firefox_enterprise_policies|firefox_enterprise_policies]]
6. [[Providers/threat_intel/crxcavator/crxcavator|crxcavator]]
7. [[Providers/social/emailformat/emailformat|emailformat]]
8. [[Providers/social/gravatar/gravatar|gravatar]]
9. [[Providers/social/skymem/skymem|skymem]]
10. [[Providers/social/emailcrawlr/emailcrawlr|emailcrawlr]]

### Wave 3: Optional Launch Support

Only after the above waves are complete.

1. [[Providers/phone/truecaller/truecaller|truecaller]]
2. [[Providers/phone/numverify/numverify|numverify]]
3. [[Providers/phone/callername/callername|callername]]
4. [[Providers/darkweb/ahmia/ahmia|ahmia]]
5. [[Providers/darkweb/darksearch/darksearch|darksearch]]
6. [[Providers/cloud/chrome_web_store_api/chrome_web_store_api|chrome_web_store_api]]
7. [[Providers/cloud/firefox_addons_site_api/firefox_addons_site_api|firefox_addons_site_api]]
8. [[Providers/tools/syft/syft|syft]]

## Definition Of Done Per Provider

For each provider:

- `prompt.md` is ready and aligned to the standard protocol
- `output.md` is completed
- `output.md` status is updated from `not_started`
- target modules are explicit
- provider classification is explicit:
  - `direct_signal_input`
  - `enrichment_only`
  - `utility_only`
  - `out_of_scope`
- signal contracts are captured where justified
- implementation cautions are captured

## Immediate Deliverables

### Deliverable 1

Finish `output.md` for all Wave 0 providers.

### Deliverable 2

Create the first launch signal registry slice from:

- `hibp`
- `accounts`
- `osquery`
- `browser_extension_detector`
- `get_browser_extension_info`

### Deliverable 3

Freeze the first launch module set:

- `breach_monitor`
- `credential_exposure`
- `account_inventory`
- `username_exposure`
- `os_security`
- `patch_status`
- `software_vulnerability`
- `extension_risk`
- `browser_configuration`

## Working Rules

- do not research all providers at once
- do not promote utility collectors into user-facing signals without a real justification
- do not let interesting OSINT distract from actionable user outcomes
- only include providers that materially improve:
  - owned identity exposure detection
  - account discovery and prioritization
  - device baseline
  - browser baseline
  - remediation guidance

## Reference Notes

- [[Signal Research Guide|Signal Research Guide]]
- [[Provider Module Map|Provider → Module Map]]
- [[Provider Schemas|Provider Schemas]]
- [[Extending the Platform|Extending the Platform]]
- [[../Archive/MVP Build 2026/pre-stage-06-signal-registry-handoff|Pre-Stage-6 Signal Registry Handoff]]
