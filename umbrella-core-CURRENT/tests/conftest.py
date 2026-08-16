"""
tests/conftest.py — Shared fixtures for the test suite.

Uses an in-memory SQLite database so tests never touch Postgres.
The async test client is built against the real FastAPI app with
overridden DB and settings dependencies.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from database.engine import Base, get_db
from services import SettingsService, RolesService

# Use in-memory SQLite for tests (no Postgres needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Override SECRET_KEY so auth tests have a known value
TEST_SECRET_KEY = "test-secret-key"


@pytest.fixture(scope="session", autouse=True)
def _test_secrets_encryption_key():
    """
    Phase 4's secrets encryption (services/secrets_service.py) requires a
    real Fernet key — deliberately, it refuses to fall back to storing
    secrets in plaintext. Session-scoped and autouse (not folded into the
    `client` fixture's per-test monkeypatching below) because plenty of
    tests exercise NodeService/ServerService directly, without ever going
    through the HTTP client fixture, and would otherwise fail on any call
    that touches a node's signing secret.
    """
    from cryptography.fernet import Fernet
    from config import get_settings

    settings = get_settings()
    settings.secrets_encryption_key = Fernet.generate_key().decode()
    yield


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """
    Create a fresh in-memory database for each test.
    Seeds defaults (settings, roles, permissions) just like the real startup.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        await SettingsService.seed_defaults(session)
        await RolesService.seed_defaults(session)

    yield session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session, monkeypatch):
    """
    Async HTTP test client with DB and settings overridden.
    Injects TEST_SECRET_KEY so auth works without a real .env.
    """
    # Patch API keys used by auth middleware (admin + plugin share test value)
    import config.settings as cfg_module
    settings = cfg_module.get_settings()
    monkeypatch.setattr(settings, "secret_key", TEST_SECRET_KEY)
    monkeypatch.setattr(settings, "admin_key", TEST_SECRET_KEY)

    import api.middleware.auth as auth_middleware
    import api.middleware.session as session_middleware
    monkeypatch.setattr(auth_middleware, "settings", settings)
    monkeypatch.setattr(session_middleware, "settings", settings)

    # Override the DB dependency
    async def override_get_db():
        async with db_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    from main import app
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# Shorthand headers for convenience
ADMIN_HEADERS = {"X-Admin-Key": TEST_SECRET_KEY}
WRONG_HEADERS = {"X-Admin-Key": "wrong-key"}
