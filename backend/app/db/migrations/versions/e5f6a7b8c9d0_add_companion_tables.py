"""add_companion_tables

Revision ID: e5f6a7b8c9d0
Revises: d3e4f5a6b7c8
Create Date: 2026-04-08 12:00:00.000000

Adds:
  - companion_sessions: one row per user tracking the registered companion binary
  - browser_snapshots: raw JSONB snapshots posted by the companion daemon
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d3e4f5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "companion_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("machine_id", sa.String(512), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("companion_version", sa.String(32), nullable=False),
        sa.Column("companion_jti", sa.String(64), nullable=False),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", name="uq_companion_sessions_user_id"),
    )
    op.create_index(
        "ix_companion_sessions_user_id",
        "companion_sessions",
        ["user_id"],
    )

    op.create_table(
        "browser_snapshots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "companion_session_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "raw_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_browser_snapshots_user_id",
        "browser_snapshots",
        ["user_id"],
    )
    op.create_index(
        "ix_browser_snapshots_user_created",
        "browser_snapshots",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_browser_snapshots_user_created", table_name="browser_snapshots")
    op.drop_index("ix_browser_snapshots_user_id", table_name="browser_snapshots")
    op.drop_table("browser_snapshots")

    op.drop_index("ix_companion_sessions_user_id", table_name="companion_sessions")
    op.drop_table("companion_sessions")
