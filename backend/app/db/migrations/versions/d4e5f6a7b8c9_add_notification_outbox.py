"""add_notification_outbox

Revision ID: d4e5f6a7b8c9
Revises: d3e4f5a6b7c8
Create Date: 2026-04-07 17:00:00.000000

Adds:
  - notification_outbox table (transactional email delivery queue)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "d3e4f5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create notification_outbox table."""
    op.create_table(
        "notification_outbox",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("signal_id", sa.String(64), nullable=False),
        sa.Column("to_email", sa.String(320), nullable=False),
        sa.Column("monitored_email", sa.String(320), nullable=False),
        sa.Column("template", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_detail", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_notification_outbox_user_id",
        ),
    )
    op.create_index(
        "ix_notification_outbox_user_id",
        "notification_outbox",
        ["user_id"],
    )
    op.create_index(
        "ix_notification_outbox_signal_id",
        "notification_outbox",
        ["signal_id"],
    )
    op.create_index(
        "ix_notification_outbox_status",
        "notification_outbox",
        ["status"],
    )
    # Composite index for the canonical "next pending row for this user" query
    op.create_index(
        "ix_notification_outbox_user_status",
        "notification_outbox",
        ["user_id", "status"],
    )


def downgrade() -> None:
    """Drop notification_outbox table."""
    op.drop_index(
        "ix_notification_outbox_user_status", table_name="notification_outbox"
    )
    op.drop_index("ix_notification_outbox_status", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_signal_id", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_user_id", table_name="notification_outbox")
    op.drop_table("notification_outbox")
