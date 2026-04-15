---
title: "provider launch plan"
tags: [zima, research, providers, launch, moc]
type: provider_launch_plan_index
created: 2026-03-22
updated: 2026-04-15
---

[[../Research/research|Research]] · [[../Research/Providers/_index|Provider Hubs]] · [[../Research/launch-research-dashboard|Launch Research Dashboard]]

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

- [[../Research/Providers/breach/hibp/hibp|hibp]]
- [[../Research/Providers/social/accounts/accounts|accounts]]
- [[../Research/Providers/breach/dehashed/dehashed|dehashed]]
- [[../Research/Providers/breach/leakcheck/leakcheck|leakcheck]]
- [[../Research/Providers/breach/breachdirectory/breachdirectory|breachdirectory]]
- [[../Research/Providers/breach/hudson_rock/hudson_rock|hudson_rock]]
- [[../Research/Providers/reputation/emailrep/emailrep|emailrep]]
- [[../Research/Providers/social/epieos/epieos|epieos]]
- [[../Research/Providers/tools/holehe/holehe|holehe]]
- [[../Research/Providers/tools/maigret/maigret|maigret]]
- [[../Research/Providers/tools/whatsmyname/whatsmyname|whatsmyname]]

### 2. Device Baseline

- [[../Research/Providers/tools/osquery/osquery|osquery]]
- [[../Research/Providers/tools/posture/posture|posture]]
- [[../Research/Providers/tools/macos_native/macos_native|macos_native]]
- [[../Research/Providers/tools/windows_native/windows_native|windows_native]]
- [[../Research/Providers/tools/linux_native/linux_native|linux_native]]
- [[../Research/Providers/tools/lynis/lynis|lynis]]
- [[../Research/Providers/tools/trivy/trivy|trivy]]
- [[../Research/Providers/tools/grype/grype|grype]]
- [[../Research/Providers/tools/syft/syft|syft]]

### 3. Browser Baseline

- [[../Research/Providers/tools/browser_extension_detector/browser_extension_detector|browser_extension_detector]]
- [[../Research/Providers/tools/get_browser_extension_info/get_browser_extension_info|get_browser_extension_info]]
- [[../Research/Providers/tools/malicious_extension_sentry/malicious_extension_sentry|malicious_extension_sentry]]
- [[../Research/Providers/tools/chromium_enterprise_policies/chromium_enterprise_policies|chromium_enterprise_policies]]
- [[../Research/Providers/tools/firefox_enterprise_policies/firefox_enterprise_policies|firefox_enterprise_policies]]
- [[../Research/Providers/threat_intel/crxcavator/crxcavator|crxcavator]]
- [[../Research/Providers/cloud/chrome_web_store_api/chrome_web_store_api|chrome_web_store_api]]
- [[../Research/Providers/cloud/firefox_addons_site_api/firefox_addons_site_api|firefox_addons_site_api]]

### 4. Optional Launch Support

- [[../Research/Providers/phone/truecaller/truecaller|truecaller]]
- [[../Research/Providers/phone/numverify/numverify|numverify]]
- [[../Research/Providers/phone/callername/callername|callername]]
- [[../Research/Providers/darkweb/ahmia/ahmia|ahmia]]
- [[../Research/Providers/darkweb/darksearch/darksearch|darksearch]]
- [[../Research/Providers/social/emailformat/emailformat|emailformat]]
- [[../Research/Providers/social/gravatar/gravatar|gravatar]]
- [[../Research/Providers/social/skymem/skymem|skymem]]
- [[../Research/Providers/social/emailcrawlr/emailcrawlr|emailcrawlr]]

### 5. Email Account Identifier - Pipeline and Onboarding

Features that run inside or downstream of the email account identifier pipeline.

**Wave 1 - output:**
- `pm_exporter_bitwarden` - Bitwarden JSON import
- `pm_exporter_proton_pass` - Proton Pass JSON import

**Wave 2 - pipeline and remediation:**
- `newsletter_detection` - pre-pass noise reduction before account classification
- SimpleLogin and Addy.io - per-service alias creation after account discovery

**Wave 3 - extended:**
- `pm_exporter_1password` - 1Password `.1pux` import
- Custom domain aliasing

**Deferred - post-launch:**
- Local LLM classification layer (requires production misclassification data first)

## Working Rule

If a provider does not improve one of these launch outcomes, defer it:

1. identify breached or exposed owned identities
2. infer likely accounts and services to secure
3. baseline the local device
4. baseline the browser and extensions
5. guide the user to a concrete next action
6. clean up the inbox signal and onboard discovered accounts into a password manager
