---
title: "wave 1 - core launch providers"
tags: [zima, research, providers, launch, wave_1]
type: provider_launch_wave
created: 2026-03-22
updated: 2026-03-22
---

[[./_index|Provider Launch Plan]] · [[../../launch-provider-status-board|Launch Provider Status Board]]

# Wave 1 - Core Launch Providers

These materially improve the audit outcome after Wave 0 is complete.

## Identity and Account Discovery

| provider | role | target modules |
|---|---|---|
| [[../breach/dehashed/dehashed|dehashed]] | breach and credential exposure | `breach_monitor`, `credential_exposure` |
| [[../breach/leakcheck/leakcheck|leakcheck]] | credential exposure support | `credential_exposure` |
| [[../breach/breachdirectory/breachdirectory|breachdirectory]] | supplementary breach evidence | `breach_monitor` |
| [[../breach/hudson_rock/hudson_rock|hudson_rock]] | stealer-log style evidence | `stealer_log_exposure` |
| [[../reputation/emailrep/emailrep|emailrep]] | email exposure context | `account_enumeration_risk`, `username_exposure` |
| [[../social/epieos/epieos|epieos]] | account discovery and alias correlation | `username_exposure`, `alias_correlation` |
| [[../tools/holehe/holehe|holehe]] | email-to-account discovery | `account_inventory`, `account_enumeration_risk` |
| [[../tools/maigret/maigret|maigret]] | username footprint discovery | `username_exposure` |
| [[../tools/whatsmyname/whatsmyname|whatsmyname]] | username and site discovery | `account_inventory`, `alias_correlation` |

## Device Baseline

| provider | role | target modules |
|---|---|---|
| [[../tools/posture/posture|posture]] | opinionated local baseline checks | device baseline modules |
| [[../tools/macos_native/macos_native|macos_native]] | macOS-native posture collection | device baseline modules |
| [[../tools/windows_native/windows_native|windows_native]] | Windows-native posture collection | device baseline modules |
| [[../tools/linux_native/linux_native|linux_native]] | Linux-native posture collection | device baseline modules |

## Browser Baseline

| provider | role | target modules |
|---|---|---|
| [[../tools/malicious_extension_sentry/malicious_extension_sentry|malicious_extension_sentry]] | known-bad extension detection | `extension_risk` |

## Working Rule

Wave 1 providers should improve prioritization, confidence, or remediation. If they only add loose context, classify them down.
