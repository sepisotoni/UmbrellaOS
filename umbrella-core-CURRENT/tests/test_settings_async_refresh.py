"""Regression for SQLAlchemy onupdate timestamps under async sessions."""

import pytest

from services.settings_service import SettingsService
from tests.conftest import ADMIN_HEADERS


@pytest.mark.asyncio
async def test_repeated_setting_updates_are_serializable(client):
    first = await client.patch(
        "/api/v1/settings/server.name",
        json={"value": "first-name"},
        headers=ADMIN_HEADERS,
    )
    assert first.status_code == 200
    second = await client.patch(
        "/api/v1/settings/server.name",
        json={"value": "second-name"},
        headers=ADMIN_HEADERS,
    )
    assert second.status_code == 200
    assert second.json()["value"] == "second-name"
    assert second.json()["updated_at"] is not None


@pytest.mark.asyncio
async def test_uncommitted_settings_update_refreshes_server_generated_columns(
    db_session,
):
    async with db_session() as db:
        result = await SettingsService.update(
            db,
            key="server.name",
            new_value="new-name",
            actor="test",
            actor_type="staff",
            commit=False,
        )
        assert result is not None
        assert result["value"] == "new-name"
        assert result["updated_at"]
        await db.rollback()
