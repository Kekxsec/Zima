---
tags: [zima, mvp, build, launch-gate]
created: 2026-03-21
updated: 2026-04-14
status: open
related:
  - "[[Zima]]"
  - "[[next-steps-to-launch]]"
---

← [[../Archive/MVP Build 2026/MVP Master|Stage Progress]]

# Stage 8 — Pre-Launch Hardening

**Exit condition:** Every item in this stage is complete and verified. This is the gate between "technically working" and "ready to accept real users." Nothing in this stage is optional.

---

## 8.1 Security Audit Checklist

Work through each item and mark it verified before launch. These map directly to the gaps identified in the architecture review.

### Authentication and Session Security

- [x] OTP codes are hashed with SHA-256 before storage — raw codes never appear in the database
- [x] OTP rate limiting enforced: 3 requests per 15 minutes per IP on `/otp/request` (Redis-backed, shared across workers)
- [x] OTP verification rate limiting enforced: 10 attempts per 15 minutes per IP on `/otp/verify` (Redis-backed)
- [x] Per-email OTP lockout: 5 consecutive failures triggers a 15-minute lockout (DB-backed, Redis-independent)
- [x] All auth failure paths return identical HTTP 401 with identical response body (no enumeration)
- [x] JWT `type` claim validated on every token decode (prevents access tokens being used as refresh tokens)
- [x] JWT secret minimum entropy enforced at startup: `Settings.validate_jwt_secret_key` rejects keys shorter than 32 characters
- [x] Deleted users cannot sign in (checked in `get_current_user` dependency)
- [x] No passwords anywhere in the codebase (grep for `password`, `bcrypt`, `passlib` — should return zero hits)

### Transport Security

- [ ] HTTPS enforced at Nginx — all HTTP requests redirect to HTTPS with 301
- [ ] TLS 1.2 minimum, TLS 1.3 preferred — TLS 1.0 and 1.1 disabled
- [ ] HSTS header present: `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- [ ] SSL certificate is valid and auto-renewing (Let's Encrypt with Certbot)
- [ ] Certificate expiry monitoring configured (alert at 30 days remaining)

### Security Headers (verify with https://securityheaders.com after deployment)

- [ ] `X-Frame-Options: DENY`
- [ ] `X-Content-Type-Options: nosniff`
- [ ] `Content-Security-Policy` — verify no `unsafe-inline` or `unsafe-eval` unless intentional
- [ ] `Referrer-Policy: strict-origin-when-cross-origin`
- [ ] `Permissions-Policy` — disable unused browser features
- [ ] `Cache-Control: no-store` on API responses
- [ ] No `Server` header leaking framework/version info

### CORS

- [x] `CORS_ALLOWED_ORIGINS` in environment — never hardcoded
- [x] Production guard: `Settings.validate_production_settings` raises at startup if any origin contains `localhost` or `127.0.0.1` when `APP_ENV=production`
- [ ] Production value is `https://yourdomain.com` only — set in Railway environment before launch
- [ ] CORS preflight returns correct `Access-Control-Allow-Methods`

### Input Validation

- [ ] All request bodies validated by Pydantic v2 schemas
- [ ] Email inputs normalized to lowercase before use
- [ ] Pagination params bounded (`limit` capped at 100, `offset` >= 0)
- [ ] No raw SQL queries anywhere outside `db/repositories/`
- [ ] Provider API responses never passed directly to database — always mapped through schemas

### Secrets Management

- [ ] No secrets in source code (run `git log --all --full-history -- "*.env"` — should return nothing)
- [ ] `detect-private-key` pre-commit hook active
- [ ] All secrets loaded via Pydantic `SecretStr` — never plain strings
- [ ] Production secrets managed via Doppler — not `.env` files on server
- [ ] Stripe webhook secret verified on every webhook request
- [ ] HIBP API key stored in secrets manager and never logged

### Rate Limiting

- [x] `/auth/otp/request` — 3 per 15 minutes per IP (real IP from `X-Forwarded-For`, Redis-backed)
- [x] `/auth/otp/verify` — 10 per 15 minutes per IP (real IP from `X-Forwarded-For`, Redis-backed)
- [x] Per-email lockout after 5 failures (DB-backed, Redis-independent fallback)
- [ ] `/scans/` POST — 5 per hour per user
- [ ] Global rate limiter configured for the API as a whole

### GDPR

- [ ] Account deletion endpoint implemented and tested
- [ ] Data export endpoint implemented and tested
- [ ] Privacy policy published at accessible URL before any sign-ups
- [ ] Terms of service published
- [ ] Consent recorded at first sign-in (`privacy_policy_accepted_at` set)
- [ ] Data retention policy documented and enforced programmatically
- [ ] ICO registration completed if processing personal data for commercial purposes (check current threshold — currently £40/year for most organisations)

---

## 8.2 Dependency Security Scan

Run before every release:

```bash
uv run pip-audit
```

Add `pip-audit` to dev dependencies. Zero known vulnerabilities required before launch. Address any findings — do not defer them.

Add to CI:

```yaml
- name: Security audit
  run: uv run pip-audit --requirement pyproject.toml
```

---

## 8.3 Environment Verification

Create a startup check that validates all required environment variables are present before the application starts serving traffic. This prevents silent failures where a missing API key causes runtime errors hours after deployment.

```python
# core/startup.py
from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

REQUIRED_IN_PRODUCTION = [
    ("resend_api_key", "Email delivery will not work"),
    ("stripe_secret_key", "Billing will not work"),
    ("stripe_webhook_secret", "Webhooks will not work"),
    ("hibp_api_key", "Breach monitoring will not work"),
]


def check_environment() -> None:
    if not settings.is_production:
        return  # Only enforce in production

    warnings = []
    for attr, message in REQUIRED_IN_PRODUCTION:
        if not getattr(settings, attr, None):
            warnings.append(f"Missing {attr.upper()}: {message}")

    if warnings:
        for w in warnings:
            logger.warning("startup.missing_config", message=w)
        # In production, fail hard if critical config is missing
        raise RuntimeError(
            f"Missing required production configuration:\n" + "\n".join(warnings)
        )
```

Call `check_environment()` in the `lifespan` function in `main.py`.

---

## 8.4 Logging Hygiene

Before launch, audit every log statement for accidental PII or secret leakage:

```bash
# Grep for patterns that might log sensitive data
grep -r "logger" backend/ | grep -i "password\|secret\|api_key\|token\|email"
```

Rules:
- Never log email addresses in info or debug logs (log `user_id` instead)
- Never log raw OTP codes (the dev console fallback in `EmailService` is dev-only — guarded by `if not settings.resend_api_key`)
- Never log JWT tokens
- Never log full request bodies on auth endpoints
- Structured log fields should contain IDs, counts, and status values — not content

---

## 8.5 Error Handling and Information Leakage

Production API responses must not expose internal error details. Add a global exception handler:

```python
# main.py addition
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    if settings.is_production:
        # Never expose internal error details in production
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal error occurred."},
        )
    # Development — return the actual error for debugging
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )
```

---

## 8.6 Database Connection Security

- [ ] Database is not publicly accessible — only reachable from the application server
- [ ] Database password is strong (generated, not chosen)
- [ ] Database user has only the permissions it needs (`SELECT`, `INSERT`, `UPDATE`, `DELETE` on application tables — no `DROP`, `CREATE`, or superuser)
- [ ] Alembic migrations run from a separate user with `DDL` permissions (or run manually at deploy time)
- [ ] Connection pool size appropriate for expected load (`pool_size=10`, `max_overflow=20` for MVP)
- [ ] `pool_pre_ping=True` to detect stale connections

---

## 8.7 Monitoring and Alerting

Before accepting real users, configure:

- **Uptime monitoring** — UptimeRobot (free) pinging `/health/ready` every 5 minutes
- **Error tracking** — Sentry (free tier) capturing unhandled exceptions with context
- **Log aggregation** — Structlog JSON output piped to a log viewer (Papertrail free tier or Logtail)

Minimum alerts to configure:
- Service down (health check failing)
- Unhandled exception rate spike
- Provider error rate spike (HIBP 429s, auth failures)
- Stripe webhook processing failures

---

## 8.8 Final Pre-Launch Sequence

Complete these in order on the day of launch:

1. Run full test suite — all green
2. Run `pip-audit` — zero vulnerabilities
3. Run import direction checker — no violations
4. Deploy to production
5. Verify `/health/ready` returns 200
6. Verify HTTPS redirect works (curl `http://yourdomain.com` returns 301)
7. Check https://securityheaders.com — aim for A or A+
8. Request an OTP for a test email — verify it arrives via Resend
9. Verify the test email is registered as a verified asset after sign-in
10. Trigger a scan — verify it completes and produces findings
11. Verify Stripe checkout flow end-to-end on a test card
12. Verify Stripe webhook processes subscription update (use Stripe CLI: `stripe trigger customer.subscription.updated`)
13. Verify account deletion removes all personal data
14. Verify data export returns expected fields
15. Confirm privacy policy and terms are publicly accessible
