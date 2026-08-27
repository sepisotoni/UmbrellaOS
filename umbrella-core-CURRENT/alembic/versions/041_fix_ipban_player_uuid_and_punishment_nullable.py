"""fix_ipban_player_uuid — make punishments.player_uuid nullable, add ban_ip_address column.

The ipban endpoint wrote player_uuid='SYSTEM' as a sentinel for IP-level bans,
but 'SYSTEM' is not a valid UUID in the players table — it always caused a
ForeignKeyViolationError once ck_punishments_type was fixed to allow 'ipban'
(migration 039). This migration resolves the secondary FK violation that
review-6 predicted would surface.

Changes:
  punishments.player_uuid: NOT NULL → NULL (for ipban rows, which have no
    specific player target). All existing player-specific punishments keep
    their player_uuid; only ipban rows have NULL.

  punishments.ban_ip_address: new VARCHAR(45) column, NULL for player-specific
    punishments, set to the banned IP for ipban rows. This replaces the pattern
    of embedding the IP in the reason string (old: reason='IP: 1.2.3.4 - reason')
    with a proper queryable column.

The correct sentinel is NULL (same pattern bridge.py uses for system-sender
messages), not a fake primary key value.

Revision ID: 041_fix_ipban_player_uuid_and_punishment_nullable
Revises:     040_add_users_sessions_discord_oauth
Create Date: 2026-08-27
"""
import sqlalchemy as sa
from alembic import op

revision = "041_fix_ipban_player_uuid_and_punishment_nullable"
down_revision = "040_add_users_sessions_discord_oauth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make player_uuid nullable — required for ipban rows (no specific player target).
    # The FK to players.uuid is retained; NULL simply means "no player".
    op.alter_column(
        "punishments",
        "player_uuid",
        existing_type=sa.String(36),
        nullable=True,
    )

    # Add ban_ip_address column for IP-level punishments.
    op.add_column(
        "punishments",
        sa.Column("ban_ip_address", sa.String(45), nullable=True),
    )

    # Back-fill ban_ip_address for any existing ipban rows that used the old
    # "IP: <ip> - <reason>" format in the reason column.
    op.execute(sa.text("""
        UPDATE punishments
        SET ban_ip_address = TRIM(SPLIT_PART(REPLACE(reason, 'IP: ', ''), ' - ', 1)),
            player_uuid = NULL
        WHERE type = 'ipban'
          AND reason LIKE 'IP: %'
          AND ban_ip_address IS NULL
    """))


def downgrade() -> None:
    # Restore the reason-string encoding for any ipban rows before dropping the column.
    op.execute(sa.text("""
        UPDATE punishments
        SET reason = 'IP: ' || ban_ip_address || ' - ' || reason,
            player_uuid = 'SYSTEM'
        WHERE type = 'ipban'
          AND ban_ip_address IS NOT NULL
    """))

    op.drop_column("punishments", "ban_ip_address")

    op.alter_column(
        "punishments",
        "player_uuid",
        existing_type=sa.String(36),
        nullable=False,
    )
