"""
alembic/versions/010_mc_commands_translation.py

Revision ID: 010_mc_commands_translation
Revises: 009_phase13_ai_tasks
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "010_mc_commands_translation"
down_revision = "009_phase13_ai_tasks"


def upgrade():
    # Create mc_commands table
    op.create_table(
        "mc_commands",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("command", sa.String(512), nullable=False),
        sa.Column("requested_by_discord_id", sa.String(64), nullable=False),
        sa.Column("requested_by_username", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create player_languages table
    op.create_table(
        "player_languages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("player_uuid", sa.String(36), nullable=False, unique=True),
        sa.Column("language_code", sa.String(8), nullable=False, server_default="en"),
        sa.Column("language_name", sa.String(64), nullable=False, server_default="English"),
        sa.Column("auto_translate_incoming", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("auto_translate_outgoing", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_player_languages_player_uuid", "player_languages", ["player_uuid"])
    
    # Create ai_config_actions table
    op.create_table(
        "ai_config_actions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("action_type", sa.String(64), nullable=False, index=True),
        sa.Column("natural_language_input", sa.Text(), nullable=False),
        sa.Column("ai_interpretation", sa.Text(), nullable=False),
        sa.Column("proposed_changes", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )


def downgrade():
    # Drop ai_config_actions
    op.drop_table("ai_config_actions")
    
    # Drop player_languages
    op.drop_index("ix_player_languages_player_uuid", table_name="player_languages")
    op.drop_table("player_languages")
    
    # Drop mc_commands
    op.drop_table("mc_commands")

