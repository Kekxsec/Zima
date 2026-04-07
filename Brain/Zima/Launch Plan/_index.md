---
title: "provider launch plan"
tags: [zima, research, providers, launch, moc]
type: provider_launch_plan_index
created: 2026-03-22
updated: 2026-03-22
---

[[../../research|Research]] · [[../_index|Provider Hubs]] · [[../../launch-research-dashboard|Launch Research Dashboard]]

# Provider Launch Plan

Use this folder as the execution view over the full provider catalogue.

It does not replace the category folders. It groups the existing providers by launch sequence and by the user journey you are building:

- passive identity and account audit
- local device baseline
- local browser baseline
- remediation and onboarding support

## Start Here

- [[wave-0-anchor-and-baseline|Wave 0 - Anchor and Baseline]]
- [[wave-1-core-launch-providers|Wave 1 - Core Launch Providers]]
- [[wave-2-hardening-and-enrichment|Wave 2 - Hardening and Enrichment]]
- [[wave-3-optional-launch-support|Wave 3 - Optional Launch Support]]
- [[deferred-for-launch|Deferred for Launch]]

## Launch Sections

### 1. Identity and Account Audit

Research these first because they define the user-facing audit value:

- [[../breach/hibp/hibp|hibp]]
- [[../social/accounts/accounts|accounts]]
- [[../breach/dehashed/dehashed|dehashed]]
- [[../breach/leakcheck/leakcheck|leakcheck]]
- [[../breach/breachdirectory/breachdirectory|breachdirectory]]
- [[../breach/hudson_rock/hudson_rock|hudson_rock]]
- [[../reputation/emailrep/emailrep|emailrep]]
- [[../social/epieos/epieos|epieos]]
- [[../tools/holehe/holehe|holehe]]
- [[../tools/maigret/maigret|maigret]]
- [[../tools/whatsmyname/whatsmyname|whatsmyname]]

### 2. Device Baseline

- [[../tools/osquery/osquery|osquery]]
- [[../tools/posture/posture|posture]]
- [[../tools/macos_native/macos_native|macos_native]]
- [[../tools/windows_native/windows_native|windows_native]]
- [[../tools/linux_native/linux_native|linux_native]]
- [[../tools/lynis/lynis|lynis]]
- [[../tools/trivy/trivy|trivy]]
- [[../tools/grype/grype|grype]]
- [[../tools/syft/syft|syft]]

### 3. Browser Baseline

- [[../tools/browser_extension_detector/browser_extension_detector|browser_extension_detector]]
- [[../tools/get_browser_extension_info/get_browser_extension_info|get_browser_extension_info]]
- [[../tools/malicious_extension_sentry/malicious_extension_sentry|malicious_extension_sentry]]
- [[../tools/chromium_enterprise_policies/chromium_enterprise_policies|chromium_enterprise_policies]]
- [[../tools/firefox_enterprise_policies/firefox_enterprise_policies|firefox_enterprise_policies]]
- [[../threat_intel/crxcavator/crxcavator|crxcavator]]
- [[../cloud/chrome_web_store_api/chrome_web_store_api|chrome_web_store_api]]
- [[../cloud/firefox_addons_site_api/firefox_addons_site_api|firefox_addons_site_api]]

### 4. Optional Launch Support

- [[../phone/truecaller/truecaller|truecaller]]
- [[../phone/numverify/numverify|numverify]]
- [[../phone/callername/callername|callername]]
- [[../darkweb/ahmia/ahmia|ahmia]]
- [[../darkweb/darksearch/darksearch|darksearch]]
- [[../social/emailformat/emailformat|emailformat]]
- [[../social/gravatar/gravatar|gravatar]]
- [[../social/skymem/skymem|skymem]]
- [[../social/emailcrawlr/emailcrawlr|emailcrawlr]]

### 5. Email Account Identifier — Pipeline and Onboarding

Features that run inside or downstream of the email account identifier pipeline.

**Wave 1 — output:**
- `pm_exporter_bitwarden` — Bitwarden JSON import
- `pm_exporter_proton_pass` — Proton Pass JSON import

**Wave 2 — pipeline and remediation:**
- `newsletter_detection` — pre-pass noise reduction before account classification
- SimpleLogin and Addy.io — per-service alias creation after account discovery

**Wave 3 — extended:**
- `pm_exporter_1password` — 1Password `.1pux` import
- Custom domain aliasing

**Deferred — post-launch:**
- Local LLM classification layer (requires production misclassification data first)

## Working Rule

If a provider does not improve one of these launch outcomes, defer it:

1. identify breached or exposed owned identities
2. infer likely accounts and services to secure
3. baseline the local device
4. baseline the browser and extensions
5. guide the user to a concrete next action
6. clean up the inbox signal and onboard discovered accounts into a password manager
