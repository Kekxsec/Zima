# backend/app/db/migrations/versions/1b2c3d4e5f6a_add_account_category.py
"""add account_category to discovered_accounts

Revision ID: 1b2c3d4e5f6a
Revises: e1f2a3b4c5d6
Create Date: 2026-04-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1b2c3d4e5f6a"
down_revision: str | Sequence[str] | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "discovered_accounts",
        sa.Column(
            "account_category",
            sa.String(20),
            nullable=True,
        ),
    )
    # Backfill based on source_type and unsubscribe_url presence.
    op.execute(
        """
        UPDATE discovered_accounts SET account_category =
            CASE
                WHEN source_type = 'newsletter'                             THEN 'newsletter'
                WHEN source_type = 'receipt'                                THEN 'receipt'
                WHEN unsubscribe_url IS NOT NULL                             THEN 'newsletter'
                WHEN source_type IN (
                    'account_confirmation', 'password_reset', 'security_alert',
                    'epieos', 'holehe', 'maigret', 'password_manager'
                )                                                           THEN 'account'
                ELSE 'account'
            END
        WHERE account_category IS NULL
        """
    )
    op.create_index(
        "ix_discovered_account_category",
        "discovered_accounts",
        ["user_id", "account_category"],
    )


def downgrade() -> None:
    op.drop_index("ix_discovered_account_category", table_name="discovered_accounts")
    op.drop_column("discovered_accounts", "account_category")
