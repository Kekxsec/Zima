"""add_session_revocation_to_users

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-04-06 16:30:00.000000

Adds:
  - users.asset_otp_fail_count / users.asset_otp_locked_until for authenticated
    asset OTP brute-force lockouts
  - users.session_revoked_at timestamp for server-side JWT logout invalidation
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3e4f5a6b7c8"
down_revision: str | Sequence[str] | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "asset_otp_fail_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "users",
        sa.Column("asset_otp_locked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("session_revoked_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "session_revoked_at")
    op.drop_column("users", "asset_otp_locked_until")
    op.drop_column("users", "asset_otp_fail_count")
