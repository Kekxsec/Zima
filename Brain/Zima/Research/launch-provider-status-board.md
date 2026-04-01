---
title: "launch provider status board"
tags: [zima, research, launch, status, graph_exclude]
type: launch_provider_status_board
created: 2026-03-22
updated: 2026-03-22
---

[[../Zima|Zima]] · [[research|Research]] · [[launch-research-dashboard|Launch Research Dashboard]]

# Launch Provider Status Board

Use this note as the single progress tracker for launch provider research.

Status values:

- `not_started`
- `in_progress`
- `complete`
- `deferred`

## Wave 0

| provider | role | target modules | status | next artifact |
|---|---|---|---|---|
| [[Providers/breach/hibp/hibp|hibp]] | breach anchor | `breach_monitor` | `not_started` | complete `output.md` |
| [[Providers/social/accounts/accounts|accounts]] | account discovery anchor | `account_inventory` | `deferred` | repo returns 404 — replaced by mailcat + holehe + maigret pipeline |
| [[Providers/tools/osquery/osquery|osquery]] | local device/browser inventory anchor | `os_security`, `patch_status`, `software_vulnerability`, browser inventory | `not_started` | complete `output.md` |
| [[Providers/tools/browser_extension_detector/browser_extension_detector|browser_extension_detector]] | local extension inventory anchor | `extension_risk` | `not_started` | complete `output.md` |
| [[Providers/tools/get_browser_extension_info/get_browser_extension_info|get_browser_extension_info]] | extension metadata normalization | `extension_risk` | `not_started` | complete `output.md` |

## Wave 1

| provider | role | target modules | status | next artifact |
|---|---|---|---|---|
| [[Providers/breach/dehashed/dehashed|dehashed]] | breach and credential exposure | `breach_monitor`, `credential_exposure` | `not_started` | complete `output.md` |
| [[Providers/breach/leakcheck/leakcheck|leakcheck]] | credential exposure support | `credential_exposure` | `not_started` | complete `output.md` |
| [[Providers/breach/breachdirectory/breachdirectory|breachdirectory]] | supplementary breach evidence | `breach_monitor` | `not_started` | complete `output.md` |
| [[Providers/reputation/emailrep/emailrep|emailrep]] | email exposure context | `account_enumeration_risk`, `username_exposure` | `not_started` | complete `output.md` |
| [[Providers/social/epieos/epieos|epieos]] | account discovery and alias correlation | `username_exposure`, `alias_correlation` | `deferred` | no public API; terms prohibit automation; requires enterprise contract |
| [[Providers/tools/holehe/holehe|holehe]] | email-to-account discovery | `account_inventory`, `account_enumeration_risk` | `not_started` | complete `output.md` |
| [[Providers/tools/maigret/maigret|maigret]] | username footprint discovery | `username_exposure` | `not_started` | complete `output.md` |
| [[Providers/tools/socid_extractor/socid_extractor|socid_extractor]] | profile enrichment companion to maigret; extracts platform UIDs, creation dates, linked accounts | `username_exposure`, `account_inventory` | `complete` | output.md complete — enrichment_only, no standalone signals |
| [[Providers/tools/mailcat/mailcat|mailcat]] | username-to-email discovery; feeds breach lookup chain | `account_inventory` | `complete` | output.md complete — replaces accounts (404); 37+ providers, 170+ domains |
| [[Providers/tools/whatsmyname/whatsmyname|whatsmyname]] | username/site discovery | `account_inventory`, `alias_correlation` | `not_started` | complete `output.md` |
| [[Providers/tools/posture/posture|posture]] | opinionated local baseline checks | device baseline modules | `not_started` | complete `output.md` |
| [[Providers/tools/macos_native/macos_native|macos_native]] | macOS-native posture collection | device baseline modules | `not_started` | complete `output.md` |
| [[Providers/tools/windows_native/windows_native|windows_native]] | Windows-native posture collection | device baseline modules | `not_started` | complete `output.md` |
| [[Providers/tools/linux_native/linux_native|linux_native]] | Linux-native posture collection | device baseline modules | `not_started` | complete `output.md` |
| [[Providers/tools/malicious_extension_sentry/malicious_extension_sentry|malicious_extension_sentry]] | known-bad extension detection | `extension_risk` | `not_started` | complete `output.md` |
| [[Providers/breach/hudson_rock/hudson_rock|hudson_rock]] | stealer-log style evidence | `stealer_log_exposure` | `not_started` | complete `output.md` |

## Wave 2

| provider | role | target modules | status | next artifact |
|---|---|---|---|---|
| [[Providers/tools/lynis/lynis|lynis]] | hardening evidence | `os_security`, `firewall_status` | `not_started` | complete `output.md` |
| [[Providers/tools/trivy/trivy|trivy]] | software vulnerability evidence | `software_vulnerability` | `not_started` | complete `output.md` |
| [[Providers/tools/grype/grype|grype]] | software vulnerability evidence | `software_vulnerability` | `not_started` | complete `output.md` |
| [[Providers/tools/chromium_enterprise_policies/chromium_enterprise_policies|chromium_enterprise_policies]] | browser policy evidence | `browser_configuration` | `not_started` | complete `output.md` |
| [[Providers/tools/firefox_enterprise_policies/firefox_enterprise_policies|firefox_enterprise_policies]] | browser policy evidence | `browser_configuration` | `not_started` | complete `output.md` |
| [[Providers/threat_intel/crxcavator/crxcavator|crxcavator]] | extension risk enrichment | `extension_risk` | `not_started` | complete `output.md` |
| [[Providers/social/emailformat/emailformat|emailformat]] | alias support | `alias_correlation` | `not_started` | complete `output.md` |
| [[Providers/social/gravatar/gravatar|gravatar]] | public profile enrichment | `public_profile_scan` | `not_started` | complete `output.md` |
| [[Providers/social/skymem/skymem|skymem]] | public email exposure support | `username_exposure` | `not_started` | complete `output.md` |
| [[Providers/social/emailcrawlr/emailcrawlr|emailcrawlr]] | public email mention support | `username_exposure` | `not_started` | complete `output.md` |
| [[Providers/tools/oui_master_database/oui_master_database|oui_master_database]] | local MAC → vendor lookup (87,970+ entries, SQLite, offline) | `device_inventory`, `network_exposure` | `complete` | output.md complete — enrichment_only, zero network/API required |
| [[Providers/threat_intel/leakix/leakix|leakix]] | exposed services & data leak search (LeakIX API) | `infrastructure_exposure`, `data_exposure` | `complete` | output.md complete — free API tier, new module: infrastructure_exposure |
| [[Providers/threat_intel/intelx/intelx|intelx]] | breach context enrichment + dark web monitoring (Intelligence X API) | `breach_monitor`, `darkweb_identity_monitor`, `username_exposure` | `complete` | output.md complete — free tier (90 results), official Python SDK |
| [[Providers/tools/frankenstein/frankenstein|frankenstein]] | DNS + HTTP/S dual probing, TLS audit, security headers | `infrastructure_exposure`, `browser_configuration` | `complete` | output.md complete — Go binary, 50 concurrent workers, SQLite output |

## Wave 3

| provider | role | target modules | status | next artifact |
|---|---|---|---|---|
| [[Providers/social/sociallinks/sociallinks|sociallinks]] | commercial identity graph API; 500+ sources; face search + post analysis | `username_exposure`, `account_inventory` | `complete` | output.md complete — post-launch/enterprise; trial access required |
| [[Providers/phone/truecaller/truecaller|truecaller]] | phone context enrichment | `phone_exposure` | `not_started` | complete `output.md` |
| [[Providers/phone/numverify/numverify|numverify]] | phone carrier enrichment | `phone_exposure` | `not_started` | complete `output.md` |
| [[Providers/phone/callername/callername|callername]] | caller-name enrichment | `phone_exposure` | `not_started` | complete `output.md` |
| [[Providers/darkweb/ahmia/ahmia|ahmia]] | dark-web mention support | `darkweb_identity_monitor` | `not_started` | complete `output.md` |
| [[Providers/darkweb/darksearch/darksearch|darksearch]] | dark-web mention support | `darkweb_identity_monitor` | `not_started` | complete `output.md` |
| [[Providers/cloud/chrome_web_store_api/chrome_web_store_api|chrome_web_store_api]] | Chrome extension metadata enrichment | `extension_risk` | `not_started` | complete `output.md` |
| [[Providers/cloud/firefox_addons_site_api/firefox_addons_site_api|firefox_addons_site_api]] | Firefox extension metadata enrichment | `extension_risk` | `not_started` | complete `output.md` |
| [[Providers/tools/syft/syft|syft]] | inventory utility support | `software_inventory` | `not_started` | complete `output.md` |
| [[Providers/tools/huginn_muninn/huginn_muninn|huginn_muninn]] | device fingerprint reference database (11M records, DHCP fingerprinting) | `device_inventory` | `complete` | output.md complete — post-launch P3; unique value is DHCP fingerprint→device model |
| [[Providers/threat_intel/darkeye/darkeye|darkeye]] | dark web mention search (darkeye.org) | `darkweb_identity_monitor` | `deferred` | output.md complete — superseded by Intelligence X; 10-result limit, no official API docs |
