"""add_is_phishing_to_newsletter_subscriptions

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-04-06 14:30:00.000000

Adds:
  - is_phishing boolean column to newsletter_subscriptions (default false)
  - Index on (user_id, is_phishing) for fast phishing inbox queries
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: str | Sequence[str] | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "newsletter_subscriptions",
        sa.Column(
            "is_phishing",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "ix_newsletter_subscription_phishing",
        "newsletter_subscriptions",
        ["user_id", "is_phishing"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_newsletter_subscription_phishing",
        table_name="newsletter_subscriptions",
    )
    op.drop_column("newsletter_subscriptions", "is_phishing")
