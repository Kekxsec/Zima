"""add_extension_tables

Revision ID: e1f2a3b4c5d6
Revises: c6d7e8f9a0b1
Create Date: 2026-04-19 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "c6d7e8f9a0b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "extension_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("browser", sa.String(32), nullable=False),
        sa.Column("extension_version", sa.String(32), nullable=False),
        sa.Column("extension_jti", sa.String(64), nullable=False),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_extension_sessions_user_id"),
    )
    op.create_index("ix_extension_sessions_user_id", "extension_sessions", ["user_id"])

    op.create_table(
        "extension_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "extension_session_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "raw_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_extension_snapshots_user_id", "extension_snapshots", ["user_id"]
    )
    op.create_index(
        "ix_extension_snapshots_user_created",
        "extension_snapshots",
        ["user_id", "created_at"],
    )

    op.create_table(
        "guidance_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "extension_session_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("step", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guidance_events_user_id", "guidance_events", ["user_id"])
    op.create_index(
        "ix_guidance_events_user_provider",
        "guidance_events",
        ["user_id", "provider"],
    )


def downgrade() -> None:
    op.drop_table("guidance_events")
    op.drop_table("extension_snapshots")
    op.drop_table("extension_sessions")
