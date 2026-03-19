# Zima — Threat Model (MVP)
Last updated: 2026-03-19
Scope: MVP backend API

## Assets to Protect
| Asset | Sensitivity | Location |
|---|---|---|
| User email addresses | High — PII | users table, assets table, auth_tokens table |
| Breach findings | High — sensitive personal data | signals table, findings table |
| JWTs | High — grants API access | client-side only |
| OTP codes | High — grants sign-in | auth_tokens table (hashed) |
| Provider API keys | Critical — enables data access | Environment variables / Railway secrets |
| Stripe keys | Critical — payment processing | Environment variables / Railway secrets |

## Threat Actors
| Actor | Motivation | Capability |
|---|---|---|
| Opportunistic attacker | Credential harvesting, data resale | Low-medium — automated tools |
| Targeted attacker | Access specific user's breach data | Medium — scripted attacks |
| Malicious user | Scan emails they don't own | Low — authenticated access only |
| Scrapers | Bulk breach data extraction | Medium — API abuse |

## Threat Matrix
| Threat | Attack Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| OTP brute force | POST /auth/otp/verify | Medium | High | Rate limiting (10/15min/IP, Redis-backed, shared across workers) + per-email lockout after 5 consecutive failures (15-min window) |
| Account enumeration | OTP request response timing | Medium | Low | Identical response for all outcomes |
| Scan abuse (scanning emails user doesn't own) | POST /scans/ | Low | High | is_verified=True gate on all scan inputs |
| JWT theft | XSS, network interception | Low | High | HTTPS, CSP, short expiry, HttpOnly cookies if browser |
| Provider key exposure | Source code, logs | Low | Critical | SecretStr, pre-commit hook, no key logging |
| Database breach | SQL injection, infra compromise | Low | Critical | ORM only, no raw queries, DB not public-facing |
| HIBP data scraping | Bulk scan triggering | Medium | Medium | Scan rate limit (5/hour/user) |
| Stripe webhook replay | Replay captured valid webhook | Low | Medium | Webhook signature verification on every request |
| GDPR data exfiltration | Authenticated data export abuse | Low | High | Export requires auth, logs to audit trail |

## Rate Limiter Behaviour

The rate limiter (slowapi + Redis) is **fail-open**: if Redis becomes transiently unavailable after startup, requests are allowed through rather than blocked. At startup, a Redis connection failure raises immediately (fail-closed). Monitor Redis availability and alert on connection failures to avoid unprotected windows.

The per-IP key is extracted from `X-Forwarded-For` (leftmost entry) then `X-Real-IP`, then `request.client.host`. On Railway all traffic is proxied through the load balancer, so the XFF value is authoritative.

## Accepted Risks
- OTP delivered via email: if email is compromised, attacker can sign in.
  Mitigation: this is the same risk model as every email-based auth system.
- Provider API availability: if HIBP is down, scans degrade gracefully.
  No mitigation needed — graceful degradation is already implemented.
- Transient Redis outage disables IP-based rate limiting. Per-email lockout
  (DB-backed) remains active regardless of Redis state.

## Out of Scope (MVP)
- Physical access to Railway infrastructure
- Supply chain attacks on dependencies (mitigated by pip-audit in CI)
- Social engineering
