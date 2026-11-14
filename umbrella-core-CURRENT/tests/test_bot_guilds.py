import pytest
from sqlalchemy import select

from models.bot_guild import BotGuild
from models.setting import Setting


ADMIN_HEADERS = {"X-Admin-Key": "test-secret-key"}


@pytest.mark.asyncio
async def test_bot_guild_sync_tracks_multiple_guilds_and_preserves_legacy_config(
    client, db_session
):
    async with db_session() as db:
        legacy_settings = {
            "discord.guild_id": "100",
            "discord.staff_alert_channel_id": "101",
            "discord.verified_role_id": "102",
        }
        for key, value in legacy_settings.items():
            setting = await db.scalar(select(Setting).where(Setting.key == key))
            setting.value = value
        await db.commit()

    def guild(guild_id: str, name: str, channel_id: str, role_id: str) -> dict:
        return {
            "guild_id": guild_id,
            "name": name,
            "channels": [
                {"id": channel_id, "name": "general", "category": None},
            ],
            "roles": [
                {"id": role_id, "name": "Verified", "color": 0},
            ],
        }

    response = await client.post(
        "/api/v1/bot/guilds/sync",
        headers=ADMIN_HEADERS,
        json={
            "guilds": [
                guild("100", "Primary", "101", "102"),
                guild("200", "Community", "201", "202"),
            ]
        },
    )
    assert response.status_code == 200
    result = {item["guild_id"]: item for item in response.json()["guilds"]}
    assert set(result) == {"100", "200"}
    assert result["100"]["staff_alert_channel_id"] == "101"
    assert result["100"]["verified_role_id"] == "102"
    assert result["200"]["staff_alert_channel_id"] is None

    response = await client.get("/api/v1/bot/guilds", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    assert {item["guild_id"] for item in response.json()["guilds"]} == {"100", "200"}

    response = await client.patch(
        "/api/v1/bot/guilds/200",
        headers=ADMIN_HEADERS,
        json={"staff_alert_channel_id": "201", "verified_role_id": "202"},
    )
    assert response.status_code == 200
    assert response.json()["staff_alert_channel_id"] == "201"
    assert response.json()["verified_role_id"] == "202"

    response = await client.patch(
        "/api/v1/bot/guilds/200",
        headers=ADMIN_HEADERS,
        json={"owner_role_id": "999"},
    )
    assert response.status_code == 422

    response = await client.post(
        "/api/v1/bot/guilds/sync",
        headers=ADMIN_HEADERS,
        json={
            "guilds": [
                {"guild_id": "200", "name": "Community", "channels": [], "roles": []}
            ]
        },
    )
    assert response.status_code == 200
    async with db_session() as db:
        removed = await db.get(BotGuild, "100")
        still_active = await db.get(BotGuild, "200")
        assert removed is not None and not removed.is_active
        assert still_active is not None and still_active.is_active
        assert still_active.staff_alert_channel_id is None
        assert still_active.verified_role_id is None
