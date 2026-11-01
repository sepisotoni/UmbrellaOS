"""Regression coverage for defects introduced by the PR #7 hardening patch."""

import pytest
from sqlalchemy import select

from models import SuspicionEvent
from tests.conftest import ADMIN_HEADERS


@pytest.mark.asyncio
async def test_false_positive_uses_authenticated_reviewer_and_completes(client, db_session):
    """The handler must bind its auth dependency and not trust reviewed_by."""
    async with db_session() as db:
        event = SuspicionEvent(
            player_uuid="00000000-0000-0000-0000-000000000099",
            trigger="repeated_ip",
            points=20,
        )
        db.add(event)
        await db.commit()
        event_id = event.id

    response = await client.post(
        "/api/v1/alts/false-positive",
        json={"event_id": event_id, "reviewed_by": "spoofed-client-name"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    async with db_session() as db:
        event = await db.scalar(select(SuspicionEvent).where(SuspicionEvent.id == event_id))
        assert event is not None
        assert event.false_positive is True
        assert event.reviewed is True
        assert event.reviewed_by == "admin-key"
