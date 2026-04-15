# backend/app/jobs/recovery.py
"""
Startup recovery jobs — re-enqueue work that was interrupted by a server restart.

Each recovery function creates its own AsyncSessionLocal() session (Rule 3) and
is safe to call multiple times (all underlying operations are idempotent).
"""

from backend.app.core.logging import get_logger
from backend.app.db.session import AsyncSessionLocal

logger = get_logger(__name__)


async def recover_stale_deletions() -> None:
    """
    Finds users whose soft-delete ran but whose personal-data erasure did not
    complete (i.e. server restarted after the 202 response but before the
    background task finished), then re-runs the erasure task synchronously.

    Detection heuristic: deleted_at IS NOT NULL AND tier != 'deleted'.
    - soft_delete() sets deleted_at and is_active=False.
    - scrub_pii() (the final step of _delete_user_personal_data) sets tier='deleted'.
    - If the process died between those two steps, the row is stuck in an
      incomplete state that this job recovers.
    """
    from backend.app.api.v1.account import _delete_user_personal_data
    from backend.app.db.repositories.users import UserRepository

    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        incomplete = await user_repo.get_users_with_incomplete_deletion()

    if not incomplete:
        return

    logger.warning(
        "startup.stale_deletions_found",
        count=len(incomplete),
        user_ids=[str(u.id) for u in incomplete],
    )

    for user in incomplete:
        try:
            await _delete_user_personal_data(user.id)
            logger.info("startup.stale_deletion_recovered", user_id=str(user.id))
        except Exception as exc:
            logger.error(
                "startup.stale_deletion_recovery_failed",
                user_id=str(user.id),
                error=str(exc),
            )
