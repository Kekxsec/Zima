← [[../Zima|Home]] · [[section-17-19-summary-and-outcome|← §17–19 Summary]]

# Section 20 — Expanded Module Domain Breakdown

Each domain entry below describes:

- **Purpose** — what this domain covers
- **Core objectives** — the specific security goals
- **Typical inputs** — data the modules in this domain require
- **Suggested modules** — named modules within this domain
- **Representative signals** — signal types this domain emits
- **Correlated findings** — higher-level findings this domain contributes to
- **Remediation themes** — categories of action that resolve signals in this domain
- **Typical tier alignment** — which tier first enables this domain
- **Implementation notes** — guidance for building this domain

---

> **Note on automation and scoring:** Automation and scoring are top-level backend layers, not module domains. They do not belong under `modules/`. See Sections 4.11, 4.9, and the design principles in Section 2.

---

## 20.1 identity/

### Purpose
Monitor personal and business identity attributes — emails, usernames, phone numbers, and domains — across breach databases, credential dumps, stealer logs, paste sites, and dark web references.

### Core objectives
- detect exposures of email addresses, usernames, phone numbers, and domains
- identify repeated credential exposure and reuse patterns
- build the base identity graph used by other domains
- support both personal and business identity monitoring

### Typical inputs
- email addresses
- usernames and aliases
- phone numbers
- domain names
- breach source records
- stealer log records
- paste mentions
- dark web references

### Suggested modules
- `breach_monitor`
- `credential_exposure`
- `password_hygiene`
- `username_exposure`
- `stealer_log_exposure`
- `account_enumeration_risk`
- `alias_correlation`
- `phone_exposure`
- `domain_identity_correlation`

### Representative signals
- `email_breached`
- `password_exposed`
- `password_reuse_detected`
- `weak_password_detected`
- `username_reuse_detected`
- `stealer_log_hit`
- `phone_number_exposed`
- `alias_exposure_detected`
- `domain_linked_to_breach`

### Correlated findings
- `high_identity_compromise_risk`
- `repeated_credential_exposure_pattern`
- `likely_account_takeover_risk`
- `identity_widely_exposed_online`

### Remediation themes
- rotate exposed credentials immediately
- use unique passwords per service
- enable MFA on all high-value accounts
- monitor high-value identities continuously
- reduce exposure of auxiliary identifiers such as phone numbers

### Typical tier alignment
Enabled in **Core** and all higher tiers.

### Implementation notes
Normalize multiple breach sources into a single view. Aggregate exposures per identity to avoid alert fatigue. This domain forms the backbone of the asset graph — other domains reference email and username entities created here.

---

## 20.2 accounts/

### Purpose
Evaluate the security posture of user accounts, focusing on controls that reduce account takeover risk and improve recoverability.

### Core objectives
- assess MFA posture across accounts
- identify risky login and recovery configurations
- discover stale sessions and connected third-party apps
- identify dormant or unmanaged accounts
- build an account inventory for the user

### Typical inputs
- account metadata from identity providers
- OAuth grant data
- session data
- recovery option configurations
- mailbox rule data
- account usage history

### Suggested modules
- `mfa_posture`
- `session_security`
- `oauth_risk`
- `account_inventory`
- `dormant_account_detection`
- `recovery_configuration`
- `privileged_account_review`
- `suspicious_login_review`
- `connected_app_review`

### Representative signals
- `mfa_missing`
- `sms_mfa_only`
- `recovery_options_missing`
- `stale_session_present`
- `risky_oauth_app`
- `dormant_account_found`
- `privileged_account_without_mfa`
- `suspicious_login_pattern`
- `insecure_recovery_email`

### Correlated findings
- `high_account_takeover_risk`
- `weak_account_recovery_resilience`
- `third_party_access_risk`
- `unmanaged_account_surface`

### Remediation themes
- enable stronger MFA on all accounts
- revoke stale sessions
- remove risky or unnecessary connected apps
- secure recovery methods
- decommission dormant accounts

### Typical tier alignment
Enabled in **Core** and all higher tiers.

### Implementation notes
Accounts must be modeled as entities distinct from identities. One email address may map to many accounts across different services. The account inventory module should be seeded from user-provided data and enriched by providers over time.

---

## 20.3 device/

### Purpose
Assess endpoint security posture across laptops, desktops, and mobile devices.

### Core objectives
- detect outdated operating systems and missing patches
- identify insecure configurations such as disabled disk encryption or no screen lock
- detect risky or vulnerable software installations
- provide baseline hardening guidance

### Typical inputs
- OS version and build
- patch level and last update timestamp
- installed application list with versions
- device configuration settings (encryption, firewall, screen lock)
- local agent data

### Suggested modules
- `os_security`
- `patch_status`
- `software_vulnerability`
- `disk_encryption_check`
- `screen_lock_check`
- `firewall_status`

### Representative signals
- `os_outdated`
- `critical_patch_missing`
- `disk_encryption_disabled`
- `firewall_disabled`
- `screen_lock_not_configured`
- `insecure_configuration_detected`
- `vulnerable_software_detected`

### Correlated findings
- `high_device_compromise_risk`
- `unpatched_endpoint_risk`
- `data_loss_risk` (where encryption is absent)

### Remediation themes
- enable automatic OS and software updates
- enable full-disk encryption
- enforce screen lock with short timeout
- enable host-based firewall
- remove or update vulnerable applications

### Typical tier alignment
Enabled in **Core** and all higher tiers.

### Implementation notes
Device data is primarily sourced from a local agent (`device_agent` provider). Agent reliability must be monitored — stale agent data should mark device signals as `stale` rather than resolved.

---

## 20.4 browser/

### Purpose
Assess browser security posture and extension risk across installed browsers.

### Core objectives
- identify malicious or risky browser extensions
- detect insecure browser configurations
- reduce tracking, data leakage, and privacy risks from the browser layer

### Typical inputs
- installed extension list with permissions and metadata
- browser configuration settings (safe browsing, cookie policy, update status)
- extension store metadata for risk classification

### Suggested modules
- `extension_risk`
- `browser_configuration`
- `cookie_policy_check`
- `browser_update_check`

### Representative signals
- `risky_extension_detected`
- `extension_excessive_permissions`
- `insecure_browser_config`
- `browser_outdated`
- `tracking_protections_disabled`

### Correlated findings
- `browser_credential_theft_risk`
- `high_browser_privacy_exposure`

### Remediation themes
- remove or replace risky extensions
- revoke excessive extension permissions
- enable safe browsing and tracking protection
- update browser to latest version

### Typical tier alignment
Enabled in **Core** and all higher tiers.

### Implementation notes
Data is sourced from the `browser_collector` local provider. Extension risk classification should be maintained as a curated internal dataset supplemented by store metadata. Risk scoring for extensions should factor in: permission scope, install count, review activity, and known malicious classifications.

---

## 20.5 network/

### Purpose
Assess local network and router security posture.

### Core objectives
- detect weak WiFi configurations
- identify exposed or unexpected services on the local network
- assess router security posture including firmware and default credentials

### Typical inputs
- local network scan results
- WiFi configuration metadata (encryption standard, password strength indicator)
- router firmware version and model
- open ports and service banners on local subnet

### Suggested modules
- `router_security`
- `wifi_security`
- `local_network_scan`
- `firmware_version_check`

### Representative signals
- `weak_wifi_encryption`
- `weak_wifi_password_indicator`
- `open_ports_detected`
- `default_router_credentials`
- `router_firmware_outdated`
- `unexpected_device_on_network`

### Correlated findings
- `network_lateral_movement_risk`
- `router_compromise_risk`

### Remediation themes
- upgrade WiFi encryption to WPA3 or WPA2-AES
- change default router credentials immediately
- update router firmware
- close unnecessary exposed ports
- segment networks where possible

### Typical tier alignment
Enabled in **Plus** and higher tiers.

### Implementation notes
Network scanning requires the `local_network_scanner` provider. Passive scanning should be preferred over aggressive scanning to avoid disruption. Router interaction may be limited without admin credentials — document coverage gaps clearly in module limitations.

---

## 20.6 domain/

### Purpose
Monitor domain security posture, DNS configuration, and exposure.

### Core objectives
- detect DNS misconfigurations
- monitor domain reputation and indicators of compromise
- identify email spoofing risks via DMARC, SPF, and DKIM gaps
- assess TLS/certificate posture for owned domains

### Typical inputs
- domain names owned by the user or business
- DNS records (MX, SPF, DMARC, DKIM, A, CNAME, NS)
- TLS certificate metadata
- domain reputation feeds
- subdomain enumeration results

### Suggested modules
- `dns_security`
- `tls_configuration`
- `domain_reputation`
- `dmarc_spf_dkim`
- `subdomain_enumeration`
- `certificate_monitor`

### Representative signals
- `missing_dmarc`
- `missing_spf`
- `weak_tls_configuration`
- `expired_certificate`
- `domain_reputation_flagged`
- `suspicious_subdomain_detected`

### Correlated findings
- `email_spoofing_risk`
- `domain_impersonation_risk`
- `certificate_trust_risk`

### Remediation themes
- publish and enforce DMARC policy
- configure SPF and DKIM records correctly
- upgrade TLS to current standards
- renew certificates before expiry
- investigate suspicious subdomains

### Typical tier alignment
Enabled in **Pro** and higher tiers.

### Implementation notes
Domain data is primarily sourced via `securitytrails`, `whoisxml`, and `crtsh` providers. Monitor certificate transparency logs continuously for unexpected certificates issued for owned domains — this is an early indicator of domain hijack or phishing infrastructure.

---

## 20.7 email/

### Purpose
Secure email systems and detect phishing risk and mailbox compromise.

### Core objectives
- identify suspicious mailbox rules that could facilitate data exfiltration
- detect phishing emails reaching the inbox
- assess email security configuration
- monitor for business email compromise indicators

### Typical inputs
- mailbox rules and filters
- email security policy configuration
- inbound email metadata (headers, sender reputation)
- forwarding configuration

### Suggested modules
- `mailbox_security`
- `phishing_detection`
- `forwarding_rule_check`
- `email_security_config`

### Representative signals
- `suspicious_forwarding_rule`
- `auto_forward_to_external_address`
- `phishing_email_detected`
- `email_security_policy_missing`
- `suspicious_mailbox_rule`

### Correlated findings
- `business_email_compromise_risk`
- `mailbox_exfiltration_risk`
- `email_phishing_exposure`

### Remediation themes
- review and remove suspicious mailbox rules
- block or quarantine forwarding to external addresses
- enable email security controls (ATP, sandboxing)
- train users on phishing recognition

### Typical tier alignment
Enabled in **Pro** and higher tiers.

### Implementation notes
Mailbox access requires OAuth or admin API access from Google Workspace or Microsoft 365 providers. Limit scope to read-only rule and configuration access. Flag all external forwarding rules for human review rather than automated removal.

---

## 20.8 infrastructure/

### Purpose
Monitor internet-facing assets and exposed services.

### Core objectives
- detect unexpectedly exposed services and ports
- identify vulnerable service versions reachable from the internet
- monitor attack surface across IP addresses associated with the user or business

### Typical inputs
- IP addresses and CIDRs owned or associated with the user
- port scan results
- service banner data
- CVE data for detected service versions

### Suggested modules
- `exposed_services`
- `port_scanning`
- `service_banner_analysis`
- `cve_correlation`

### Representative signals
- `exposed_rdp`
- `exposed_ssh`
- `vulnerable_service_detected`
- `service_running_outdated_version`
- `unexpected_port_open`

### Correlated findings
- `high_attack_surface_risk`
- `remote_access_exploitation_risk`

### Remediation themes
- close or firewall unnecessary exposed ports
- update service software to patched versions
- restrict remote access (RDP, SSH) to VPN or allowlisted IPs
- disable services that are not required

### Typical tier alignment
Enabled in **Pro** and higher tiers.

### Implementation notes
Infrastructure scanning uses `shodan`, `censys`, and `binaryedge` providers. These are passive lookups against existing scan data rather than active scanning initiated by Zima. Distinguish clearly between what Zima discovers passively and what would require active scanning. Document this distinction in module limitations.

---

## 20.9 privacy/

### Purpose
Identify personal data exposure across data brokers, public profiles, and information aggregators.

### Core objectives
- detect personal information exposed via data brokers
- identify excessive public profile information
- help users reduce their digital footprint
- flag unnecessary exposure of contact information, address, and employment data

### Typical inputs
- full name
- email addresses
- phone numbers
- physical address
- username aliases

### Suggested modules
- `data_broker_exposure`
- `public_profile_scan`
- `people_search_exposure`

### Representative signals
- `personal_data_exposed_broker`
- `excessive_public_information`
- `address_exposed_online`
- `phone_number_publicly_listed`

### Correlated findings
- `high_privacy_exposure_risk`
- `social_engineering_target_risk`

### Remediation themes
- submit data removal requests to data brokers
- reduce public profile visibility on social platforms
- use aliases and dedicated email addresses for public-facing registrations
- opt out of people-search sites

### Typical tier alignment
Enabled in **Plus** and higher tiers.

### Implementation notes
Data broker coverage is inherently incomplete. Document which brokers and aggregators are covered clearly so users understand the scope. Removal requests cannot always be verified automatically — model remediation status as pending until confirmed.

---

## 20.10 darkweb/

### Purpose
Monitor dark web channels for exposure of credentials, personal data, and direct mentions of the user or business.

### Core objectives
- detect credentials or personal data found on dark web marketplaces or forums
- identify mentions of the user or business on threat actor channels
- provide early warning of targeted threats

### Typical inputs
- email addresses
- usernames
- domain names
- business name

### Suggested modules
- `darkweb_identity_monitor`
- `credential_dump_monitor`
- `threat_actor_mentions`

### Representative signals
- `credential_found_darkweb`
- `identity_mentioned_darkweb`
- `data_for_sale_darkweb`

### Correlated findings
- `active_credential_threat`
- `targeted_threat_actor_risk`

### Remediation themes
- rotate credentials found on dark web immediately
- escalate targeted mentions to incident response
- monitor continuously and increase alert sensitivity for affected identities

### Typical tier alignment
Enabled in **Plus** and higher tiers.

### Implementation notes
Potential sources include Dark Web Informer, curated OSINT feeds, and controlled scraping pipelines. Coverage is inherently partial — dark web visibility is never complete. Be transparent with users about coverage scope. Treat findings from this domain as high-priority signals warranting immediate human review.

---

## 20.11 threat_intel/

### Purpose
Aggregate and apply threat intelligence feeds to identify known malicious infrastructure, indicators of compromise, and emerging threats relevant to the user.

### Core objectives
- detect user-owned or user-accessed assets matching known malicious indicators
- monitor for emerging threats relevant to the user's profile
- flag phishing infrastructure impersonating the user's domains

### Typical inputs
- domain names
- IP addresses
- URLs from browsing or email
- file hashes (where agent data is available)

### Suggested modules
- `phishing_feed_monitor`
- `malware_ioc_monitor`
- `emerging_threats`
- `domain_ioc_match`

### Representative signals
- `malicious_domain_detected`
- `known_ioc_match`
- `phishing_site_impersonating_domain`
- `ip_flagged_threat_intel`

### Correlated findings
- `active_threat_infrastructure_risk`
- `domain_impersonation_via_phishing`

### Remediation themes
- block flagged domains and IPs at network or DNS level
- investigate and report phishing sites impersonating owned domains
- escalate active IOC matches to incident review

### Typical tier alignment
Enabled in **Plus** and higher tiers.

### Implementation notes
Providers include OTX, ThreatFox, OpenPhish, and curated RSS feeds. IOC feeds have high false-positive rates — confidence scoring must account for source reliability and recency. Stale IOC entries (older than 90 days without re-confirmation) should be downgraded automatically.

---

## 20.12 cloud/

### Purpose
Assess cloud infrastructure security posture across cloud accounts and services.

### Core objectives
- identify insecure cloud resource configurations
- detect over-permissioned identities and roles
- flag publicly exposed storage or compute
- review logging and monitoring configuration

### Typical inputs
- cloud account metadata (AWS, GCP, Azure)
- IAM roles, policies, and users
- storage bucket and object configurations
- network security group and firewall rules
- logging and CloudTrail configuration

### Suggested modules
- `cloud_config_review`
- `identity_access_review`
- `public_storage_detection`
- `logging_posture_check`

### Representative signals
- `excessive_iam_permissions`
- `public_storage_detected`
- `mfa_not_enforced_cloud_root`
- `cloudtrail_logging_disabled`
- `insecure_security_group_rule`

### Correlated findings
- `cloud_data_exposure_risk`
- `cloud_account_takeover_risk`
- `compliance_logging_gap`

### Remediation themes
- apply least privilege to all IAM roles and users
- make storage buckets private by default
- enforce MFA on cloud root and admin accounts
- enable audit logging across all cloud services

### Typical tier alignment
Enabled in **Business** tier only.

### Implementation notes
Cloud providers (AWS, GCP, Azure) require read-only IAM role assignment. Clearly document the minimum required permissions for each cloud provider in the provider's `README.md`. Cloud config assessment is a broad domain — prioritize findings by blast radius and likelihood of exploitation.

---

## 20.13 saas/

### Purpose
Manage SaaS application risk exposure across business-critical software.

### Core objectives
- inventory SaaS applications in use
- identify risky or over-permissioned SaaS integrations
- detect shadow SaaS (unapproved apps)
- monitor SaaS security posture and access controls

### Typical inputs
- OAuth grant data from identity provider
- SaaS app lists from Google Workspace or Microsoft 365 admin console
- app permission metadata

### Suggested modules
- `saas_inventory`
- `saas_permission_audit`
- `shadow_saas_detection`

### Representative signals
- `risky_saas_integration`
- `shadow_saas_detected`
- `over_permissioned_saas_app`
- `saas_app_with_broad_data_access`

### Correlated findings
- `saas_data_exfiltration_risk`
- `unmanaged_saas_surface`

### Remediation themes
- revoke access for risky or unrecognised SaaS integrations
- review and reduce OAuth permission scopes
- establish approved SaaS list and block shadow apps
- enforce SSO for all business-critical SaaS

### Typical tier alignment
Enabled in **Business** tier only.

### Implementation notes
SaaS inventory is best sourced from identity provider OAuth grant data (Google Workspace, Microsoft 365). Coverage is limited to apps that use OAuth-based SSO — apps with direct username/password login will not appear. Document this scope limitation clearly.

---

## 20.14 secrets/

### Purpose
Detect exposed secrets and credentials in source code, configuration files, and public repositories.

### Core objectives
- identify API keys, tokens, and passwords committed to source code repositories
- detect secrets in configuration files accessible from the codebase
- prevent ongoing credential leakage from developer workflows

### Typical inputs
- Git repository contents (public and private where access is granted)
- CI/CD configuration files
- commit history

### Suggested modules
- `github_secret_scan`
- `config_secret_scan`
- `commit_history_scan`

### Representative signals
- `api_key_exposed`
- `secret_in_repo`
- `credentials_in_config_file`
- `token_committed_to_history`

### Correlated findings
- `live_credential_exposure_risk`
- `supply_chain_secret_risk`

### Remediation themes
- rotate any exposed secret immediately — assume it is compromised
- remove secret from repository history using git-filter-repo or BFG
- add pre-commit hooks to prevent future secret commits
- migrate to secrets manager patterns (environment variables, vault references)

### Typical tier alignment
Enabled in **Pro** and higher tiers.

### Implementation notes
GitHub scanning uses the GitHub provider with read-only repository access. Treat any discovered secret as actively compromised regardless of commit age — rotation is always the required first step. Pre-commit hook tooling (e.g. `gitleaks`, `detect-secrets`) should be recommended as a remediation action.

---

## 20.15 supply_chain/

### Purpose
Assess software supply chain risk through dependency vulnerability scanning and software bill of materials analysis.

### Core objectives
- identify vulnerable third-party dependencies in use
- detect packages with known CVEs or malicious behaviour indicators
- support SBOM generation for compliance and auditing

### Typical inputs
- dependency manifests (`package.json`, `requirements.txt`, `go.mod`, `Cargo.toml`, etc.)
- lockfiles
- SBOM documents

### Suggested modules
- `dependency_vulnerability_scan`
- `sbom_analysis`
- `malicious_package_detection`

### Representative signals
- `vulnerable_dependency_detected`
- `critically_vulnerable_dependency`
- `malicious_package_suspected`
- `dependency_unmaintained`

### Correlated findings
- `supply_chain_compromise_risk`
- `critical_cve_in_production_dependency`

### Remediation themes
- upgrade vulnerable dependencies to patched versions
- remove or replace unmaintained packages
- pin dependency versions and verify integrity via lockfiles
- establish a dependency review process for new additions

### Typical tier alignment
Enabled in **Pro** and higher tiers.

### Implementation notes
Vulnerability data is sourced from OSV, NVD, and package registry advisories. SBOM generation is a secondary output useful for compliance reporting. Prioritize findings by severity (CVSS score) and reachability — a critical CVE in a transitive dependency that is never called is lower priority than one in a directly invoked code path.

---

## 20.16 backup/

### Purpose
Ensure data recoverability by assessing backup presence, configuration, and integrity.

### Core objectives
- verify that critical data has backups configured
- check that backups are tested and restorable
- identify gaps in recovery point objectives
- assess backup storage security

### Typical inputs
- backup configuration metadata from cloud providers or backup services
- last backup timestamp
- backup storage location and access controls
- backup test records

### Suggested modules
- `backup_presence_check`
- `backup_integrity_test`
- `backup_recency_check`
- `backup_storage_security`

### Representative signals
- `no_backup_detected`
- `backup_not_tested`
- `backup_overdue`
- `backup_storage_publicly_accessible`

### Correlated findings
- `ransomware_recovery_risk`
- `data_loss_risk`

### Remediation themes
- establish automated backup routines for all critical data
- test backup restoration regularly and document results
- store backups in an isolated, access-controlled location
- follow the 3-2-1 backup rule (3 copies, 2 media types, 1 offsite)

### Typical tier alignment
Enabled in **Plus** and higher tiers.

### Implementation notes
Backup assessment is heavily dependent on what data the user provides about their backup setup. Where automated verification is not possible, the module should prompt the user to confirm backup status and record that confirmation with a timestamp for future reference.

---

## 20.17 incident_readiness/

### Purpose
Assess readiness to detect and respond to security incidents effectively.

### Core objectives
- verify that logging and monitoring are configured to support incident detection
- assess whether an incident response plan exists and is current
- identify gaps in detection capability before an incident occurs

### Typical inputs
- logging configuration from cloud and SaaS providers
- existence and recency of incident response documentation
- alert configuration metadata

### Suggested modules
- `incident_plan_check`
- `logging_configuration`
- `alert_coverage_check`

### Representative signals
- `no_incident_plan`
- `incident_plan_outdated`
- `insufficient_logging`
- `no_security_alerting_configured`

### Correlated findings
- `blind_spot_risk` (inability to detect breach)
- `slow_recovery_risk`

### Remediation themes
- create or review incident response plan annually
- enable audit and activity logging across all critical systems
- configure alerts for high-priority signal types
- run tabletop exercises to validate response capability

### Typical tier alignment
Enabled in **Business** tier only.

### Implementation notes
Much of this domain's assessment relies on user-provided information and self-attestation rather than automated verification. Where automated checks are possible (e.g. confirming CloudTrail is enabled), prefer them. Where not possible, prompt the user for confirmation and flag it for periodic review.

---

## 20.18 compliance/

### Purpose
Map the user's or business's security posture to recognised frameworks and identify compliance gaps.

### Core objectives
- assess posture against GDPR baseline controls
- map signals and findings to framework controls (CIS, ISO 27001, Cyber Essentials, NIST)
- identify and prioritise compliance gaps
- support audit preparation

### Typical inputs
- signals and findings from all other active domains
- user or business profile (jurisdiction, industry, data handling description)
- framework selection

### Suggested modules
- `gdpr_check`
- `baseline_controls_check`
- `framework_mapping`

### Representative signals
- `compliance_gap_detected`
- `gdpr_control_missing`
- `framework_control_not_met`

### Correlated findings
- `regulatory_risk_exposure`
- `audit_readiness_gap`

### Remediation themes
- address highest-priority compliance gaps first based on risk and regulatory exposure
- document controls that are met and maintain evidence
- establish review cadence for compliance posture

### Typical tier alignment
Enabled in **Business** tier only.

### Implementation notes
Compliance mapping is derived from signals and findings already generated by other domains — this domain adds a framework lens rather than new detection. Maintain framework control mappings as versioned data files separate from module logic. Support multiple frameworks simultaneously where the user has multiple compliance obligations.

---

## 20.19 Cross-Domain Correlation Patterns

Cross-domain intelligence is not a separate module domain. It is the responsibility of the **correlation layer** (Section 4.8), which uses the asset graph to relate signals from different domains into composite findings.

**Example patterns:**

| Signal combination | Resulting finding |
|---|---|
| `email_breached` + `mfa_missing` + `password_reuse_detected` | `high_account_takeover_risk` |
| `missing_dmarc` + `domain_reputation_flagged` + `phishing_email_detected` | `brand_impersonation_risk` |
| `os_outdated` + `exposed_rdp` + `weak_wifi_encryption` | `high_device_compromise_risk` |
| `risky_saas_integration` + `over_permissioned_saas_app` | `saas_data_exfiltration_risk` |
| `api_key_exposed` + `vulnerable_dependency_detected` | `supply_chain_compromise_risk` |

These combinations are defined as rules in `backend/app/correlation/rules/`. New cross-domain findings are added there, not in individual module domains.

---

## 20.20 Final Domain Model Principle

Zima's domain model follows one rule without exception:

- **Domains** define security areas of concern
- **Modules** define specific detection capabilities within a domain
- **Providers** define data sources consumed by modules

Never mix these concerns.

Each domain must:

- be independently deployable
- emit standardized signals
- integrate with other domains only via the correlation layer

This ensures:

- **scalability** — new domains can be added without modifying existing ones
- **maintainability** — each domain can be understood, tested, and modified in isolation
- **extensibility** — new providers, modules, and correlation rules can be introduced without architectural changes

---

**See also:** [[section-06-module-architecture|§6 Module Architecture]] · [[section-07-provider-module-relationships|§7 Provider↔Module Patterns]] · [[section-12-example-module-definition|§12 Example Module]] · [[section-17-19-summary-and-outcome|§17–19 Summary]] · [[../Zima|Home]]
