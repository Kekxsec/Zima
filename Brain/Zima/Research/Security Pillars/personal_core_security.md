---
title: "pillar / personal core security"
tags: [zima, research, pillars, personal_core_security]
type: security_pillar_hub
pillar: personal_core_security
obsidianUIMode: preview
---

[[../research|Research]] · [[_index|Security Pillars]]

# personal/core security

## framing

- foundational personal and SMB security posture
- highest-value early detections for individuals and unmanaged environments
- likely the strongest fit for Core-tier and local-agent/app development

## identity

- scope: breaches, credential exposure, aliases, phone-linked identity risk, and domain-linked identity risk
- suggested modules: `breach_monitor`, `credential_exposure`, `username_exposure`, `stealer_log_exposure`, `phone_exposure`, `alias_correlation`, `domain_identity_correlation`
- provider hubs: [[../Providers/breach/breach|breach]], [[../Providers/darkweb/darkweb|darkweb]], [[../Providers/social/social|social]], [[../Providers/phone/phone|phone]], [[../Providers/reputation/reputation|reputation]], [[../Providers/domain/domain|domain]], [[../Providers/tools/tools|tools]]

## accounts

- scope: MFA posture, sessions, recovery paths, connected apps, and account inventory
- suggested modules: `mfa_posture`, `session_security`, `oauth_risk`, `account_inventory`, `recovery_configuration`, `connected_app_review`
- provider hubs: [[../Providers/social/social|social]], [[../Providers/cloud/cloud|cloud]], [[../Providers/tools/tools|tools]]

## device

- scope: OS posture, patching, disk encryption, firewall status, and vulnerable software
- suggested modules: `os_security`, `patch_status`, `software_vulnerability`, `disk_encryption_check`, `screen_lock_check`, `firewall_status`
- provider hubs: [[../Providers/tools/tools|tools]], [[../Providers/cloud/cloud|cloud]]

## browser

- scope: extension risk, browser configuration, update posture, and privacy protection state
- suggested modules: `extension_risk`, `browser_configuration`, `cookie_policy_check`, `browser_update_check`
- provider hubs: [[../Providers/tools/tools|tools]], [[../Providers/threat_intel/threat_intel|threat_intel]], [[../Providers/social/social|social]]
