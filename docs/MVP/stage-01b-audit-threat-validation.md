# Stage 1b — Audit Log, Threat Model, and Input Validation

This file supplements Stage 1. These additions are integrated into the scaffold stage — they are not optional extras. Complete them before moving to Stage 2.

---

## Audit Log

### Why

For a security product, an audit trail is both a security control and a user trust signal. Without it you cannot answer "who signed in and when", "who triggered this scan", or "when was this account deleted" — questions that will come up in support, in security incidents, and from users who want to understand their own account history.

### AuditEvent Model

```python
# db/models/audit.py
import uuid
from datetime import datetime
from sqlalchemy import String, JSON, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base

class AuditEventType:
    # Auth
    SIGN_IN_REQUESTED      = "auth.sign_in_requested"
    SIGN_IN_SUCCESS        = "auth.sign_in_success"
    SIGN_IN_FAILED         = "auth.sign_in_failed"
    OTP_RATE_LIMITED       = "auth.otp_rate_limited"

    # Scans
    SCAN_TRIGGERED         = "scan.triggered"
    SCAN_COMPLETED         = "scan.completed"
    SCAN_FAILED            = "scan.failed"

    # Account
    ACCOUNT_CREATED        = "account.created"
    ACCOUNT_DELETED        = "account.deleted"
    DATA_EXPORTED          = "account.data_exported"
    TIER_CHANGED           = "account.tier_changed"

    # Assets
    ASSET_VERIFIED         = "asset.verified"

    # Findings
    FINDING_SUPPRESSED     = "finding.suppressed"
    SIGNAL_SUPPRESSED      = "signal.suppressed"


class AuditEvent(Base):
    """
    Append-only audit log. Records are never updated or deleted.
    On GDPR erasure requests, the user_id is nulled but the event
    record is retained for security and billing audit purposes.
    The event_type and metadata are retained; PII in metadata is removed.
    """
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Nullable — nulled on GDPR erasure, not deleted
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    # Structured metadata — keep IDs and counts, never PII
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_audit_user_time", "user_id", "created_at"),
        Index("ix_audit_type_time", "event_type", "created_at"),
    )
```

### Audit Repository

```python
# db/repositories/audit.py
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models.audit import AuditEvent, AuditEventType

class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log(
        self,
        event_type: str,
        user_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """
        Fire-and-forget audit logging.
        Never raises — a failed audit log must not break the operation being audited.
        """
        try:
            event = AuditEvent(
                user_id=user_id,
                event_type=event_type,
                ip_address=ip_address,
                metadata=metadata or {},
            )
            self.session.add(event)
            # Does not flush — caller's commit will persist this
        except Exception as e:
            from backend.app.core.logging import get_logger
            get_logger(__name__).error("audit.log_failed", error=str(e))

    async def get_for_user(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditEvent]:
        result = await self.session.execute(
            select(AuditEvent)
            .where(AuditEvent.user_id == user_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
```

### Where to Call Audit Logging

Add `AuditRepository.log()` calls at these points. Add it to the existing service methods — it is one line in each case.

| Location | Event type | Metadata |
|---|---|---|
| `auth/service.py` — `request_otp()` | `auth.sign_in_requested` | `{}` — no email in metadata |
| `auth/service.py` — `verify_otp()` success | `auth.sign_in_success` | `{"user_id": str}` |
| `auth/service.py` — `verify_otp()` failure | `auth.sign_in_failed` | `{}` |
| `auth/service.py` — OTP rate limit hit | `auth.otp_rate_limited` | `{}` |
| `auth/service.py` — new user created | `account.created` | `{"user_id": str}` |
| `assets/service.py` — email verified | `asset.verified` | `{"entity_type": "email"}` |
| `jobs/orchestrator.py` — scan started | `scan.triggered` | `{"scan_id": str, "tier": str}` |
| `jobs/orchestrator.py` — scan completed | `scan.completed` | `{"scan_id": str, "signals": int, "findings": int}` |
| `jobs/orchestrator.py` — scan failed | `scan.failed` | `{"scan_id": str, "error": str}` |
| `api/v1/account.py` — delete initiated | `account.deleted` | `{"user_id": str}` |
| `api/v1/account.py` — data exported | `account.data_exported` | `{"user_id": str}` |
| Stripe webhook — tier updated | `account.tier_changed` | `{"old_tier": str, "new_tier": str}` |
| Finding suppressed | `finding.suppressed` | `{"finding_id": str}` |

**Rule on metadata content:** Never log email addresses, names, or other PII in the metadata field. Log `user_id` (a UUID), counts, IDs, and status values. This means the audit log remains useful after a GDPR erasure request nulls the `user_id`.

### Audit API Endpoint

```python
# api/v1/account.py (addition)
@router.get("/audit-log")
async def get_audit_log(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Returns the authenticated user's own activity log."""
    audit_repo = AuditRepository(db)
    events = await audit_repo.get_for_user(
        user_id=current_user.id,
        limit=min(limit, 100),
        offset=offset,
    )
    return {"events": events, "limit": limit, "offset": offset}
```

---

## Threat Model

This is a one-page working document, not a formal security assessment. Write it before Stage 2. Its value is forcing you to think through the attack surface before building auth and scan logic. Revisit it as new features are added.

```markdown
# Zima — Threat Model (MVP)
Last updated: [date]
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
| OTP brute force | POST /auth/otp/verify | Medium | High | Rate limiting (10/15min/IP) + per-email lockout |
| Account enumeration | OTP request response timing | Medium | Low | Identical response for all outcomes |
| Scan abuse (scanning emails user doesn't own) | POST /scans/ | Low | High | is_verified=True gate on all scan inputs |
| JWT theft | XSS, network interception | Low | High | HTTPS, CSP, short expiry, HttpOnly cookies if browser |
| Provider key exposure | Source code, logs | Low | Critical | SecretStr, pre-commit hook, no key logging |
| Database breach | SQL injection, infra compromise | Low | Critical | ORM only, no raw queries, DB not public-facing |
| HIBP data scraping | Bulk scan triggering | Medium | Medium | Scan rate limit (5/hour/user) |
| Stripe webhook replay | Replay captured valid webhook | Low | Medium | Webhook signature verification on every request |
| GDPR data exfiltration | Authenticated data export abuse | Low | High | Export requires auth, logs to audit trail |

## Accepted Risks
- OTP delivered via email: if email is compromised, attacker can sign in.
  Mitigation: this is the same risk model as every email-based auth system.
- Provider API availability: if HIBP is down, scans degrade gracefully.
  No mitigation needed — graceful degradation is already implemented.

## Out of Scope (MVP)
- Physical access to Railway infrastructure
- Supply chain attacks on dependencies (mitigated by pip-audit in CI)
- Social engineering
```

Save this as `docs/threat-model.md` in the repository. Update it whenever a new module, provider, or API endpoint is added.

---

## Input Validation — Length Constraints on All Pydantic Schemas

Database column-level constraints produce 500 errors when exceeded. Pydantic schema-level constraints produce 422 errors with clear messages. All bounded database columns must have matching Pydantic `max_length` constraints.

### signals/schemas.py — updated

```python
from pydantic import BaseModel, Field
from backend.app.core.enums import Severity, Confidence, EntityType
import uuid

class SignalCreate(BaseModel):
    signal_type: str = Field(..., max_length=100)
    category: str = Field(..., max_length=100)
    entity_type: EntityType
    entity_id: uuid.UUID
    entity_value: str = Field(..., max_length=512)
    user_id: uuid.UUID
    severity: Severity
    confidence: Confidence
    source: str = Field(..., max_length=100)
    provider: str = Field(..., max_length=100)
    summary: str = Field(..., max_length=512)
    details: str | None = Field(None, max_length=4096)
    evidence: dict | None = None
    tags: list[str] = Field(default_factory=list, max_length=20)
    recommended_action: str | None = Field(None, max_length=512)
```

### auth/schemas.py — OTP request validation

```python
from pydantic import BaseModel, EmailStr, Field, field_validator
import re

class OTPRequest(BaseModel):
    email: EmailStr
    # Privacy policy acceptance required on first sign-in
    privacy_policy_accepted: bool = False

class OTPVerify(BaseModel):
    email: EmailStr
    # Code must be exactly 6 digits — reject anything else before touching the DB
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
```

The `pattern=r"^\d{6}$"` on the OTP code means non-numeric inputs and wrong-length codes are rejected by Pydantic before any database query runs. This eliminates a class of injection attempts and reduces unnecessary DB load.

### Pagination parameters — consistent across all list endpoints

```python
# core/schemas.py — shared pagination schema
from pydantic import BaseModel, Field

class PaginationParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
```

Use this on every list endpoint. `ge=1, le=100` means limit is always 1-100. `ge=0` means offset is always non-negative. Import and use rather than repeating `min(limit, 100)` inline in every endpoint.

### Asset value validation

```python
# assets/schemas.py
from pydantic import BaseModel, EmailStr, Field, field_validator
from backend.app.core.enums import EntityType

class AssetCreate(BaseModel):
    entity_type: EntityType
    value: str = Field(..., min_length=1, max_length=512)

    @field_validator("value")
    @classmethod
    def strip_and_lowercase(cls, v: str, info) -> str:
        """Normalise email values before storage."""
        return v.strip().lower()
```

### Finding and signal suppression request schemas

These are needed for the suppression endpoints added in Stage 6b:

```python
# findings/schemas.py
from pydantic import BaseModel, Field

class SuppressRequest(BaseModel):
    reason: str | None = Field(None, max_length=256)
```
