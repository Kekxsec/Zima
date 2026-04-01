---
title: "launch focus providers"
tags: [zima, research, launch, providers, focus]
type: launch_focus_providers
created: 2026-03-22
updated: 2026-03-22
---

[[../Zima|Zima]] · [[research|Research]] · [[launch-provider-matrix|Launch Provider Matrix]]

# Launch Focus Providers

This is the implementation shortlist for the launch scenario:

- consumer-facing guided security audit
- passive identity/account exposure first
- local device/browser baseline second
- remediation, education, and tooling onboarding throughout

## Focus Now

| provider          | provider path                      | what it does                                                      | architecture sit                                                        | launch priority |
| ----------------- | ---------------------------------- | ----------------------------------------------------------------- | ----------------------------------------------------------------------- | --------------- |
| `hibp`            | `providers/breach/hibp`            | confirmed breach exposure and breach history                      | `identity -> breach_monitor`                                            | `P0`            |
| `dehashed`        | `providers/breach/dehashed`        | richer credential and account exposure                            | `identity -> breach_monitor`, `credential_exposure`                     | `P0`            |
| `leakcheck`       | `providers/breach/leakcheck`       | credential exposure lookup                                        | `identity -> credential_exposure`                                       | `P0`            |
| `breachdirectory` | `providers/breach/breachdirectory` | supplementary breach coverage                                     | `identity -> breach_monitor`                                            | `P1`            |
| `hudson_rock`     | `providers/breach/hudson_rock`     | stealer-log style compromised credential signals                  | `identity -> stealer_log_exposure`                                      | `P1`            |
| `emailrep`        | `providers/reputation/emailrep`    | email reputation / exposure context                               | `identity -> account_enumeration_risk`, `username_exposure`             | `P1`            |
| ~~`accounts`~~    | ~~`providers/social/accounts`~~    | ~~likely service/account discovery from usernames and email handles~~ | **DEFERRED** — GitHub repo returns 404; replaced by mailcat + holehe + maigret | ~~`P0`~~ |
| `mailcat`         | `providers/tools/mailcat`          | username-to-email address discovery across 37+ providers; feeds breach chain | `accounts -> account_inventory` (email discovery precursor)   | `P1`            |
| ~~`epieos`~~      | ~~`providers/social/epieos`~~      | ~~account discovery and alias correlation from email~~            | **DEFERRED** — no public API; terms prohibit automation; enterprise contract only | ~~`P1`~~ |
| `holehe`          | `providers/tools/holehe`           | email-to-service account discovery                                | `accounts -> account_inventory`, `identity -> account_enumeration_risk` | `P1`            |
| `maigret`         | `providers/tools/maigret`          | username footprint discovery across 3000+ sites                   | `identity -> username_exposure`                                         | `P1`            |
| `socid_extractor` | `providers/tools/socid_extractor`  | enrich maigret-found profile URLs with platform UIDs, creation dates, linked accounts | `identity -> username_exposure` (enrichment), `account_inventory` (enrichment) | `P2` |
| `whatsmyname`     | `providers/tools/whatsmyname`      | username-to-service presence discovery                            | `accounts -> account_inventory`                                         | `P1`            |
| `emailformat`     | `providers/social/emailformat`     | alias and address pattern correlation                             | `identity -> alias_correlation`                                         | `P2`            |
| `gravatar`        | `providers/social/gravatar`        | public profile / avatar linkage from email                        | `privacy -> public_profile_scan`, `identity` support                    | `P2`            |
| `skymem`          | `providers/social/skymem`          | public email/identity exposure discovery                          | `identity -> username_exposure`, `privacy` support                      | `P2`            |
| `emailcrawlr`     | `providers/social/emailcrawlr`     | public email mentions and exposure clues                          | `identity -> username_exposure`, `privacy` support                      | `P2`            |

## Device Baseline

| provider | provider path | what it does | architecture sit | launch priority |
|---|---|---|---|---|
| `osquery` | `providers/tools/osquery` | broad device inventory and posture collection | `device -> os_security`, `patch_status`, `software_vulnerability` | `P0` |
| `posture` | `providers/tools/posture` | opinionated local posture checks | `device -> baseline posture modules` | `P0` |
| `macos_native` | `providers/tools/macos_native` | macOS-native posture and config checks | `device -> platform-specific baseline` | `P0` |
| `windows_native` | `providers/tools/windows_native` | Windows-native posture and config checks | `device -> platform-specific baseline` | `P0` |
| `linux_native` | `providers/tools/linux_native` | Linux-native posture and config checks | `device -> platform-specific baseline` | `P0` |
| `lynis` | `providers/tools/lynis` | host hardening audit and findings | `device -> os_security`, `firewall_status`, hardening guidance | `P1` |
| `trivy` | `providers/tools/trivy` | vulnerable software / package checks | `device -> software_vulnerability` | `P1` |
| `grype` | `providers/tools/grype` | package vulnerability scanning | `device -> software_vulnerability` | `P1` |
| `syft` | `providers/tools/syft` | software inventory / SBOM support | `device -> software inventory utility` | `P2` |

## Browser Baseline

| provider | provider path | what it does | architecture sit | launch priority |
|---|---|---|---|---|
| `browser_extension_detector` | `providers/tools/browser_extension_detector` | detect installed browser extensions | `browser -> extension_risk` | `P0` |
| `get_browser_extension_info` | `providers/tools/get_browser_extension_info` | normalize extension metadata and permissions | `browser -> extension_risk` | `P0` |
| `malicious_extension_sentry` | `providers/tools/malicious_extension_sentry` | internal risk classification for known-bad extensions | `browser -> extension_risk` | `P0` |
| `chromium_enterprise_policies` | `providers/tools/chromium_enterprise_policies` | Chromium-family browser policy/config checks | `browser -> browser_configuration` | `P1` |
| `firefox_enterprise_policies` | `providers/tools/firefox_enterprise_policies` | Firefox policy/config checks | `browser -> browser_configuration` | `P1` |
| `crxcavator` | `providers/threat_intel/crxcavator` | extension reputation / risk enrichment | `browser -> extension_risk` | `P1` |
| `chrome_web_store_api` | `providers/cloud/chrome_web_store_api` | extension store metadata enrichment | `browser -> extension_risk` | `P2` |
| `firefox_addons_site_api` | `providers/cloud/firefox_addons_site_api` | Firefox add-on metadata enrichment | `browser -> extension_risk` | `P2` |

## Optional Support At Launch

| provider | provider path | what it does | architecture sit | launch priority |
|---|---|---|---|---|
| `truecaller` | `providers/phone/truecaller` | public phone identity / caller context | `identity -> phone_exposure`, `privacy` support | `P2` |
| `numverify` | `providers/phone/numverify` | phone number carrier / line-type enrichment | `identity -> phone_exposure` | `P2` |
| `callername` | `providers/phone/callername` | caller-name style enrichment | `identity -> phone_exposure` | `P2` |
| `googlemaps` | `providers/social/googlemaps` | public people/business/location exposure clues | `privacy -> data_broker_exposure` | `P3` |
| `openstreetmap` | `providers/social/openstreetmap` | public map/location exposure clues | `privacy -> data_broker_exposure` | `P3` |
| `ahmia` | `providers/darkweb/ahmia` | dark-web mention search | `darkweb -> darkweb_identity_monitor` | `P3` |
| `darksearch` | `providers/darkweb/darksearch` | dark-web search and mention discovery | `darkweb -> darkweb_identity_monitor` | `P3` |

## Post-Launch / Enterprise

| provider | provider path | what it does | architecture sit | launch priority |
|---|---|---|---|---|
| `sociallinks` | `providers/social/sociallinks` | commercial identity graph API; 500+ sources; face search, social post analysis, blockchain + dark web | `identity -> username_exposure`, `account_inventory` (enrichment) | `post-launch` |

## Do Not Focus On For Launch

- `domain/*`
- `ip/*`
- most `threat_intel/*`
- most `cloud/*`
- `crypto/*`
- `tools/network_*`
- `tools/domain_web_and_external_exposure_discovery/*`
- `tools/cloud_and_infrastructure_posture/*`
- `content_analysis/*` as standalone product work

Those groups are useful later, but they do not materially improve the first consumer outcome:

`find what matters, prioritize it, and guide the user through fixing it`

## Deferred (Blocked)

| provider | reason |
|---|---|
| `accounts` (soxoj) | GitHub repo returns HTTP 404 — cannot source schema or interface. Replaced by mailcat + holehe + maigret pipeline. |
| `epieos` | No public API schema; Terms of Service prohibit robot/automated queries; enterprise custom plan only. Contact for contract before revisiting. |
