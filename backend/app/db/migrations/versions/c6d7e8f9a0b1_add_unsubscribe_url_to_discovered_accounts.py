"""add_unsubscribe_url_to_discovered_accounts

Revision ID: c6d7e8f9a0b1
Revises: a3b4c5d6e7f8
Create Date: 2026-04-18 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c6d7e8f9a0b1"
down_revision: str | Sequence[str] | None = "a3b4c5d6e7f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add unsubscribe_url column to discovered_accounts."""
    op.add_column(
        "discovered_accounts",
        sa.Column("unsubscribe_url", sa.String(length=1024), nullable=True),
    )


def downgrade() -> None:
    """Remove unsubscribe_url column from discovered_accounts."""
    op.drop_column("discovered_accounts", "unsubscribe_url")
