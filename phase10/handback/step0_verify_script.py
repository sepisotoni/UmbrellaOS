"""
_step0_verify.py — Phase 10 Decision 8 / step 0.

Calls marketplace.install.list and marketplace.install.dashboard_slots for
real, against the real FastAPI app + registry + database (same harness
tests/conftest.py uses), and dumps the raw JSON response shape so it can be
diffed against DASHBOARD-PLUGIN-UI-SCOPING.md's assumptions.

Not a pytest test — a one-off verification script per the kickoff doc's
step 0 instruction. Run with the venv active:
    python _step0_verify.py
"""
import asyncio
import base64
import io
import json
import zipfile

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from cryptography.fernet import Fernet

from database.engine import Base, get_db
from services import SettingsService, RolesService
from config import get_settings

TEST_SECRET_KEY = "step0-verify-key"


def _manifest() -> dict:
    return {
        "schema_version": 1,
        "plugin_id": "step0-verify-plugin",
        "name": "Step0 Verify Plugin",
        "version": "1.0.0",
        "author": "step0-script",
        "description": "Live shape verification plugin.",
        "capabilities": [
            {
                "local_name": "status",
                "summary": "Report status.",
                "entrypoint": "handlers:status",
                "params": {},
                "result": {"online": {"type": "boolean"}, "players": {"type": "integer"}},
                "required_permission": None,
            }
        ],
        "discord_commands": [],
        "dashboard_ui_slots": [
            {
                "slot": "dashboard.widgets",
                "label": "Step0 Status",
                "capability": "status",
                "render_as": "stat_pair",
            }
        ],
    }


def _zip_base64(manifest: dict) -> str:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("plugin.json", json.dumps(manifest))
        zf.writestr("handlers.py", "def status(params):\n    return {'online': True, 'players': 4}\n")
    return base64.b64encode(buf.getvalue()).decode()


async def main():
    settings = get_settings()
    settings.secrets_encryption_key = Fernet.generate_key().decode()
    settings.secret_key = TEST_SECRET_KEY
    settings.admin_key = TEST_SECRET_KEY

    import api.middleware.auth as auth_middleware
    import api.middleware.session as session_middleware
    auth_middleware.settings = settings
    session_middleware.settings = settings

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False,
        autoflush=False, autocommit=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await SettingsService.seed_defaults(session)
        await RolesService.seed_defaults(session)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    import tempfile, os
    tmp_root = tempfile.mkdtemp()
    settings.plugin_storage_root = os.path.join(tmp_root, "plugins")

    from main import app
    app.dependency_overrides[get_db] = override_get_db
    ADMIN_HEADERS = {"X-Admin-Key": TEST_SECRET_KEY}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        pub = await ac.post(
            "/api/v1/capabilities/marketplace.listing.publish/invoke",
            json={"zip_base64": _zip_base64(_manifest())},
            headers=ADMIN_HEADERS,
        )
        print("=== publish ===", pub.status_code)
        print(json.dumps(pub.json(), indent=2))

        inst = await ac.post(
            "/api/v1/capabilities/marketplace.install.install/invoke",
            json={"plugin_id": "step0-verify-plugin", "version": "1.0.0"},
            headers=ADMIN_HEADERS,
        )
        print("=== install ===", inst.status_code)
        print(json.dumps(inst.json(), indent=2))

        listed = await ac.post(
            "/api/v1/capabilities/marketplace.install.list/invoke",
            json={},
            headers=ADMIN_HEADERS,
        )
        print("=== marketplace.install.list (RAW LIVE SHAPE) ===", listed.status_code)
        print(json.dumps(listed.json(), indent=2))

        slots = await ac.post(
            "/api/v1/capabilities/marketplace.install.dashboard_slots/invoke",
            json={},
            headers=ADMIN_HEADERS,
        )
        print("=== marketplace.install.dashboard_slots (RAW LIVE SHAPE) ===", slots.status_code)
        print(json.dumps(slots.json(), indent=2))

        # cleanup
        await ac.post(
            "/api/v1/capabilities/marketplace.install.uninstall/invoke",
            json={"plugin_id": "step0-verify-plugin"},
            headers=ADMIN_HEADERS,
        )

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
