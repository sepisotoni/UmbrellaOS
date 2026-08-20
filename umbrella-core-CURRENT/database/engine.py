"""
database/engine.py — Async SQLAlchemy engine + session factory.

Design decisions:
- We use async engine (asyncpg driver) for all application code.
- A separate sync engine is provided only for Alembic migrations.
- Sessions are scoped per-request via FastAPI dependency injection.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config.settings import get_settings

settings = get_settings()

# Async engine — used by the application
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    # Supabase's connection string routes through PgBouncer in
    # transaction-pooling mode by default. asyncpg's server-side
    # prepared-statement cache is incompatible with that: statements
    # prepared on one pooled connection can get reused against a
    # different underlying Postgres session, producing
    # DuplicatePreparedStatementError / ProtocolViolationError under
    # concurrent load (seen 2026-08-20 — every settings-table read
    # started failing under real traffic). Disabling asyncpg's
    # statement cache is the standard fix for this exact PgBouncer
    # transaction-mode + asyncpg combination; it costs a small amount
    # of per-query overhead (no server-side plan reuse) in exchange
    # for correctness. See https://sqlalche.me/e/20/f405.
    connect_args={"statement_cache_size": 0},
)

# Session factory — produces async sessions
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,    # Avoid lazy-load issues after commit
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Shared declarative base. All ORM models inherit from this."""
    pass


async def get_db() -> AsyncSession:
    """
    FastAPI dependency. Yields an async DB session per request,
    rolling back on exception and always closing on exit.

    Usage:
        @router.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all tables. Called on startup in development; use Alembic in production."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
