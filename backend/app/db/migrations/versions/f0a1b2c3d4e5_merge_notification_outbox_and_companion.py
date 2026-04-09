# backend/app/db/migrations/versions/f0a1b2c3d4e5_merge_notification_outbox_and_companion.py
"""Merge notification_outbox and companion_tables heads.

Revision ID: f0a1b2c3d4e5
Revises: d4e5f6a7b8c9, e5f6a7b8c9d0
Create Date: 2026-04-08

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "f0a1b2c3d4e5"
down_revision: tuple[str, str] = ("d4e5f6a7b8c9", "e5f6a7b8c9d0")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
