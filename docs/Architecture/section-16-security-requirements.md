# Section 16 — Security Requirements for Zima Itself

Because Zima handles sensitive personal and business data and may execute actions on behalf of users, the platform must be built with security-first practices throughout. These are not optional — they are architectural requirements.

---

## Requirements

**Secrets management**
Never store API keys, provider credentials, or user tokens in the database in plaintext. Use a secrets manager (e.g. HashiCorp Vault, AWS Secrets Manager, or an encrypted local keystore for personal deployments). Reference secrets by identifier only.

**Encryption at rest and in transit**
All sensitive data must be encrypted at rest. All communication between Zima components and external providers must use TLS. Internal service-to-service communication must also be encrypted where applicable.

**Least privilege**
Providers and workflows should request only the minimum permissions necessary. OAuth scopes, API keys, and automation credentials must be scoped narrowly. Review and document the required permissions for every provider.

**Input validation**
All inputs — from users, from providers, from the API — must be validated and sanitized strictly. Treat all external data as untrusted.

**Graceful failure handling**
Timeouts, authentication failures, and malformed data must never cause unhandled exceptions or data corruption. Every provider and module must degrade gracefully.

**Rate limiting and backoff**
Implement rate limiting on all outbound provider calls. Use exponential backoff with jitter on retries. Do not hammer failing APIs.

**Secure defaults**
Configuration defaults must be secure. Do not require users to opt into security — make the secure choice the default everywhere.

**Audit logging**
All significant actions — scan executions, automation workflow runs, user-initiated changes — must be written to an immutable audit log. Automation actions in particular must be fully traceable.

**Sandboxing**
High-risk provider interactions (e.g. local network scanning, device agents) should be sandboxed or isolated where possible.

**Safe data processing**
Never pass untrusted provider data to unsafe operations (e.g. `eval`, shell commands, dynamic imports). Treat provider responses as hostile input.
