"""
tests/registry/test_capabilities_anticheat_maintenance.py — REST
integration tests for the anticheat_violations retention purge
capability.
"""
import datetime as dt

import pytest

from models.anticheat_violation import AnticheatViolation
from tests.conftest import ADMIN_HEADERS
from tests.registry.conftest import session_headers_for_role


@pytest.mark.asyncio
async def test_anticheat_maintenance_capability_is_listed(client):
    response = await client.get("/api/v1/capabilities")
    names = {c["name"] for c in response.json()}
    assert "anticheat.violations.purge_old" in names


@pytest.mark.asyncio
async def test_purge_old_invoke_removes_expired_rows(client, db_session):
    async with db_session() as db:
        old = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=365)
        db.add(AnticheatViolation(
            player_uuid=None, player_name="AncientOffender", check_name="Fly",
            verbose="test", vl=5, timestamp=old,
        ))
        await db.commit()

    response = await client.post(
        "/api/v1/capabilities/anticheat.violations.purge_old/invoke",
        json={},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["purged_count"] >= 1


@pytest.mark.asyncio
async def test_purge_old_denied_for_role_without_punishments_manage(client, db_session):
    headers = await session_headers_for_role(db_session, "helper")
    response = await client.post(
        "/api/v1/capabilities/anticheat.violations.purge_old/invoke",
        json={},
        headers=headers,
    )
    assert response.status_code == 403
