"""
alembic/env.py — Alembic migration environment.
Configured for async SQLAlchemy with autogenerate support.
"""
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Load all models so autogenerate can detect them
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.settings import get_settings
from database.engine import Base  # noqa: F401 — triggers all model imports

settings = get_settings()

# Alembic Config object
config = context.config

# Set DB URL from our settings (overrides alembic.ini placeholder)
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection needed)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # AUDIT-2026-08-30 fix: 048_widen_alembic_version.py (this chat's own
    # earlier fix) widens alembic_version.version_num to VARCHAR(255), but
    # being revision 048 means it runs far too late to help — on a truly
    # fresh database, 033_add_anticheat_violations_table's own
    # version-stamp write (34-char revision id) fails against the
    # *original* VARCHAR(32) column long before migration 048 ever gets a
    # chance to run. A numbered migration can never retroactively widen a
    # column in time to help revisions that come before it in the same
    # linear chain — the widening has to happen before ANY migration
    # runs, unconditionally, regardless of current revision history.
    #
    # This block does exactly that: creates alembic_version with the wide
    # column if it doesn't exist yet (matching what Alembic would create
    # lazily anyway, just wider from the start), or widens it in place if
    # it already exists narrower. Idempotent and safe to run on every
    # invocation — a no-op once the column is already VARCHAR(255) or
    # wider. 048_widen_alembic_version.py itself is left in place
    # unchanged: harmless (ALTER ... TYPE VARCHAR(255) on an
    # already-VARCHAR(255) column succeeds trivially), and removing it
    # would just be extra churn on an already-shared, already-applied
    # revision chain for no benefit.
    connection.exec_driver_sql(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'alembic_version'
            ) THEN
                CREATE TABLE alembic_version (
                    version_num VARCHAR(255) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                );
            ELSIF (
                SELECT character_maximum_length FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'alembic_version'
                AND column_name = 'version_num'
            ) < 255 THEN
                ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255);
            END IF;
        END $$;
        """
    )
    # CRITICAL: SQLAlchemy 2.x connections "autobegin" an implicit
    # transaction on first execute() and never auto-commit it. Without
    # this explicit commit, the bootstrap DDL above silently starts a
    # transaction that context.begin_transaction() below then continues
    # inside of instead of starting its own — meaning the ENTIRE
    # migration run (not just this DDL) ends up uncommitted and gets
    # silently rolled back when the connection closes. Confirmed the hard
    # way: a full 001->048 run logged every migration as successful with
    # zero errors, then every single table was gone afterward. Committing
    # here ends the bootstrap's implicit transaction cleanly so
    # context.begin_transaction() below starts a fresh, real one for the
    # actual migrations.
    connection.commit()

    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
