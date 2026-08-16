"""Add hosting domain: nodes, server_templates, allocations, servers

Revision ID: 012_hosting_domain
Revises: 011_add_suspicion_score
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa


revision = '012_hosting_domain'
down_revision = '011_add_suspicion_score'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'nodes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False, unique=True),
        sa.Column('daemon_url', sa.String(256), nullable=False),
        sa.Column('signing_secret', sa.String(256), nullable=False),
        sa.Column('status', sa.String(16), nullable=False, server_default='pending'),
        sa.Column('labels', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'server_templates',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('image', sa.String(256), nullable=False),
        sa.Column('startup_command', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('default_env', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('default_memory_bytes', sa.Integer(), nullable=False, server_default='1073741824'),
        sa.Column('default_cpu_cores', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'servers',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('node_id', sa.String(36), sa.ForeignKey('nodes.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('template_id', sa.String(36), sa.ForeignKey('server_templates.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('template_version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False, server_default='unknown'),
        sa.Column('working_dir', sa.String(512), nullable=False),
        sa.Column('env_overrides', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('memory_bytes', sa.Integer(), nullable=False),
        sa.Column('cpu_cores', sa.Float(), nullable=False),
        sa.Column('is_suspended', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_started_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_servers_node_id', 'servers', ['node_id'])

    op.create_table(
        'allocations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('node_id', sa.String(36), sa.ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('protocol', sa.String(8), nullable=False, server_default='tcp'),
        sa.Column('server_id', sa.String(36), sa.ForeignKey('servers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('container_port', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('node_id', 'port', 'protocol', name='uq_allocation_node_port_protocol'),
    )
    op.create_index('ix_allocations_node_id', 'allocations', ['node_id'])
    op.create_index('ix_allocations_server_id', 'allocations', ['server_id'])


def downgrade() -> None:
    op.drop_index('ix_allocations_server_id', table_name='allocations')
    op.drop_index('ix_allocations_node_id', table_name='allocations')
    op.drop_table('allocations')
    op.drop_index('ix_servers_node_id', table_name='servers')
    op.drop_table('servers')
    op.drop_table('server_templates')
    op.drop_table('nodes')
