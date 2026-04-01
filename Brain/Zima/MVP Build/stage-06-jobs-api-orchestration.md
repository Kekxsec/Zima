← [[MVP Master|Stage Progress]]

# Stage 6 — Jobs, API, and Scan Orchestration

Additional prework to stage 6:
  1. email/service.py is missing send_breach_alert

  Stage 6's orchestrator calls _email_service.send_breach_alert(...) but the method doesn't exist — only
  send_otp is implemented. This is covered in Stage 6b. When you reach Stage 6 you'll hit this and need to
  implement it (or stub it) before the orchestrator works. Not a blocker now, just flag it.

  2. The test database environment is not configured

  The 5 failing repository tests need APP_ENV=testing and a dedicated test database. This isn't blocking unit
  tests today, but Stage 6's integration tests (test_scan_pipeline.py) require a real database and will fail
  with the same assertion error unless this is set up first. Before running Stage 6 verification, you'll need:

  # Create a .env.test file at repo root
  APP_ENV=testing
  DATABASE_URL=postgresql+asyncpg://zima:zima_dev_password@localhost:5432/zima_test
  DATABASE_URL_SYNC=postgresql+psycopg2://zima:zima_dev_password@localhost:5432/zima_test
  # ... other vars same as .env
  # Create the test database
  createdb zima_test
  # Run tests with the test env
  APP_ENV=testing uv run pytest tests/integration/ -v

**Exit condition:** `uv run pytest tests/integration/ tests/api/test_scan_endpoints.py tests/api/test_findings_endpoints.py -v` passes. POST `/api/v1/scans/` triggers a background task that creates its own session. GET `/api/v1/findings/` returns paginated results. Score history is preserved across repeated scans. No duplicate signals or findings on repeated runs.

**Read CLAUDE-CODE-BRIEFING.md before starting this stage.**

---

## Files to Create in This Stage — In Order

1. `backend/app/jobs/models.py` ← defined in CLAUDE-CODE-BRIEFING.md, copy exactly
2. `backend/app/db/repositories/scans.py`
3. `backend/app/jobs/runner.py`
4. `backend/app/jobs/orchestrator.py`
5. `backend/app/api/v1/scans.py`
6. `backend/app/api/v1/findings.py`
7. `backend/app/api/v1/signals.py`
8. `backend/app/api/v1/scores.py`
9. Run: `uv run alembic revision --autogenerate -m "scan_model"`
10. Run: `uv run alembic upgrade head`
11. Write tests

---

## 6.1 Jobs Models

Create `backend/app/jobs/models.py` using the exact implementation in **CLAUDE-CODE-BRIEFING.md** under "Scan Model — Correct Location". Copy it exactly. Do not place the `Scan` model anywhere else.

---

## 6.2 Scan Repository

```python
# backend/app/db/repositories/scans.py
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.enums import ScanStatus, Tier
from backend.app.jobs.models import Scan


class ScanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user_id: uuid.UUID, tier: Tier) -> Scan:
        scan = Scan(
            user_id=user_id,
            tier=tier.value,
            status=ScanStatus.PENDING,
        )
        self.session.add(scan)
        await self.session.flush()
        return scan

    async def get_by_id_for_user(
        self, scan_id: uuid.UUID, user_id: uuid.UUID
    ) -> Scan | None:
        result = await self.session.execute(
            select(Scan).where(
                Scan.id == scan_id,
                Scan.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        scan_id: uuid.UUID,
        status: ScanStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        signals_created: int | None = None,
        findings_created: int | None = None,
        domains_run: list | None = None,
        error_detail: str | None = None,
    ) -> None:
        values: dict = {"status": status.value}
        if started_at is not None:
            values["started_at"] = started_at
        if completed_at is not None:
            values["completed_at"] = completed_at
        if signals_created is not None:
            values["signals_created"] = signals_created
        if findings_created is not None:
            values["findings_created"] = findings_created
        if domains_run is not None:
            values["domains_run"] = domains_run
        if error_detail is not None:
            values["error_detail"] = error_detail
        await self.session.execute(
            update(Scan).where(Scan.id == scan_id).values(**values)
        )

    async def mark_stale_scans_failed(
        self, stale_after_minutes: int = 10
    ) -> int:
        """
        Marks any scan in RUNNING status for longer than stale_after_minutes as FAILED.
        Called at startup and when the scan status endpoint detects a stale scan.
        Returns count of scans updated.
        """
        stale_threshold = datetime.now(timezone.utc) - timedelta(
            minutes=stale_after_minutes
        )
        result = await self.session.execute(
            update(Scan)
            .where(
                and_(
                    Scan.status == ScanStatus.RUNNING.value,
                    Scan.started_at < stale_threshold,
                )
            )
            .values(
                status=ScanStatus.FAILED.value,
                completed_at=datetime.now(timezone.utc),
                error_detail="Scan timed out — marked failed by stale scan detector",
            )
        )
        count: int = result.rowcount
        return count

    async def get_history_for_user(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Scan]:
        result = await self.session.execute(
            select(Scan)
            .where(Scan.user_id == user_id)
            .order_by(Scan.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
```

---

## 6.3 Module Runner

```python
# backend/app/jobs/runner.py
import uuid

from backend.app.core.enums import Tier
from backend.app.core.logging import get_logger
from backend.app.db.repositories.assets import AssetRepository
from backend.app.db.repositories.signals import SignalRepository
from backend.app.modules.base.service import BaseModuleService
from backend.app.modules.identity.breach_monitor.service import BreachMonitorService
from backend.app.tiers.loader import get_enabled_domains

logger = get_logger(__name__)

# Module registry — add new module classes here as they are built.
# Key: domain name matching tiers/config/*.yaml enabled_domains values.
# Value: list of module service classes for that domain.
DOMAIN_MODULES: dict[str, list[type[BaseModuleService]]] = {
    "identity": [BreachMonitorService],
}


class ModuleRunner:
    def __init__(
        self,
        asset_repo: AssetRepository,
        signal_repo: SignalRepository,
    ) -> None:
        self.asset_repo = asset_repo
        self.signal_repo = signal_repo

    async def run_for_user(
        self,
        user_id: uuid.UUID,
        tier: Tier,
    ) -> dict[str, int | list[str]]:
        """
        Runs all enabled module domains for this user's tier.
        Returns a summary dict with 'signals_created' and 'domains_run'.
        """
        enabled_domains = get_enabled_domains(tier)
        signals_created = 0
        domains_run: list[str] = []

        for domain in enabled_domains:
            module_classes = DOMAIN_MODULES.get(domain, [])
            if not module_classes:
                continue

            for ModuleClass in module_classes:
                module = ModuleClass()
                count = await self._run_module(module, user_id)
                signals_created += count

            domains_run.append(domain)

        return {"signals_created": signals_created, "domains_run": domains_run}

    async def _run_module(
        self,
        module: BaseModuleService,
        user_id: uuid.UUID,
    ) -> int:
        """
        Runs one module against all verified assets matching its required entity types.
        Upserts returned signals into the database.
        Catches and logs individual asset failures without stopping the run.
        Returns the total number of signals upserted.
        """
        count = 0
        for entity_type in module.required_entity_types:
            # CRITICAL: only verified assets are scanned — enforced here
            assets = await self.asset_repo.get_verified_for_user(
                user_id=user_id,
                entity_type=entity_type,
            )
            for asset in assets:
                try:
                    signals = await module.run(
                        user_id=user_id,
                        asset_id=asset.id,
                        asset_value=asset.value,
                    )
                    for signal in signals:
                        await self.signal_repo.upsert(signal)
                        count += 1
                except Exception as exc:
                    logger.error(
                        "runner.module_asset_error",
                        module=module.module_name,
                        asset_id=str(asset.id),
                        error=str(exc),
                    )
        return count
```

---

## 6.4 Scan Orchestrator

```python
# backend/app/jobs/orchestrator.py
import uuid
from datetime import datetime, timezone

from backend.app.core.enums import ScanStatus, Tier
from backend.app.core.logging import get_logger
from backend.app.correlation.engine import CorrelationEngine
from backend.app.correlation.rules.identity_compromise import HighIdentityCompromiseRisk
from backend.app.db.repositories.assets import AssetRepository
from backend.app.db.repositories.findings import FindingRepository
from backend.app.db.repositories.scans import ScanRepository
from backend.app.db.repositories.scores import ScoreRepository
from backend.app.db.repositories.signals import SignalRepository
from backend.app.db.session import AsyncSessionLocal
from backend.app.email.service import EmailService
from backend.app.jobs.runner import ModuleRunner
from backend.app.remediation.engine import RemediationEngine
from backend.app.scoring.calculators.identity_score import (
    SCORER_VERSION,
    calculate_identity_score,
)

logger = get_logger(__name__)

# Stateless engines — safe to instantiate once at module level
_correlation_engine = CorrelationEngine(rules=[HighIdentityCompromiseRisk()])
_remediation_engine = RemediationEngine()
_email_service = EmailService()


async def run_scan_task(
    user_id: uuid.UUID,
    scan_id: uuid.UUID,
    tier: Tier,
) -> None:
    """
    Background task entry point for a full scan cycle.

    IMPORTANT: Creates its own AsyncSession. Never called with a session parameter.
    Receives only serialisable values: UUIDs and enums.

    Sequence:
    1. Mark scan RUNNING
    2. Run module runner against verified assets for this tier
    3. Run correlation engine against open signals
    4. Calculate and append scores (never overwrite)
    5. Send email notifications for new high/critical signals
    6. Mark scan COMPLETED

    On any unhandled exception, marks scan FAILED and logs the error.
    """
    async with AsyncSessionLocal() as session:
        scan_repo = ScanRepository(session)
        signal_repo = SignalRepository(session)
        finding_repo = FindingRepository(session)
        score_repo = ScoreRepository(session)
        asset_repo = AssetRepository(session)

        await scan_repo.update_status(
            scan_id=scan_id,
            status=ScanStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        await session.commit()

        try:
            # ── Step 1: Run modules ─────────────────────────────────────────
            runner = ModuleRunner(asset_repo=asset_repo, signal_repo=signal_repo)
            run_result = await runner.run_for_user(user_id=user_id, tier=tier)
            await session.commit()

            # ── Step 2: Correlate ──────────────────────────────────────────
            signals = await signal_repo.get_open_for_user(user_id, limit=1000)
            findings = _correlation_engine.run(user_id=user_id, signals=signals)
            for finding in findings:
                await finding_repo.upsert(finding)
            await session.commit()

            # ── Step 3: Score (append-only — never overwrite) ──────────────
            identity_score, signal_count = calculate_identity_score(signals)
            await score_repo.insert(
                user_id=user_id,
                domain="identity",
                score=identity_score,
                signal_count=signal_count,
                scan_id=scan_id,
                scorer_version=SCORER_VERSION,
            )
            await session.commit()

            # ── Step 4: Notify for new unnotified high/critical signals ─────
            await _send_new_signal_notifications(
                user_id=user_id,
                signals=signals,
                asset_repo=asset_repo,
            )

            # ── Step 5: Mark completed ─────────────────────────────────────
            await scan_repo.update_status(
                scan_id=scan_id,
                status=ScanStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc),
                signals_created=int(run_result["signals_created"]),
                findings_created=len(findings),
                domains_run=list(run_result["domains_run"]),
            )
            await session.commit()

            logger.info(
                "scan.completed",
                scan_id=str(scan_id),
                user_id=str(user_id),
                signals=run_result["signals_created"],
                findings=len(findings),
                identity_score=identity_score,
            )

        except Exception as exc:
            logger.error(
                "scan.failed",
                scan_id=str(scan_id),
                user_id=str(user_id),
                error=str(exc),
                exc_info=True,
            )
            try:
                await scan_repo.update_status(
                    scan_id=scan_id,
                    status=ScanStatus.FAILED,
                    completed_at=datetime.now(timezone.utc),
                    error_detail=str(exc)[:1024],
                )
                await session.commit()
            except Exception as inner_exc:
                logger.error("scan.failed_to_mark_failed", error=str(inner_exc))


async def _send_new_signal_notifications(
    user_id: uuid.UUID,
    signals: list,
    asset_repo: AssetRepository,
) -> None:
    """
    Sends breach alert emails for signals that have not yet been notified.
    Uses signal.notified_at IS NULL to determine which signals are new.
    Caps at 3 emails per scan to prevent flooding.
    Updates notified_at on each signal after sending.
    """
    unnotified_high = [
        s for s in signals
        if s.severity in ("critical", "high")
        and s.signal_type == "email_breached"
        and s.notified_at is None
    ][:3]  # Hard cap at 3 notifications per scan

    if not unnotified_high:
        return

    primary_asset = await asset_repo.get_primary_email(user_id)
    if not primary_asset:
        return

    for signal in unnotified_high:
        evidence = signal.evidence or {}
        await _email_service.send_breach_alert(
            to_email=primary_asset.value,
            monitored_email=signal.entity_value,
            breach_title=evidence.get("breach_name", "Unknown breach"),
            breach_date=evidence.get("breach_date", "Unknown date"),
            data_classes=evidence.get("data_classes", []),
        )
        # Mark as notified so this signal is not emailed again on the next scan
        from datetime import datetime, timezone
        signal.notified_at = datetime.now(timezone.utc)
```

---

## 6.5 Signal Model Addition — notified_at

Add the `notified_at` field to the `Signal` model in `backend/app/signals/models.py`:

```python
# ADDITION TO: backend/app/signals/models.py
# Add this field to the Signal class, after the existing status field:

    notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

After adding this field, run:
```bash
uv run alembic revision --autogenerate -m "signal_notified_at"
uv run alembic upgrade head
```

---

## 6.6 API Endpoints

### Scans

```python
# backend/app/api/v1/scans.py
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.auth.models import User
from backend.app.core.enums import ScanStatus, Tier
from backend.app.db.repositories.scans import ScanRepository
from backend.app.jobs.models import Scan
from backend.app.jobs.orchestrator import run_scan_task
from backend.app.main import limiter

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("/", status_code=202)
@limiter.limit("5/hour")
async def trigger_scan(
    request: Request,  # Required by slowapi for rate limiting
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Queues a scan for the authenticated user.
    Returns immediately with scan_id. Client polls GET /scans/{scan_id} for completion.
    Background task creates its own database session — no session is passed to it.
    """
    scan_repo = ScanRepository(db)
    scan = await scan_repo.create(
        user_id=current_user.id,
        tier=Tier(current_user.tier),
    )
    await db.commit()

    # Pass only serialisable values — never a session or db object
    background_tasks.add_task(
        run_scan_task,
        user_id=current_user.id,
        scan_id=scan.id,
        tier=Tier(current_user.tier),
    )

    return {"scan_id": str(scan.id), "status": ScanStatus.PENDING.value}


@router.get("/")
async def get_scan_history(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    scan_repo = ScanRepository(db)
    scans = await scan_repo.get_history_for_user(
        user_id=current_user.id,
        limit=min(limit, 50),
        offset=offset,
    )
    return {"scans": [_scan_to_dict(s) for s in scans], "limit": limit, "offset": offset}


@router.get("/{scan_id}")
async def get_scan_status(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Returns current status of a scan. Also detects and marks stale scans.
    Poll this endpoint after triggering a scan to check for completion.
    """
    try:
        scan_uuid = uuid.UUID(scan_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid scan ID format")

    scan_repo = ScanRepository(db)
    scan = await scan_repo.get_by_id_for_user(
        scan_id=scan_uuid,
        user_id=current_user.id,
    )
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Detect and mark stale scans on read — prevents stuck RUNNING status
    if scan.status == ScanStatus.RUNNING.value and scan.started_at:
        stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=10)
        if scan.started_at < stale_threshold:
            scan.status = ScanStatus.FAILED.value
            scan.completed_at = datetime.now(timezone.utc)
            scan.error_detail = "Scan timed out"
            await db.commit()

    return _scan_to_dict(scan)


def _scan_to_dict(scan: Scan) -> dict:
    return {
        "id": str(scan.id),
        "status": scan.status,
        "tier": scan.tier,
        "started_at": scan.started_at.isoformat() if scan.started_at else None,
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        "signals_created": scan.signals_created,
        "findings_created": scan.findings_created,
        "domains_run": scan.domains_run,
        "error_detail": scan.error_detail,
        "created_at": scan.created_at.isoformat(),
    }
```

### Findings

```python
# backend/app/api/v1/findings.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.auth.models import User
from backend.app.correlation.models import Finding
from backend.app.db.repositories.findings import FindingRepository
from backend.app.db.repositories.signals import SignalRepository
from backend.app.db.models.audit import AuditEventType
from backend.app.db.repositories.audit import AuditRepository
from pydantic import BaseModel, Field

router = APIRouter(prefix="/findings", tags=["findings"])


class SuppressRequest(BaseModel):
    reason: str | None = Field(None, max_length=256)


@router.get("/")
async def get_findings(
    filter_status: str = "open",
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Returns findings for the authenticated user.
    filter_status: "open" (default), "suppressed", or "resolved"
    """
    if filter_status not in ("open", "suppressed", "resolved"):
        raise HTTPException(status_code=422, detail="filter_status must be open, suppressed, or resolved")

    finding_repo = FindingRepository(db)
    signal_repo = SignalRepository(db)

    findings = await finding_repo.get_for_user_by_status(
        user_id=current_user.id,
        status=filter_status,
        limit=min(limit, 100),
        offset=offset,
    )
    total = await finding_repo.count_for_user_by_status(
        user_id=current_user.id, status=filter_status
    )
    signal_count = await signal_repo.count_open_for_user(current_user.id)

    return {
        "findings": findings,
        "signals_open": signal_count,
        "total": total,
        "limit": limit,
        "offset": offset,
        "filter_status": filter_status,
    }


@router.patch("/{finding_id}/suppress", status_code=200)
async def suppress_finding(
    finding_id: str,
    body: SuppressRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Suppresses an open finding. It will not appear in the default open findings list."""
    result = await db.execute(
        update(Finding)
        .where(
            Finding.finding_id == finding_id,
            Finding.user_id == current_user.id,
            Finding.status == "open",
        )
        .values(status="suppressed")
        .returning(Finding.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=404, detail="Finding not found or not in open status"
        )

    audit_repo = AuditRepository(db)
    await audit_repo.log(
        event_type=AuditEventType.FINDING_SUPPRESSED,
        user_id=current_user.id,
        metadata={"finding_id": finding_id, "reason": body.reason},
    )
    await db.commit()
    return {"status": "suppressed", "finding_id": finding_id}


@router.patch("/{finding_id}/unsuppress", status_code=200)
async def unsuppress_finding(
    finding_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Restores a suppressed finding to open status."""
    result = await db.execute(
        update(Finding)
        .where(
            Finding.finding_id == finding_id,
            Finding.user_id == current_user.id,
            Finding.status == "suppressed",
        )
        .values(status="open")
        .returning(Finding.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=404, detail="Finding not found or not in suppressed status"
        )
    await db.commit()
    return {"status": "open", "finding_id": finding_id}
```

### Signals

```python
# backend/app/api/v1/signals.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.auth.models import User
from backend.app.db.models.audit import AuditEventType
from backend.app.db.repositories.audit import AuditRepository
from backend.app.signals.models import Signal
from pydantic import BaseModel, Field

router = APIRouter(prefix="/signals", tags=["signals"])


class SuppressRequest(BaseModel):
    reason: str | None = Field(None, max_length=256)


@router.patch("/{signal_id}/suppress", status_code=200)
async def suppress_signal(
    signal_id: str,
    body: SuppressRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Suppresses an open signal."""
    result = await db.execute(
        update(Signal)
        .where(
            Signal.signal_id == signal_id,
            Signal.user_id == current_user.id,
            Signal.status == "open",
        )
        .values(status="suppressed")
        .returning(Signal.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=404, detail="Signal not found or not in open status"
        )

    audit_repo = AuditRepository(db)
    await audit_repo.log(
        event_type=AuditEventType.SIGNAL_SUPPRESSED,
        user_id=current_user.id,
        metadata={"signal_id": signal_id, "reason": body.reason},
    )
    await db.commit()
    return {"status": "suppressed", "signal_id": signal_id}
```

### Scores

```python
# backend/app/api/v1/scores.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.auth.models import User
from backend.app.db.repositories.scores import ScoreRepository

router = APIRouter(prefix="/scores", tags=["scores"])


@router.get("/")
async def get_scores(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Returns the most recent score per domain for the authenticated user."""
    score_repo = ScoreRepository(db)
    latest = await score_repo.get_latest_for_user(current_user.id)
    return {
        "scores": [
            {
                "domain": s.domain,
                "score": s.score,
                "signal_count": s.signal_count,
                "scorer_version": s.scorer_version,
                "calculated_at": s.calculated_at.isoformat(),
            }
            for s in latest
        ]
    }


@router.get("/{domain}/history")
async def get_score_history(
    domain: str,
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Returns score history for a domain. Used for trend charts."""
    score_repo = ScoreRepository(db)
    history = await score_repo.get_history_for_domain(
        user_id=current_user.id,
        domain=domain,
        limit=min(limit, 90),
    )
    return {
        "domain": domain,
        "history": [
            {
                "score": s.score,
                "signal_count": s.signal_count,
                "scorer_version": s.scorer_version,
                "calculated_at": s.calculated_at.isoformat(),
            }
            for s in history
        ],
    }
```

---

## 6.7 FindingRepository Additions

The `FindingRepository` in Stage 3 needs two additional methods used by the findings endpoint. Add these to `backend/app/db/repositories/findings.py`:

```python
# ADDITION TO: backend/app/db/repositories/findings.py
# Add these two methods to the FindingRepository class:

    async def get_for_user_by_status(
        self,
        user_id: uuid.UUID,
        status: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Finding]:
        result = await self.session.execute(
            select(Finding)
            .where(Finding.user_id == user_id, Finding.status == status)
            .order_by(Finding.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_for_user_by_status(
        self, user_id: uuid.UUID, status: str
    ) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Finding)
            .where(Finding.user_id == user_id, Finding.status == status)
        )
        return result.scalar_one()
```

Add this import to the top of `findings.py` if not already present:
```python
from sqlalchemy import func
```

---

## 6.8 AuditRepository

The `AuditRepository` is referenced in this stage. Create it now if it does not already exist from Stage 1b:

```python
# backend/app/db/repositories/audit.py
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models.audit import AuditEvent


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
        Appends an audit event. Never raises — a failed audit log must not
        block the operation being audited. The caller's commit will persist this.
        """
        try:
            event = AuditEvent(
                user_id=user_id,
                event_type=event_type,
                ip_address=ip_address,
                metadata=metadata or {},
            )
            self.session.add(event)
        except Exception as exc:
            from backend.app.core.logging import get_logger
            get_logger(__name__).error("audit.log_failed", error=str(exc))
```

---

## 6.9 Run Migrations

```bash
uv run alembic revision --autogenerate -m "scan_and_notified_at"
uv run alembic upgrade head
uv run alembic current  # Must show: (head)
```

---

## 6.10 Tests

### tests/api/test_scan_endpoints.py

```python
# tests/api/test_scan_endpoints.py
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_trigger_scan_requires_authentication(client: AsyncClient) -> None:
    response = await client.post("/api/v1/scans/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_trigger_scan_returns_202_with_scan_id(
    auth_client: AsyncClient,
) -> None:
    with patch("backend.app.api.v1.scans.run_scan_task") as mock_task:
        response = await auth_client.post("/api/v1/scans/")
    assert response.status_code == 202
    data = response.json()
    assert "scan_id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_trigger_scan_enqueues_background_task(
    auth_client: AsyncClient,
) -> None:
    """Background task must be added — session must NOT be passed to it."""
    with patch("backend.app.api.v1.scans.run_scan_task") as mock_task:
        await auth_client.post("/api/v1/scans/")
    mock_task.assert_not_called()  # It's added via BackgroundTasks, not called directly


@pytest.mark.asyncio
async def test_get_scan_history_returns_empty_for_new_user(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get("/api/v1/scans/")
    assert response.status_code == 200
    assert response.json()["scans"] == []


@pytest.mark.asyncio
async def test_get_scan_status_returns_404_for_unknown_id(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get(
        "/api/v1/scans/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_scan_status_returns_404_for_other_users_scan(
    auth_client: AsyncClient,
    paid_auth_client: AsyncClient,
) -> None:
    """User A cannot access User B's scan."""
    with patch("backend.app.api.v1.scans.run_scan_task"):
        create_resp = await auth_client.post("/api/v1/scans/")
    scan_id = create_resp.json()["scan_id"]

    response = await paid_auth_client.get(f"/api/v1/scans/{scan_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_scan_status_returns_422_for_invalid_uuid(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get("/api/v1/scans/not-a-uuid")
    assert response.status_code == 422
```

### tests/api/test_findings_endpoints.py

```python
# tests/api/test_findings_endpoints.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_findings_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/findings/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_findings_returns_empty_for_new_user(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get("/api/v1/findings/")
    assert response.status_code == 200
    data = response.json()
    assert data["findings"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_findings_defaults_to_open_status(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get("/api/v1/findings/")
    assert response.status_code == 200
    assert response.json()["filter_status"] == "open"


@pytest.mark.asyncio
async def test_get_findings_rejects_invalid_status_filter(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get("/api/v1/findings/?filter_status=invalid")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_suppress_finding_returns_404_for_nonexistent(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.patch(
        "/api/v1/findings/sig_nonexistent/suppress",
        json={"reason": "test"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_scores_returns_empty_for_new_user(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get("/api/v1/scores/")
    assert response.status_code == 200
    assert response.json()["scores"] == []
```

### tests/integration/test_scan_pipeline.py

```python
# tests/integration/test_scan_pipeline.py
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.enums import ScanStatus, Tier
from backend.app.db.repositories.findings import FindingRepository
from backend.app.db.repositories.scans import ScanRepository
from backend.app.db.repositories.scores import ScoreRepository
from backend.app.db.repositories.signals import SignalRepository
from backend.app.jobs.orchestrator import run_scan_task
from tests.factories import AssetFactory, UserFactory


@pytest.mark.asyncio
async def test_scan_task_creates_its_own_session(
    db_session: AsyncSession,
) -> None:
    """
    run_scan_task must create its own session internally.
    Verify it does not accept a session parameter.
    """
    import inspect
    sig = inspect.signature(run_scan_task)
    param_names = list(sig.parameters.keys())
    assert "session" not in param_names
    assert "db" not in param_names


@pytest.mark.asyncio
async def test_scan_task_marks_scan_running_then_completed(
    db_session: AsyncSession,
    mock_hibp_no_breaches,
) -> None:
    user = UserFactory.build()
    db_session.add(user)
    asset = AssetFactory.build(user_id=user.id, entity_type="email", is_verified=True)
    db_session.add(asset)
    await db_session.commit()

    scan_repo = ScanRepository(db_session)
    scan = await scan_repo.create(user_id=user.id, tier=Tier.CORE)
    await db_session.commit()

    await run_scan_task(
        user_id=user.id,
        scan_id=scan.id,
        tier=Tier.CORE,
    )

    await db_session.refresh(scan)
    assert scan.status == ScanStatus.COMPLETED.value
    assert scan.completed_at is not None
    assert scan.started_at is not None


@pytest.mark.asyncio
async def test_repeated_scan_does_not_duplicate_signals(
    db_session: AsyncSession,
    mock_hibp_with_breaches,
) -> None:
    user = UserFactory.build()
    db_session.add(user)
    asset = AssetFactory.build(user_id=user.id, entity_type="email", is_verified=True)
    db_session.add(asset)
    await db_session.commit()

    scan_repo = ScanRepository(db_session)

    # First scan
    scan1 = await scan_repo.create(user_id=user.id, tier=Tier.CORE)
    await db_session.commit()
    await run_scan_task(user_id=user.id, scan_id=scan1.id, tier=Tier.CORE)

    # Second scan
    scan2 = await scan_repo.create(user_id=user.id, tier=Tier.CORE)
    await db_session.commit()
    await run_scan_task(user_id=user.id, scan_id=scan2.id, tier=Tier.CORE)

    signal_repo = SignalRepository(db_session)
    signals = await signal_repo.get_open_for_user(user.id, limit=1000)

    # HIBP mock returns 2 breaches — should have exactly 2 signals, not 4
    assert len(signals) == 2


@pytest.mark.asyncio
async def test_repeated_scan_appends_new_score_row(
    db_session: AsyncSession,
    mock_hibp_no_breaches,
) -> None:
    user = UserFactory.build()
    db_session.add(user)
    asset = AssetFactory.build(user_id=user.id, entity_type="email", is_verified=True)
    db_session.add(asset)
    await db_session.commit()

    scan_repo = ScanRepository(db_session)
    score_repo = ScoreRepository(db_session)

    scan1 = await scan_repo.create(user_id=user.id, tier=Tier.CORE)
    await db_session.commit()
    await run_scan_task(user_id=user.id, scan_id=scan1.id, tier=Tier.CORE)

    scan2 = await scan_repo.create(user_id=user.id, tier=Tier.CORE)
    await db_session.commit()
    await run_scan_task(user_id=user.id, scan_id=scan2.id, tier=Tier.CORE)

    history = await score_repo.get_history_for_domain(user.id, "identity", limit=10)
    # Two scan runs must produce two score rows — scores are append-only
    assert len(history) == 2


@pytest.mark.asyncio
async def test_scan_task_marks_failed_on_module_crash(
    db_session: AsyncSession,
) -> None:
    user = UserFactory.build()
    db_session.add(user)
    await db_session.commit()

    scan_repo = ScanRepository(db_session)
    scan = await scan_repo.create(user_id=user.id, tier=Tier.CORE)
    await db_session.commit()

    with patch(
        "backend.app.jobs.runner.ModuleRunner.run_for_user",
        new=AsyncMock(side_effect=RuntimeError("simulated crash")),
    ):
        await run_scan_task(user_id=user.id, scan_id=scan.id, tier=Tier.CORE)

    await db_session.refresh(scan)
    assert scan.status == ScanStatus.FAILED.value
    assert "simulated crash" in (scan.error_detail or "")
```

---

## Stage 6 Verification

```bash
uv run alembic current               # Must show: (head)
uv run python scripts/check_imports.py
uv run pytest tests/api/test_scan_endpoints.py tests/api/test_findings_endpoints.py -v
uv run pytest tests/integration/test_scan_pipeline.py -v
```

All must pass before proceeding to Stage 6b and Stage 7.
