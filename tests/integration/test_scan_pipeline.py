# tests/integration/test_scan_pipeline.py

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.jobs.orchestrator import run_scan_task


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
