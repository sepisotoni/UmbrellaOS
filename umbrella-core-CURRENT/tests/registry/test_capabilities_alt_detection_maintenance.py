"""
tests/registry/test_capabilities_alt_detection_maintenance.py — REST
integration tests for the suspicion_score decay capability.
"""
import datetime as dt
import uuid as uuid_lib

import pytest

from models import Player, SuspicionEvent
from tests.conftest import ADMIN_HEADERS
from tests.registry.conftest import session_headers_for_role


@pytest.mark.asyncio
async def test_alt_detection_maintenance_capability_is_listed(client):
    response = await client.get("/api/v1/capabilities")
    names = {c["name"] for c in response.json()}
    assert "alt_detection.suspicion.decay_stale" in names


@pytest.mark.asyncio
async def test_decay_stale_invoke_reduces_stale_scores(client, db_session):
    async with db_session() as db:
        player = Player(
            uuid=str(uuid_lib.uuid4()), username="stale_offender", suspicion_score=50,
        )
        db.add(player)
        old_event = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=90)
        db.add(SuspicionEvent(
            player_uuid=player.uuid, trigger="alt_ip_match", points=50, created_at=old_event,
        ))
        await db.commit()

    response = await client.post(
        "/api/v1/capabilities/alt_detection.suspicion.decay_stale/invoke",
        json={},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["decayed_count"] >= 1


@pytest.mark.asyncio
async def test_decay_stale_denied_for_role_without_punishments_manage(client, db_session):
    headers = await session_headers_for_role(db_session, "helper")
    response = await client.post(
        "/api/v1/capabilities/alt_detection.suspicion.decay_stale/invoke",
        json={},
        headers=headers,
    )
    assert response.status_code == 403
