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

**JWT library**
Use `PyJWT` (package: `PyJWT>=2.8.0`, import: `import jwt`). Do not use `python-jose` — it is unmaintained and has known CVEs. Algorithm confusion attacks are less mitigated in python-jose.

**Input validation**
All inputs — from users, from providers, from the API — must be validated and sanitized strictly. Treat all external data as untrusted.

**Graceful failure handling**
Timeouts, authentication failures, and malformed data must never cause unhandled exceptions or data corruption. Every provider and module must degrade gracefully.

**Rate limiting and backoff**
Implement rate limiting on all outbound provider calls. Use exponential backoff with jitter on retries. Do not hammer failing APIs.

*Implementation note:* The inbound API rate limiter (slowapi) uses Redis as its storage backend (`storage_uri=settings.redis_url`). This ensures counters are shared across all worker processes and persist across restarts. The rate limit key is the real client IP, extracted from `X-Forwarded-For` (leftmost entry) or `X-Real-IP` headers — not `request.client.host`, which resolves to the Railway load balancer on all requests. The limiter is fail-open on transient Redis failures after startup; a Redis failure at startup is fail-closed. Monitor Redis health.

**Secure defaults**
Configuration defaults must be secure. Do not require users to opt into security — make the secure choice the default everywhere.

*Implementation notes:*
- `Settings.validate_jwt_secret_key` enforces a minimum length of 32 characters at startup. Shorter values raise `ValueError` with instructions for generating a suitable key.
- `Settings.validate_production_settings` raises `ValueError` at startup if `APP_ENV=production` and any CORS origin contains `localhost` or `127.0.0.1`.
- `EmailService` raises `RuntimeError` at startup if `APP_ENV=production` and `RESEND_API_KEY` is not set.
- Raw OTP codes are never logged — even in development, the log entry omits the code value.

**OTP brute-force protection**
The auth service tracks consecutive OTP verification failures per user. After `OTP_MAX_FAILURES` (5) consecutive failures, `User.otp_locked_until` is set to `now + 15 minutes`. All `verify_otp` calls check the lockout before touching the token, ensuring a locked account cannot be verified regardless of whether the submitted code is correct. The counter and lockout are reset to zero on successful verification. This is DB-backed and remains active regardless of Redis state.

**Exception handling**
Never use a bare `except Exception` to catch both domain errors and infrastructure failures in the same branch. Auth errors (`AuthTokenInvalidException`, `AuthTokenExpiredException`) must be caught explicitly. Unknown exceptions must propagate to the framework's default error handler so operators see 500 errors rather than misleading 401s.

**Audit logging**
All significant actions — scan executions, automation workflow runs, user-initiated changes — must be written to an immutable audit log. Automation actions in particular must be fully traceable.

*Implementation note (Stages 1–2):* `AuditEvent` is append-only (never updated or deleted). On GDPR erasure, `user_id` is nulled but the event row is retained. `AuditRepository` is wired into `AuthService` via dependency injection and emits `SIGN_IN_REQUESTED`, `SIGN_IN_SUCCESS`, `SIGN_IN_FAILED`, and `OTP_RATE_LIMITED` events. Auth failures emit audit events with `user_id=None` when no user identity can be established. Lockout events are recorded as `SIGN_IN_FAILED` with `metadata.reason = "locked"`.

**Sandboxing**
High-risk provider interactions (e.g. local network scanning, device agents) should be sandboxed or isolated where possible.

**Safe data processing**
Never pass untrusted provider data to unsafe operations (e.g. `eval`, shell commands, dynamic imports). Treat provider responses as hostile input.
