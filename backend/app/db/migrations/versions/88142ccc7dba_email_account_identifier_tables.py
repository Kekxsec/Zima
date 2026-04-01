"""email account identifier tables

Revision ID: 88142ccc7dba
Revises: eef37f637714
Create Date: 2026-03-31 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, UUID

revision: str = "88142ccc7dba"
down_revision: str | Sequence[str] | None = "eef37f637714"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # service_registry
    # ------------------------------------------------------------------
    op.create_table(
        "service_registry",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("service_name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column(
            "common_domains",
            ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("login_url", sa.String(512), nullable=True),
        sa.Column("password_reset_url", sa.String(512), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_service_registry_name", "service_registry", ["service_name"]
    )
    op.create_index("ix_service_registry_name", "service_registry", ["service_name"])
    op.create_index("ix_service_registry_active", "service_registry", ["is_active"])

    # ------------------------------------------------------------------
    # mbox_uploads
    # ------------------------------------------------------------------
    op.create_table(
        "mbox_uploads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "accounts_discovered",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "signals_created",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("error_detail", sa.String(1024), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
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
    )
    op.create_unique_constraint(
        "uq_mbox_upload_user_hash", "mbox_uploads", ["user_id", "file_hash"]
    )
    op.create_index("ix_mbox_uploads_user_id", "mbox_uploads", ["user_id"])
    op.create_index("ix_mbox_upload_user_status", "mbox_uploads", ["user_id", "status"])

    # ------------------------------------------------------------------
    # discovered_accounts
    # ------------------------------------------------------------------
    op.create_table(
        "discovered_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("upload_id", UUID(as_uuid=True), nullable=False),
        sa.Column("service_name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("email_used", sa.String(512), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("login_url", sa.String(512), nullable=True),
        sa.Column("password_reset_url", sa.String(512), nullable=True),
        sa.Column("sender_domain", sa.String(255), nullable=False),
        sa.Column(
            "email_count",
            sa.Integer,
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_reviewed",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
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
    )
    op.create_unique_constraint(
        "uq_discovered_account",
        "discovered_accounts",
        ["user_id", "service_name", "email_used"],
    )
    op.create_index("ix_discovered_account_user", "discovered_accounts", ["user_id"])
    op.create_index(
        "ix_discovered_account_upload", "discovered_accounts", ["upload_id"]
    )
    op.create_index(
        "ix_discovered_account_user_service",
        "discovered_accounts",
        ["user_id", "service_name"],
    )
    op.create_index(
        "ix_discovered_account_reviewed",
        "discovered_accounts",
        ["user_id", "is_reviewed"],
    )


def downgrade() -> None:
    op.drop_table("discovered_accounts")
    op.drop_table("mbox_uploads")
    op.drop_table("service_registry")
