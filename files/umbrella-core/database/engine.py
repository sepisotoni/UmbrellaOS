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
    # Reconnect on stale connections
    
    
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
