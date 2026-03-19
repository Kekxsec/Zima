"""security_hardening

Revision ID: a1b2c3d4e5f6
Revises: e0dffe5ea597
Create Date: 2026-03-19 09:00:00.000000

Adds:
- users.otp_fail_count        — consecutive OTP failure counter for brute-force protection
- users.otp_locked_until      — timestamp until which OTP verification is blocked
- ix_auth_token_email_expires — composite index on auth_tokens(email, expires_at) for
                                 count_active_for_email and get_valid_token query performance
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "e0dffe5ea597"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("otp_fail_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("otp_locked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_auth_token_email_expires",
        "auth_tokens",
        ["email", "expires_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_auth_token_email_expires", table_name="auth_tokens")
    op.drop_column("users", "otp_locked_until")
    op.drop_column("users", "otp_fail_count")
