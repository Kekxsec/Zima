"""scan_target_emails

Revision ID: f1a2b3c4d5e6
Revises: eef37f637714
Create Date: 2026-03-31 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "eef37f637714"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "scans",
        sa.Column(
            "target_emails",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.alter_column("scans", "target_emails", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("scans", "target_emails")
