---
title: "pillar / business operational security"
tags: [zima, research, pillars, business_operational_security]
type: security_pillar_hub
pillar: business_operational_security
obsidianUIMode: preview
kind: reference
status: active
llm_include: true
code_scope: cross_repo
---

[[../research|Research]] · [[_index|Security Pillars]]

# business and operational security

## framing

- managed environments, operational resilience, and business-grade control coverage
- strongest fit for Business-tier and authenticated provider integrations
- more likely to depend on cloud APIs, admin access, and structured control evidence

## cloud

- scope: cloud configuration, IAM posture, public storage, and logging coverage
- suggested modules: `cloud_config_review`, `identity_access_review`, `public_storage_detection`, `logging_posture_check`
- provider hubs: [[../Providers/cloud/cloud|cloud]], [[../Providers/tools/tools|tools]]

## saas

- scope: SaaS inventory, shadow SaaS, OAuth permissions, and risky third-party app access
- suggested modules: `saas_inventory`, `saas_permission_audit`, `shadow_saas_detection`
- provider hubs: [[../Providers/social/social|social]], [[../Providers/domain/domain|domain]], [[../Providers/cloud/cloud|cloud]]

## secrets

- scope: exposed tokens, keys, credentials, and secrets in repositories, configs, and commit history
- suggested modules: `github_secret_scan`, `config_secret_scan`, `commit_history_scan`
- provider hubs: [[../Providers/tools/tools|tools]], [[../Providers/social/social|social]], [[../Providers/content_analysis/content_analysis|content_analysis]], [[../Providers/cloud/cloud|cloud]]

## supply_chain

- scope: vulnerable dependencies, malicious packages, and SBOM-oriented software risk
- suggested modules: `dependency_vulnerability_scan`, `sbom_analysis`, `malicious_package_detection`
- provider hubs: [[../Providers/tools/tools|tools]], [[../Providers/content_analysis/content_analysis|content_analysis]], [[../Providers/threat_intel/threat_intel|threat_intel]]

## backup

- scope: backup presence, recency, integrity testing, and storage security
- suggested modules: `backup_presence_check`, `backup_integrity_test`, `backup_recency_check`, `backup_storage_security`
- provider hubs: [[../Providers/cloud/cloud|cloud]]

## incident_readiness

- scope: incident planning, logging posture, alert coverage, and response readiness
- suggested modules: `incident_plan_check`, `logging_configuration`, `alert_coverage_check`
- provider hubs: [[../Providers/cloud/cloud|cloud]]

## compliance

- scope: framework mapping, control coverage, and audit-readiness gaps derived from other domains
- suggested modules: `gdpr_check`, `baseline_controls_check`, `framework_mapping`
- provider hubs: [[../Providers/cloud/cloud|cloud]], [[../Providers/domain/domain|domain]], [[../Providers/threat_intel/threat_intel|threat_intel]], [[../Providers/tools/tools|tools]]
