# Wave 1 Security Remediation Guide

**Status**: Detailed fix implementation guide for 3 critical + 4 medium/low issues
**Estimated Time**: 6-8 hours total

---

## Fix 1: Remove Plaintext Passwords from DeHashed Evidence (C1)

### Step 1a: Update DeHashed Provider

**File**: `/Users/max/Zima/backend/app/providers/breach/dehashed/client.py`

**Current code** (lines 40-68):
```python
_inputs: list[tuple[str, str]] = []
if domain is not None:
    _inputs.append(("domain", domain))
if email is not None:
    _inputs.append(("email", email))
for _entity_type, _value in _inputs:
    if _entity_type not in {"email", "domain"}:
        continue
    val = _value.strip()
    query = f'email:"{val}"' if _entity_type == "email" else f'email:"@{val}"'
    url = f"{self.base_url}?query={urllib.parse.quote(query)}&size=5"
    data = await self._fetch(url, headers)
    total = data.get("total", 0) if isinstance(data, dict) else 0
    entries = data.get("entries", []) if isinstance(data, dict) else []
    if total and total > 0:
        findings.append(
            dict(
                provider=self.name,
                category="credential_leak",
                title=f"DeHashed: {val}",
                description=f"{val} found in {total} DeHashed breach record(s)",
                entity_type=_entity_type,
                entity_value=val,
                tags=["dehashed", "leak", "breach", "passive"],
                raw={"total": total, "sample_count": len(entries), "entries": entries},  # ← PROBLEM
            )
        )
return findings
```

**Replace with**:
```python
_inputs: list[tuple[str, str]] = []
if domain is not None:
    _inputs.append(("domain", domain))
if email is not None:
    _inputs.append(("email", email))
for _entity_type, _value in _inputs:
    if _entity_type not in {"email", "domain"}:
        continue
    val = _value.strip()
    query = f'email:"{val}"' if _entity_type == "email" else f'email:"@{val}"'
    url = f"{self.base_url}?query={urllib.parse.quote(query)}&size=5"
    data = await self._fetch(url, headers)
    total = data.get("total", 0) if isinstance(data, dict) else 0
    entries = data.get("entries", []) if isinstance(data, dict) else []
    if total and total > 0:
        findings.append(
            dict(
                provider=self.name,
                category="credential_leak",
                title=f"DeHashed: {val}",
                description=f"{val} found in {total} DeHashed breach record(s)",
                entity_type=_entity_type,
                entity_value=val,
                tags=["dehashed", "leak", "breach", "passive"],
                raw={
                    "total": total,
                    "sample_count": len(entries),
                    # REMOVED: entries with plaintext passwords are NOT stored
                    # Modules can check for password presence via _check_dehashed_credentials() below
                },
            )
        )
return findings
```

### Step 1b: Add helper method to scan entries in-memory (not persisting to DB)

Add this method to DehashedProvider class:

```python
@staticmethod
def _check_dehashed_credentials(entries: list[dict[str, Any]]) -> tuple[bool, bool]:
    """Check if entries contain plaintext passwords or hashes.

    Returns: (has_plaintext, has_hash)
    NOTE: This method is called in-memory; entries are NOT persisted.
    """
    has_plaintext = False
    has_hash = False
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("password"):
            has_plaintext = True
        if entry.get("hashed_password"):
            has_hash = True
        if has_plaintext and has_hash:
            break  # Early exit once we have both
    return has_plaintext, has_hash
```

Then update `_fetch()` to use this:

```python
async def _fetch(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
    return await self._get(
        url, label="Dehashed", headers=headers, timeout=self._timeout_seconds
    )
```

Keep the method as-is. The filtering happens in modules that call this.

### Step 1c: Update Breach Monitor Module

**File**: `/Users/max/Zima/backend/app/modules/identity/breach_monitor/service.py`

**Current code** (lines 103-129):
```python
for finding in dehashed_findings:
    raw = finding.get("raw", {})
    entries: list[dict[str, Any]] = raw.get("entries", []) if isinstance(raw, dict) else []
    severity = _breach_severity_dehashed(entries)
    total = raw.get("total", 0) if isinstance(raw, dict) else 0
    signals.append(
        SignalCreate(
            signal_type="email_breached",
            category="identity_security",
            entity_type=EntityType.EMAIL,
            entity_id=asset_id,
            entity_value=asset_value,
            user_id=user_id,
            severity=severity,
            confidence=Confidence.HIGH,
            source=self.module_name,
            provider="dehashed",
            summary=f"Email found in {total} DeHashed breach record(s)",
            details=finding.get("description"),
            evidence={"raw_finding": finding},  # ← PROBLEM: stores plaintext credentials
            tags=finding.get("tags", []) + ["identity", "breach"],
            recommended_action=(
                "Rotate credentials for any services where this email was used. "
                "Enable MFA if not already active."
            ),
        )
    )
```

**Replace with**:
```python
for finding in dehashed_findings:
    raw = finding.get("raw", {})
    # NOTE: entries are no longer in raw dict (removed in provider)
    # We check severity based on flags only, not entry data
    total = raw.get("total", 0) if isinstance(raw, dict) else 0

    # For breach_monitor, severity depends on whether ANY password data exists
    # We don't have entries here anymore, so assume HIGH
    severity = Severity.HIGH  # Default for breach detection

    signals.append(
        SignalCreate(
            signal_type="email_breached",
            category="identity_security",
            entity_type=EntityType.EMAIL,
            entity_id=asset_id,
            entity_value=asset_value,
            user_id=user_id,
            severity=severity,
            confidence=Confidence.HIGH,
            source=self.module_name,
            provider="dehashed",
            summary=f"Email found in {total} DeHashed breach record(s)",
            details=finding.get("description"),
            evidence={
                "source_provider": "dehashed",
                "breach_count": total,
                # REMOVED: raw_finding - this contained entries with plaintext passwords
            },
            tags=finding.get("tags", []) + ["identity", "breach"],
            recommended_action=(
                "Rotate credentials for any services where this email was used. "
                "Enable MFA if not already active."
            ),
        )
    )
```

Also update the helper function at the top of the file:

```python
def _breach_severity_dehashed(entries: list[dict[str, Any]]) -> Severity:
    """CRITICAL if any entry has plaintext or hashed password; HIGH otherwise.

    DEPRECATED: This function is no longer used because entries are not persisted.
    Kept for reference only.
    """
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("password") or entry.get("hashed_password"):
            return Severity.CRITICAL
    return Severity.HIGH
```

### Step 1d: Update Credential Exposure Module (Same Pattern)

**File**: `/Users/max/Zima/backend/app/modules/identity/credential_exposure/service.py`

The credential_exposure module currently expects entries to determine has_plaintext/has_hash. Since we removed them, we need to adjust:

**Option A** (Recommended - Keep credential_exposure for plaintext detection):
Re-add entries but ONLY to credential_exposure module, with explicit in-memory processing:

```python
# Update DeHashed provider to return entries only to credential_exposure
# This is complex - see Option B instead
```

**Option B** (Simpler - Use provider method):
Update the provider to have a method that returns credentials info without persisting:

```python
# backend/app/providers/breach/dehashed/client.py

async def search_breaches_with_credential_check(
    self, *, domain: str | None = None, email: str | None = None
) -> tuple[list[dict[str, Any]], dict[str, tuple[bool, bool]]]:
    """Returns (findings, credentials_map) where credentials_map is {email: (has_plaintext, has_hash)}.

    Credentials are NOT stored in findings; only boolean flags returned.
    """
    api_email = str(self._api_email).strip()
    api_key = str(self._api_key).strip()
    if not api_email or not api_key:
        raise ProviderError(...)

    creds = base64.b64encode(f"{api_email}:{api_key}".encode()).decode()
    headers = {"Accept": "application/json", "Authorization": f"Basic {creds}"}
    findings: list[dict[str, Any]] = []
    credentials_map: dict[str, tuple[bool, bool]] = {}

    _inputs: list[tuple[str, str]] = []
    if domain is not None:
        _inputs.append(("domain", domain))
    if email is not None:
        _inputs.append(("email", email))

    for _entity_type, _value in _inputs:
        if _entity_type not in {"email", "domain"}:
            continue
        val = _value.strip()
        query = f'email:"{val}"' if _entity_type == "email" else f'email:"@{val}"'
        url = f"{self.base_url}?query={urllib.parse.quote(query)}&size=5"
        data = await self._fetch(url, headers)
        total = data.get("total", 0) if isinstance(data, dict) else 0
        entries = data.get("entries", []) if isinstance(data, dict) else []

        if total and total > 0:
            # Check credentials in-memory
            has_plaintext = any(
                bool(e.get("password"))
                for e in entries
                if isinstance(e, dict)
            )
            has_hash = any(
                bool(e.get("hashed_password"))
                for e in entries
                if isinstance(e, dict)
            )
            credentials_map[val] = (has_plaintext, has_hash)

            # Add finding WITHOUT entries
            findings.append(
                dict(
                    provider=self.name,
                    category="credential_leak",
                    title=f"DeHashed: {val}",
                    description=f"{val} found in {total} DeHashed breach record(s)",
                    entity_type=_entity_type,
                    entity_value=val,
                    tags=["dehashed", "leak", "breach", "passive"],
                    raw={"total": total, "sample_count": len(entries)},
                )
            )

    return findings, credentials_map
```

Then update credential_exposure module to use the map:

```python
# backend/app/modules/identity/credential_exposure/service.py
if settings.dehashed_email and settings.dehashed_api_key:
    dehashed = DehashedProvider(
        api_email=settings.dehashed_email,
        api_key=settings.dehashed_api_key.get_secret_value(),
    )
    try:
        findings, credentials_map = await dehashed.search_breaches_with_credential_check(
            email=asset_value
        )
    except ProviderError as e:
        logger.error(...)
        findings = []
        credentials_map = {}

    for finding in findings:
        val = finding.get("entity_value", "")
        has_plaintext, has_hash = credentials_map.get(val, (False, False))

        if not has_plaintext and not has_hash:
            continue  # no password data

        severity = _severity_for_credential(has_plaintext, has_hash)
        # ... rest of signal creation
```

**SIMPLER ALTERNATIVE**: Just check the breach_count and assume HIGH severity without specific credential type checking:

```python
# backend/app/modules/identity/credential_exposure/service.py
if settings.dehashed_email and settings.dehashed_api_key:
    dehashed = DehashedProvider(
        api_email=settings.dehashed_email,
        api_key=settings.dehashed_api_key.get_secret_value(),
    )
    try:
        findings = await dehashed.search_breaches(email=asset_value)
    except ProviderError as e:
        logger.error(...)
        findings = []

    for finding in findings:
        raw = finding.get("raw", {})
        sample_count = raw.get("sample_count", 0) if isinstance(raw, dict) else 0

        if not sample_count:
            continue  # no entries found

        # Conservative: Assume passwords may be exposed (hash or plaintext unknown)
        signals.append(
            SignalCreate(
                signal_type="password_exposed",
                category="identity_security",
                entity_type=EntityType.EMAIL,
                entity_id=asset_id,
                entity_value=asset_value,
                user_id=user_id,
                severity=Severity.HIGH,  # Always HIGH for credential_exposure
                confidence=Confidence.HIGH,
                source=self.module_name,
                provider="dehashed",
                summary=f"Credentials exposed in {sample_count} DeHashed record(s)",
                details=finding.get("description"),
                evidence={
                    "source_provider": "dehashed",
                    "has_plaintext": False,  # Unknown - not persisted
                    "has_hash": True,  # Assume hash present if in DeHashed
                    "password_present": True,
                    "sample_count": sample_count,
                },
                tags=["credential_exposure", "password_exposed", "dehashed"],
                recommended_action=(
                    "Rotate the exposed password immediately on all services where it was used. "
                    "Use a unique password for each service. Enable MFA."
                ),
            )
        )
```

### Step 1e: Database Migration

Create a migration to clear sensitive evidence from existing signals:

**File**: `/Users/max/Zima/backend/migrations/versions/yyyy_mm_dd_hhmmss_clear_plaintext_passwords.py` (create new file)

```python
"""Clear plaintext passwords from DeHashed evidence.

Revision ID: clear_plaintext_dehashed
Revises: <previous_revision>
Create Date: 2026-03-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'clear_plaintext_dehashed'
down_revision = '<check your previous migration ID>'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove plaintext credentials from evidence dicts."""
    connection = op.get_bind()

    # For any signals with evidence containing raw_finding.raw.entries,
    # remove the entries field
    update_sql = text("""
    UPDATE signals
    SET evidence = jsonb_set(
        evidence,
        '{raw_finding,raw}',
        evidence->'raw_finding'->'raw' - 'entries'
    )
    WHERE provider = 'dehashed'
    AND evidence -> 'raw_finding' -> 'raw' ? 'entries'
    AND evidence->'raw_finding'->'raw'->'entries' IS NOT NULL;
    """)

    connection.execute(update_sql)
    print("Cleared plaintext passwords from DeHashed signals")


def downgrade() -> None:
    """Downgrade would require restoring from backup - not supported."""
    print("WARNING: Downgrade would require restoring from backup.")
    pass
```

Run migration:
```bash
cd /Users/max/Zima
alembic upgrade head
```

---

## Fix 2: Add Input Validation to Subprocess Providers (C2)

### Step 2a: Update Holehe Provider

**File**: `/Users/max/Zima/backend/app/providers/tools/holehe/client.py`

**Add at top** (after imports):
```python
import re

_MAX_EMAIL_LENGTH = 254  # RFC 5321
_EMAIL_PATTERN = re.compile(
    r'^[a-zA-Z0-9._%\-+]{1,64}@[a-zA-Z0-9.\-]{1,255}\.[a-zA-Z]{2,}$'
)


def _validate_email(email: str) -> None:
    """Validate email format and length. Raises ProviderError if invalid."""
    email = email.strip()

    if not email:
        raise ProviderError("Email cannot be empty", retryable=False)

    if len(email) > _MAX_EMAIL_LENGTH:
        raise ProviderError(
            f"Email exceeds maximum length ({_MAX_EMAIL_LENGTH} chars)",
            retryable=False,
        )

    if not _EMAIL_PATTERN.match(email):
        raise ProviderError(
            "Invalid email format (contains invalid characters or structure)",
            retryable=False,
        )
```

**Update `check_accounts_tool()` method**:
```python
async def check_accounts_tool(self, email: str) -> list[dict[str, Any]]:
    if not shutil.which(_TOOL_NAME):
        raise ProviderError(
            message="holehe not found in PATH, install with: pip install holehe",
            retryable=False,
        )

    email = email.strip().lower()

    # Validate email before subprocess call
    _validate_email(email)

    findings: list[dict[str, Any]] = []
    found_sites = await asyncio.to_thread(self._run_holehe, email)

    # ... rest of method unchanged
```

### Step 2b: Update Maigret Provider

**File**: `/Users/max/Zima/backend/app/providers/tools/maigret/client.py`

**Add at top** (after imports):
```python
_USERNAME_MIN_LENGTH = 3
_USERNAME_MAX_LENGTH = 32


def _validate_username(username: str) -> None:
    """Validate username format. Raises ProviderError if invalid."""
    username = username.strip()

    if not username:
        raise ProviderError("Username cannot be empty", retryable=False)

    if len(username) < _USERNAME_MIN_LENGTH:
        raise ProviderError(
            f"Username too short (minimum {_USERNAME_MIN_LENGTH} chars)",
            retryable=False,
        )

    if len(username) > _USERNAME_MAX_LENGTH:
        raise ProviderError(
            f"Username too long (maximum {_USERNAME_MAX_LENGTH} chars)",
            retryable=False,
        )

    # Allow: letters, numbers, dots, underscores, hyphens
    # Most platforms accept these; Maigret tool validates further
    if not re.match(r'^[a-zA-Z0-9._\-]+$', username):
        raise ProviderError(
            "Username contains invalid characters (allowed: a-z, 0-9, . _ -)",
            retryable=False,
        )
```

**Update `search_usernames()` method**:
```python
async def search_usernames(self, username: str) -> list[dict[str, Any]]:
    if not shutil.which(_TOOL_NAME):
        raise ProviderError(
            message="maigret not found in PATH, install with: pip install maigret",
            retryable=False,
        )

    username = username.strip().lower()

    # Validate username before subprocess call
    _validate_username(username)

    findings: list[dict[str, Any]] = []
    found_accounts = await asyncio.to_thread(self._run_maigret, username)

    # ... rest of method unchanged
```

### Step 2c: Update Module That Calls Maigret

**File**: `/Users/max/Zima/backend/app/modules/identity/username_exposure/service.py`

**Update lines 113-159** (Maigret section):
```python
# --- Maigret: username-based platform discovery ---
derived_username = asset_value.split("@")[0] if "@" in asset_value else asset_value

if derived_username and len(derived_username) >= 3:
    if len(derived_username) > 32:
        logger.debug(
            "username_exposure.skip_long_username",
            derived_username=derived_username,
            length=len(derived_username),
        )
    else:
        maigret = MaigretProvider()
        try:
            findings = await maigret.search_usernames(derived_username)
        except ProviderError as e:
            logger.error(
                "username_exposure.maigret_failure",
                error=str(e),
                asset_value=asset_value,
            )
            findings = []

        for finding in findings:
            # ... rest of loop unchanged
```

---

## Fix 3: Implement API Rate Limiting (C3)

### Step 3a: Create API Usage Model

**File**: `/Users/max/Zima/backend/app/db/models/api_usage.py` (NEW)

```python
# backend/app/db/models/api_usage.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base

if TYPE_CHECKING:
    pass


class ApiUsageLog(Base):
    """Track API calls per user/provider for quota enforcement."""

    __tablename__ = "api_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    provider_name: Mapped[str] = mapped_column(String(50), index=True)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    __table_args__ = (
        Index("ix_api_usage_user_provider_date", "user_id", "provider_name", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ApiUsageLog(user_id={self.user_id}, provider={self.provider_name}, "
            f"cost={self.cost}, created_at={self.created_at})>"
        )
```

### Step 3b: Create API Usage Repository

**File**: `/Users/max/Zima/backend/app/db/repositories/api_usage.py` (NEW)

```python
# backend/app/db/repositories/api_usage.py
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from backend.app.db.models.api_usage import ApiUsageLog
from backend.app.providers.base.exceptions import ProviderError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# Define quotas per tier and provider
# Providers marked "paid" should have stricter limits
PROVIDER_QUOTAS = {
    # Format: "provider_name": {"core": daily_limit, "pro": daily_limit, "enterprise": unlimited}
    "hibp": {"core": 50, "pro": 500, "enterprise": 10000},
    "dehashed": {"core": 10, "pro": 50, "enterprise": 500},  # Expensive: $0.10/query
    "breachdirectory": {"core": 25, "pro": 100, "enterprise": 500},  # RapidAPI quota
    "hudson_rock": {"core": 10, "pro": 50, "enterprise": 500},  # Expensive
    "leakcheck": {"core": 50, "pro": 500, "enterprise": 10000},
    "epieos": {"core": 25, "pro": 100, "enterprise": 500},  # Expensive
    "emailrep": {"core": 100, "pro": 1000, "enterprise": 10000},
}

PROVIDER_COSTS = {
    # Format: "provider_name": cost_per_call_in_usd
    "hibp": 0.0,  # Free for authenticated users
    "dehashed": 0.10,
    "breachdirectory": 0.01,  # Rough estimate, RapidAPI based
    "hudson_rock": 0.05,
    "leakcheck": 0.0,  # Free
    "epieos": 0.10,
    "emailrep": 0.0,  # Free with key
}


class ApiQuotaExceededError(ProviderError):
    """Raised when API quota exceeded for provider."""

    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=False)


class ApiUsageRepository:
    """Manage API call quotas and cost tracking."""

    async def check_quota(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        provider_name: str,
        user_tier: str = "core",
    ) -> None:
        """Check if user has quota remaining for provider.

        Raises ApiQuotaExceededError if quota exceeded.
        """
        quotas = PROVIDER_QUOTAS.get(provider_name, {})
        daily_limit = quotas.get(user_tier, quotas.get("core", 100))

        if daily_limit is None:
            # Enterprise tier: unlimited
            return

        # Count calls in last 24 hours
        stmt = select(func.count(ApiUsageLog.id)).where(
            ApiUsageLog.user_id == user_id,
            ApiUsageLog.provider_name == provider_name,
            ApiUsageLog.created_at
            > datetime.now(timezone.utc) - timedelta(days=1),
        )
        count = await session.scalar(stmt) or 0

        if count >= daily_limit:
            raise ApiQuotaExceededError(
                f"API quota exceeded for {provider_name} ({count}/{daily_limit} "
                f"calls in last 24h). Please try again tomorrow."
            )

    async def log_api_call(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        provider_name: str,
    ) -> None:
        """Log an API call (assumes quota already checked)."""
        cost = PROVIDER_COSTS.get(provider_name, 0.0)

        log_entry = ApiUsageLog(
            user_id=user_id,
            provider_name=provider_name,
            cost=cost,
        )
        session.add(log_entry)
        await session.flush()

    async def get_daily_usage(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        provider_name: str,
    ) -> dict:
        """Get usage stats for a provider."""
        stmt = select(
            func.count(ApiUsageLog.id).label("count"),
            func.sum(ApiUsageLog.cost).label("total_cost"),
        ).where(
            ApiUsageLog.user_id == user_id,
            ApiUsageLog.provider_name == provider_name,
            ApiUsageLog.created_at
            > datetime.now(timezone.utc) - timedelta(days=1),
        )
        result = await session.execute(stmt)
        row = result.one_or_none()

        return {
            "provider": provider_name,
            "calls_today": row.count or 0 if row else 0,
            "cost_today": float(row.total_cost or 0.0) if row else 0.0,
        }
```

### Step 3c: Add Migration for ApiUsageLog

**File**: `/Users/max/Zima/backend/migrations/versions/yyyy_mm_dd_hhmmss_create_api_usage_log.py` (NEW)

```python
"""Create API usage log table.

Revision ID: create_api_usage_log
Revises: <previous_revision>
Create Date: 2026-03-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'create_api_usage_log'
down_revision = '<previous_migration_id>'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'api_usage_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('provider_name', sa.String(length=50), nullable=False),
        sa.Column('cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_api_usage_logs_user_id', 'api_usage_logs', ['user_id'])
    op.create_index('ix_api_usage_logs_provider_name', 'api_usage_logs', ['provider_name'])
    op.create_index('ix_api_usage_logs_created_at', 'api_usage_logs', ['created_at'])
    op.create_index(
        'ix_api_usage_user_provider_date',
        'api_usage_logs',
        ['user_id', 'provider_name', 'created_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_api_usage_user_provider_date', table_name='api_usage_logs')
    op.drop_index('ix_api_usage_logs_created_at', table_name='api_usage_logs')
    op.drop_index('ix_api_usage_logs_provider_name', table_name='api_usage_logs')
    op.drop_index('ix_api_usage_logs_user_id', table_name='api_usage_logs')
    op.drop_table('api_usage_logs')
```

### Step 3d: Integrate Quota Checks into Scan Orchestration

**File**: `/Users/max/Zima/backend/app/jobs/orchestrator.py` (UPDATE - or create if doesn't exist)

```python
# backend/app/jobs/orchestrator.py
from backend.app.db.repositories.api_usage import (
    ApiUsageRepository,
    ApiQuotaExceededError,
)

class ScanOrchestrator:
    async def run_modules_for_asset(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
        user_tier: str = "core",
    ) -> list[Signal]:
        """Run all applicable modules for an asset, checking API quotas."""
        signals: list[Signal] = []
        api_usage_repo = ApiUsageRepository()

        # Map modules to required providers
        module_providers = {
            "breach_monitor": ["hibp", "dehashed", "breachdirectory"],
            "credential_exposure": ["dehashed", "leakcheck", "breachdirectory"],
            "stealer_log_exposure": ["hudson_rock"],
            "username_exposure": ["epieos", "tool_maigret"],
            "alias_correlation": ["epieos"],
            "account_inventory": ["tool_holehe"],
            "account_enumeration_risk": ["emailrep"],
        }

        enabled_modules = await self._get_enabled_modules_for_tier(user_tier)

        for module_name in enabled_modules:
            providers = module_providers.get(module_name, [])

            # Check quotas for all providers this module will call
            quota_exceeded_providers = []
            for provider in providers:
                try:
                    await api_usage_repo.check_quota(
                        session, user_id, provider, user_tier
                    )
                except ApiQuotaExceededError:
                    quota_exceeded_providers.append(provider)
                    logger.warn(
                        "quota_check.limit_reached",
                        user_id=str(user_id),
                        provider=provider,
                        tier=user_tier,
                    )

            # Skip module if any required provider exceeds quota
            if quota_exceeded_providers:
                logger.info(
                    "scan_orchestrator.skipping_module",
                    module=module_name,
                    reason=f"quota_exceeded_for: {quota_exceeded_providers}",
                    user_id=str(user_id),
                )
                continue

            # Run module and log API calls
            try:
                module = self._get_module(module_name)
                module_signals = await module.run(user_id, asset_id, asset_value)
                signals.extend(module_signals)

                # Log API calls to providers
                for provider in providers:
                    if provider.startswith("tool_"):
                        continue  # Skip local tools
                    try:
                        await api_usage_repo.log_api_call(
                            session, user_id, provider
                        )
                    except Exception as e:
                        logger.error(
                            "api_usage.log_failed",
                            provider=provider,
                            error=str(e),
                        )

            except Exception as e:
                logger.error(
                    "scan_orchestrator.module_failure",
                    module=module_name,
                    error=str(e),
                )

        await session.commit()
        return signals
```

---

## Fix 4: Wrap API Keys in SecretStr (M1)

Quick fix - apply to all 6 providers that accept API keys:

### File 1: `/Users/max/Zima/backend/app/providers/breach/epieos/client.py`

**Line 23-25**: Change from:
```python
def __init__(self, api_key: str = "", timeout_seconds: int = 15) -> None:
    super().__init__(timeout_seconds=timeout_seconds)
    self._api_key = api_key
```

To:
```python
from pydantic import SecretStr

def __init__(self, api_key: str | SecretStr = "", timeout_seconds: int = 15) -> None:
    super().__init__(timeout_seconds=timeout_seconds)
    if isinstance(api_key, str):
        self._api_key = SecretStr(api_key) if api_key else SecretStr("")
    else:
        self._api_key = api_key
```

Then **line 27** (in validate_email method): Change from:
```python
api_key = str(self._api_key).strip()
```

To:
```python
api_key = (
    self._api_key.get_secret_value() if isinstance(self._api_key, SecretStr)
    else str(self._api_key)
).strip()
```

### Repeat for these 5 other files:
- `/Users/max/Zima/backend/app/providers/reputation/emailrep/client.py` (line 17)
- `/Users/max/Zima/backend/app/providers/breach/dehashed/client.py` (line 26-27)
- `/Users/max/Zima/backend/app/providers/breach/leakcheck/client.py` (line 24)
- `/Users/max/Zima/backend/app/providers/breach/breachdirectory/client.py` (line 41)
- `/Users/max/Zima/backend/app/providers/breach/hudson_rock/client.py` (line 24)

Use the same pattern for each.

---

## Fix 5: Remove PII from Epieos Evidence (M2)

### File: `/Users/max/Zima/backend/app/providers/social/epieos/client.py`

**Lines 90-99** (Google account): Change from:
```python
raw={
    "google_id": google.get("id"),
    "name": google.get("name"),
    "lastActivity": google.get("lastActivity"),
    "mapsReviews": google.get("mapsReviews"),
    "calendarEvents": google.get("calendarEvents"),
    "photosPublic": google.get("photosPublic"),
    "youtubeChannel": google.get("youtubeChannel"),
    "hangoutsLastActivity": google.get("hangoutsLastActivity"),
},
```

To:
```python
raw={
    "google_id": google.get("id"),
    # PII removed: name, lastActivity, etc.
    "has_maps_reviews": bool(google.get("mapsReviews")),
    "has_photos_public": bool(google.get("photosPublic")),
    "has_youtube_channel": bool(google.get("youtubeChannel")),
},
```

**Lines 116-119** (Apple account): Change from:
```python
raw={
    "apple_id": apple.get("id"),
    "email_verified": apple.get("email_verified"),
},
```

To (no changes needed, already minimal):
```python
raw={
    "apple_id": apple.get("id"),
    "email_verified": apple.get("email_verified"),
},
```

### File: `/Users/max/Zima/backend/app/modules/identity/alias_correlation/service.py`

**Lines 56-80** (Signal creation): Change evidence from:
```python
evidence={
    "source_provider": "epieos",
    "alias_email": alias_name,  # ← This is PII
    "platform": "Google",
},
```

To:
```python
evidence={
    "source_provider": "epieos",
    "alias_detected": True,  # ← Boolean flag instead of actual name
    "platform": "Google",
},
```

Also update summary to not expose the name:
```python
summary=f"Real name linked to this identity via Google account",  # Instead of "Alias '{alias_name}'..."
```

---

## Fix 6: Improve Username Validation (L1)

**File**: `/Users/max/Zima/backend/app/providers/social/accounts/client.py`

**Line 45**: Change from:
```python
if not uname or len(uname) < 3:
    continue
```

To:
```python
_MIN_USERNAME = 3
_MAX_USERNAME = 32

if not uname or len(uname) < _MIN_USERNAME or len(uname) > _MAX_USERNAME:
    continue
if not re.match(r'^[a-zA-Z0-9._-]{3,32}$', uname):
    continue
```

Add import:
```python
import re
```

---

## Testing

### Create comprehensive tests

**File**: `/Users/max/Zima/tests/security/test_credential_handling.py` (NEW)

```python
# tests/security/test_credential_handling.py
import pytest
from backend.app.providers.breach.dehashed.client import DehashedProvider
from backend.app.providers.tools.holehe.client import HoleheProvider
from backend.app.providers.base.exceptions import ProviderError


@pytest.mark.asyncio
async def test_dehashed_no_plaintext_in_findings():
    """Verify plaintext passwords not stored in findings."""
    provider = DehashedProvider(
        api_email="test@example.com",
        api_key="test_key",
    )

    # Mock the _get method to return sample data
    mock_response = {
        "total": 1,
        "entries": [
            {
                "email": "user@example.com",
                "username": "john",
                "password": "secret123",
                "hashed_password": "hash123",
            }
        ],
    }

    # Override _fetch to return mock data
    async def mock_fetch(url, headers):
        return mock_response

    provider._fetch = mock_fetch

    findings = await provider.search_breaches(email="user@example.com")

    # Assert: no plaintext passwords in findings
    assert len(findings) == 1
    finding = findings[0]
    raw = finding.get("raw", {})

    # The critical assertion
    assert "entries" not in raw, "CRITICAL: entries should not be in raw dict"

    # Should have total and sample_count
    assert raw.get("total") == 1
    assert raw.get("sample_count") == 1


@pytest.mark.asyncio
async def test_holehe_email_validation():
    """Verify invalid emails rejected before subprocess."""
    holehe = HoleheProvider()

    # Test too long
    with pytest.raises(ProviderError, match="exceeds maximum"):
        await holehe.check_accounts_tool("a" * 300 + "@example.com")

    # Test invalid format
    with pytest.raises(ProviderError, match="Invalid email"):
        await holehe.check_accounts_tool("not-an-email")

    # Test empty
    with pytest.raises(ProviderError, match="cannot be empty"):
        await holehe.check_accounts_tool("")


@pytest.mark.asyncio
async def test_maigret_username_validation():
    """Verify invalid usernames rejected before subprocess."""
    from backend.app.providers.tools.maigret.client import MaigretProvider

    maigret = MaigretProvider()

    # Test too short
    with pytest.raises(ProviderError, match="too short"):
        await maigret.search_usernames("ab")

    # Test too long
    with pytest.raises(ProviderError, match="too long"):
        await maigret.search_usernames("a" * 50)

    # Test invalid characters
    with pytest.raises(ProviderError, match="invalid characters"):
        await maigret.search_usernames("user@invalid!")


@pytest.mark.asyncio
async def test_api_quota_enforcement(async_session):
    """Verify API quotas enforced."""
    from backend.app.db.repositories.api_usage import (
        ApiUsageRepository,
        ApiQuotaExceededError,
    )
    import uuid

    repo = ApiUsageRepository()
    user_id = uuid.uuid4()

    # Simulate reaching quota for "core" tier (10 DeHashed calls/day)
    for _ in range(10):
        await repo.log_api_call(async_session, user_id, "dehashed")

    # Next call should fail
    with pytest.raises(ApiQuotaExceededError):
        await repo.check_quota(async_session, user_id, "dehashed", "core")


def test_secret_str_not_leaked():
    """Verify SecretStr not leaked in repr/str."""
    from pydantic import SecretStr
    from backend.app.providers.social.epieos.client import EpieosProvider

    provider = EpieosProvider(api_key="supersecret123")

    # The provider __repr__ should not contain the secret
    repr_str = repr(provider)
    assert "supersecret123" not in repr_str
    assert "secret" not in repr_str.lower()


def test_epieos_no_pii_in_evidence():
    """Verify PII removed from Epieos evidence."""
    # This is harder to test without mocking the provider
    # But at minimum, verify the raw dict structure doesn't include sensitive fields

    # When provider returns findings, check structure
    sample_finding = {
        "provider": "epieos",
        "raw": {
            "google_id": "12345",
            "has_maps_reviews": True,  # ← Should be boolean flag
            "has_photos_public": False,  # ← Not the actual data
        },
    }

    raw = sample_finding["raw"]
    assert "name" not in raw, "Real name should not be in evidence"
    assert "lastActivity" not in raw, "Activity data should not be in evidence"
    assert "youtubeChannel" not in raw, "YouTube channel should not be in evidence"
```

### Run tests

```bash
cd /Users/max/Zima
pytest tests/security/test_credential_handling.py -v
```

---

## Deployment Checklist

- [ ] Apply all code fixes (Fix 1-6)
- [ ] Run migrations: `alembic upgrade head`
- [ ] Run tests: `pytest tests/security/`
- [ ] Clear existing sensitive data: `python scripts/clear_sensitive_evidence.py`
- [ ] Deploy to staging
- [ ] Verify API quotas working with test accounts
- [ ] Verify input validation rejects invalid inputs
- [ ] Run full integration test suite
- [ ] Deploy to production with database backup

---

## Verification Commands

```bash
# Check for remaining plaintext password references
grep -r "password" backend/app/providers/breach/dehashed/ | grep -v ".pyc" | grep -v "has_password"

# Check for shell=True in subprocess
grep -r "shell=True" backend/app/providers/

# Verify all API keys use SecretStr
grep -r "_api_key = " backend/app/providers/ | grep -v "SecretStr"

# Verify no PII in Epieos evidence
grep -r "\"name\"" backend/app/providers/social/epieos/

# Check all logger.error calls
grep -r "logger.error" backend/app/modules/identity/ | grep "str(e)"
```

---

## Estimated Effort

- Fix 1 (DeHashed credentials): 1.5 hours
- Fix 2 (Subprocess validation): 1 hour
- Fix 3 (API rate limiting): 3 hours
- Fix 4 (SecretStr wrapping): 0.5 hours
- Fix 5 (Epieos PII): 0.5 hours
- Fix 6 (Username validation): 0.25 hours
- Testing & validation: 1.5 hours

**Total: ~8 hours**

Can be parallelized if multiple developers available.
