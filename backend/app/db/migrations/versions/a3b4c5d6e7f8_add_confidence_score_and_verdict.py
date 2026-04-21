# backend/app/db/migrations/versions/a3b4c5d6e7f8_add_confidence_score_and_verdict.py
"""Add confidence_score and user_verdict to discovered_accounts.

Revision ID: a3b4c5d6e7f8
Revises: f0a1b2c3d4e5
Create Date: 2026-04-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3b4c5d6e7f8"
down_revision: str | Sequence[str] | None = "f0a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "discovered_accounts",
        sa.Column(
            "confidence_score",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "discovered_accounts",
        sa.Column(
            "user_verdict",
            sa.String(length=20),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_discovered_account_confidence",
        "discovered_accounts",
        ["user_id", "confidence_score"],
    )


def downgrade() -> None:
    op.drop_index("ix_discovered_account_confidence", table_name="discovered_accounts")
    op.drop_column("discovered_accounts", "user_verdict")
    op.drop_column("discovered_accounts", "confidence_score")
