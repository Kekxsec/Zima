"""remove maigret inventory and merge heads

Revision ID: a7b8c9d0e1f2
Revises: 88142ccc7dba, f1a2b3c4d5e6
Create Date: 2026-04-01 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: str | Sequence[str] | None = ("88142ccc7dba", "f1a2b3c4d5e6")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(sa.text("DELETE FROM discovered_accounts WHERE source_type = 'maigret'"))
    op.execute(sa.text("DELETE FROM signals WHERE provider = 'tool_maigret'"))


def downgrade() -> None:
    """Downgrade schema."""
    # Irreversible data cleanup.
    pass
