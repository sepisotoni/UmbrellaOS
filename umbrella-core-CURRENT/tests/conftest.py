"""
tests/conftest.py — Shared fixtures for the test suite.

Uses an in-memory SQLite database so tests never touch Postgres.
The async test client is built against the real FastAPI app with
overridden DB, settings, and rate-limiter dependencies.

Rate limiter hermetics (Critical Finding #1):
  main.py creates a RateLimiter against redis://localhost:6379/0 at import
  time. When Redis is reachable the real limiter fires during tests, causing
  ~272 failures (counters trip the per-IP limit within a single test file).
  When Redis is unreachable the middleware fails open — so tests pass, but
  only because a safety valve is silently swallowing errors. Neither
  behaviour is correct for a test suite.

  Fix: conftest patches main._rate_limiter with a no-op stub before the
  client fixture yields. The stub always returns allowed=True with no Redis
  I/O, making tests hermetic regardless of whether a local Redis is running.
  The real RateLimiter and its fixed-window algorithm are tested separately
  in tests/test_rate_limit.py using a mock Redis client.
"""
import os

# AUDIT-2026-08-29 fix: main.py now calls validate_secrets(settings) at
# module import time, which hard-fails if SECRET_KEY/ADMIN_KEY are still
# the "change-me-in-production" default (a real, correct production
# safety check another agent added). But it runs at import time — before
# pytest ever gets to invoke the _test_secrets fixture's monkeypatch
# below — so any test file that does `from main import app` at its own
# module level (e.g. test_health.py) fails during collection, before a
# single test even runs, unless SECRET_KEY/ADMIN_KEY are already valid in
# the environment. conftest.py is always imported before sibling test
# modules in its directory, so setting them here (before any import that
# could reach config/settings.py's get_settings()) fixes it for every
# test file, not just ones that already patch settings post-import.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-the-insecure-default")
os.environ.setdefault("ADMIN_KEY", "test-secret-key-not-the-insecure-default")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from database.engine import Base, get_db
from services import SettingsService, RolesService
from services.rate_limit_service import RateLimitResult

# Use in-memory SQLite for tests (no Postgres needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Override SECRET_KEY so auth tests have a known value
TEST_SECRET_KEY = "test-secret-key"


class _NoOpRateLimiter:
    """Always-allow rate limiter stub for tests.

    Replaces the real Redis-backed RateLimiter so tests are hermetic —
    they pass whether or not a local Redis is running, and they never
    trip the per-IP counter from rapid sequential requests within a
    test file (Critical Finding #1 fix).
    """

    async def check(self, identifier: str, limit: int, window_seconds: int) -> RateLimitResult:
        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=limit,
            reset_seconds=window_seconds,
        )


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
    Async HTTP test client with DB, settings, and rate limiter overridden.
    Injects TEST_SECRET_KEY so auth works without a real .env.

    Rate limiter is replaced with _NoOpRateLimiter so tests are hermetic
    regardless of Redis availability (Critical Finding #1 fix).
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

    # Replace the real Redis-backed rate limiter with a no-op stub.
    # The RateLimitMiddleware captures `rate_limiter` as `self._limiter` at
    # add_middleware() time. We patch the module-level `_rate_limiter` for
    # completeness, then walk the middleware stack to find the
    # RateLimitMiddleware instance and patch its `_limiter` reference directly.
    # This is robust to Starlette stack nesting depth changes.
    import main as main_module
    from api.middleware.rate_limit import RateLimitMiddleware

    no_op = _NoOpRateLimiter()
    monkeypatch.setattr(main_module, "_rate_limiter", no_op)

    # Walk the ASGI middleware stack to find the RateLimitMiddleware instance
    node = main_module.app
    for _ in range(20):  # depth guard
        if isinstance(node, RateLimitMiddleware):
            node._limiter = no_op
            break
        node = getattr(node, "app", None)
        if node is None:
            break

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
PLUGIN_HEADERS = {"X-Plugin-Key": TEST_SECRET_KEY}
