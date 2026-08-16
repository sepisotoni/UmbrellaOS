"""Add api_keys table and MFA columns on users

Revision ID: 013_identity_phase3
Revises: 012_hosting_domain
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa


revision = '013_identity_phase3'
down_revision = '012_hosting_domain'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('mfa_secret', sa.String(64), nullable=True))
    op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='false'))

    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('key_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('key_prefix', sa.String(16), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_api_keys_key_hash', table_name='api_keys')
    op.drop_table('api_keys')
    op.drop_column('users', 'mfa_enabled')
    op.drop_column('users', 'mfa_secret')
