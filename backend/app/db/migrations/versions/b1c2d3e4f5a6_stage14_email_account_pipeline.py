"""stage14_email_account_pipeline

Revision ID: b1c2d3e4f5a6
Revises: f93c39dc7f48
Create Date: 2026-04-06 14:00:00.000000

Adds:
  - newsletter_subscriptions table (14d)
  - vault_imports table (14b/14c)
  - user_integrations table (14e)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: str | Sequence[str] | None = "f93c39dc7f48"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- newsletter_subscriptions ---
    op.create_table(
        "newsletter_subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_domain", sa.String(255), nullable=False),
        sa.Column("sender_name", sa.String(255), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unsubscribe_url", sa.String(1024), nullable=True),
        sa.Column("list_id", sa.String(512), nullable=True),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="high"),
        sa.Column("is_reviewed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "recommended_action",
            sa.String(50),
            nullable=False,
            server_default="review",
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
        sa.UniqueConstraint(
            "user_id", "sender_domain", name="uq_newsletter_subscription"
        ),
    )
    op.create_index(
        "ix_newsletter_subscription_user",
        "newsletter_subscriptions",
        ["user_id"],
    )
    op.create_index(
        "ix_newsletter_subscription_reviewed",
        "newsletter_subscriptions",
        ["user_id", "is_reviewed"],
    )

    # --- vault_imports ---
    op.create_table(
        "vault_imports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("import_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column(
            "accounts_discovered", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("error_detail", sa.String(1024), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("user_id", "file_hash", name="uq_vault_import_user_hash"),
    )
    op.create_index(
        "ix_vault_import_user_status",
        "vault_imports",
        ["user_id", "status"],
    )

    # --- user_integrations ---
    op.create_table(
        "user_integrations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("api_key_ciphertext", sa.String(1024), nullable=False),
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
        sa.UniqueConstraint("user_id", "provider", name="uq_user_integration"),
    )
    op.create_index(
        "ix_user_integration_user",
        "user_integrations",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_integration_user", table_name="user_integrations")
    op.drop_table("user_integrations")

    op.drop_index("ix_vault_import_user_status", table_name="vault_imports")
    op.drop_table("vault_imports")

    op.drop_index(
        "ix_newsletter_subscription_reviewed", table_name="newsletter_subscriptions"
    )
    op.drop_index(
        "ix_newsletter_subscription_user", table_name="newsletter_subscriptions"
    )
    op.drop_table("newsletter_subscriptions")
