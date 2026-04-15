← [[../Zima|Home]] · [[section-11-development-rules|← §11 Dev Rules]] · [[section-13-example-provider-definition|§13 Example Provider →]]

# Section 12 — Example Module Definition

This section provides a fully worked example of a module definition to serve as a reference template for all future module development.

---

**Module:** `mfa_posture`
**Domain:** `accounts`
**Security capability:** Detect accounts lacking strong MFA or relying on weak factors such as SMS
**Required inputs:** Account identifiers and admin API access, depending on provider
**Providers used:** Google Workspace, Microsoft 365, GitHub

**Signals emitted:**

- `mfa_missing`
- `sms_mfa_only`
- `fido_key_not_enabled`

**Possible correlated findings:**

- `high_account_takeover_risk`

**Remediation playbooks:**

- enroll in authenticator app MFA
- register hardware security key
- add backup codes

**Automation hooks:**

- open MFA enablement workflow where provider API supports it

**Known limitations:**

- requires sufficient API privileges; read-only OAuth scopes are insufficient
- may not cover all personal account types or self-hosted identity providers

---

## What This Demonstrates

- The module focuses on exactly one capability: assessing MFA posture
- It consumes multiple providers (Google Workspace, Microsoft 365, GitHub) via Pattern C
- It does not decide correlation or scoring — it emits signals only
- Remediation hints are lightweight references to playbooks; the remediation engine owns the full guidance
- Known limitations are documented honestly at the module level
