"""audit_fk_cascade_hardening

Restore Asset->users FK (CASCADE), add CASCADE to Signal FKs, add missing
FK+index pairs on companion/extension snapshots and discovered_accounts.upload_id.

Revision ID: c1d2e3f4a5b6
Revises: 1b2c3d4e5f6a
Create Date: 2026-04-25

"""

from collections.abc import Sequence

from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: str | Sequence[str] | None = "1b2c3d4e5f6a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Clean any orphaned rows before re-adding constraints. New constraints will
    # fail to create if dangling FKs exist.
    op.execute("DELETE FROM assets WHERE user_id NOT IN (SELECT id FROM users)")
    op.execute("DELETE FROM signals WHERE entity_id NOT IN (SELECT id FROM assets)")
    op.execute("DELETE FROM signals WHERE user_id NOT IN (SELECT id FROM users)")
    op.execute(
        "DELETE FROM browser_snapshots "
        "WHERE companion_session_id NOT IN (SELECT id FROM companion_sessions)"
    )
    op.execute(
        "DELETE FROM extension_snapshots "
        "WHERE extension_session_id NOT IN (SELECT id FROM extension_sessions)"
    )
    # Relax discovered_accounts.upload_id to nullable: scan-discovered rows
    # (holehe / maigret) come from scans, not mbox uploads.
    op.execute("ALTER TABLE discovered_accounts ALTER COLUMN upload_id DROP NOT NULL")
    # Convert the legacy sentinel value to NULL before adding the FK so the
    # constraint is satisfiable.
    op.execute(
        "UPDATE discovered_accounts SET upload_id = NULL "
        "WHERE upload_id = '00000000-0000-0000-0000-000000000001'"
    )
    op.execute(
        "DELETE FROM discovered_accounts "
        "WHERE upload_id IS NOT NULL "
        "AND upload_id NOT IN (SELECT id FROM mbox_uploads)"
    )
    op.execute(
        "DELETE FROM newsletter_subscriptions "
        "WHERE upload_id NOT IN (SELECT id FROM mbox_uploads)"
    )

    # ── assets.user_id (restore FK, dropped in e0dffe5ea597) ────────────────
    op.create_foreign_key(
        "assets_user_id_fkey",
        "assets",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ── signals.entity_id and signals.user_id (re-create with CASCADE) ──────
    op.drop_constraint("signals_entity_id_fkey", "signals", type_="foreignkey")
    op.drop_constraint("signals_user_id_fkey", "signals", type_="foreignkey")
    op.create_foreign_key(
        "signals_entity_id_fkey",
        "signals",
        "assets",
        ["entity_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "signals_user_id_fkey",
        "signals",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ── browser_snapshots.companion_session_id ──────────────────────────────
    op.create_foreign_key(
        "browser_snapshots_companion_session_id_fkey",
        "browser_snapshots",
        "companion_sessions",
        ["companion_session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_browser_snapshots_companion_session_id",
        "browser_snapshots",
        ["companion_session_id"],
    )

    # ── extension_snapshots.extension_session_id ────────────────────────────
    op.create_foreign_key(
        "extension_snapshots_extension_session_id_fkey",
        "extension_snapshots",
        "extension_sessions",
        ["extension_session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_extension_snapshots_extension_session_id",
        "extension_snapshots",
        ["extension_session_id"],
    )

    # ── discovered_accounts.upload_id ───────────────────────────────────────
    op.create_foreign_key(
        "discovered_accounts_upload_id_fkey",
        "discovered_accounts",
        "mbox_uploads",
        ["upload_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ── newsletter_subscriptions.upload_id ──────────────────────────────────
    op.create_foreign_key(
        "newsletter_subscriptions_upload_id_fkey",
        "newsletter_subscriptions",
        "mbox_uploads",
        ["upload_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_newsletter_subscriptions_upload_id",
        "newsletter_subscriptions",
        ["upload_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_newsletter_subscriptions_upload_id",
        table_name="newsletter_subscriptions",
    )
    op.drop_constraint(
        "newsletter_subscriptions_upload_id_fkey",
        "newsletter_subscriptions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "discovered_accounts_upload_id_fkey",
        "discovered_accounts",
        type_="foreignkey",
    )
    op.execute("ALTER TABLE discovered_accounts ALTER COLUMN upload_id SET NOT NULL")
    op.drop_index(
        "ix_extension_snapshots_extension_session_id", table_name="extension_snapshots"
    )
    op.drop_constraint(
        "extension_snapshots_extension_session_id_fkey",
        "extension_snapshots",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_browser_snapshots_companion_session_id", table_name="browser_snapshots"
    )
    op.drop_constraint(
        "browser_snapshots_companion_session_id_fkey",
        "browser_snapshots",
        type_="foreignkey",
    )

    op.drop_constraint("signals_user_id_fkey", "signals", type_="foreignkey")
    op.drop_constraint("signals_entity_id_fkey", "signals", type_="foreignkey")
    op.create_foreign_key(
        "signals_entity_id_fkey", "signals", "assets", ["entity_id"], ["id"]
    )
    op.create_foreign_key(
        "signals_user_id_fkey", "signals", "users", ["user_id"], ["id"]
    )

    op.drop_constraint("assets_user_id_fkey", "assets", type_="foreignkey")
