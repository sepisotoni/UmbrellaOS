import hashlib
import time

import pytest
from sqlalchemy import select

from models.bot_guild import BotGuild
from models.setting import Setting


ADMIN_HEADERS = {"X-Admin-Key": "test-secret-key"}


def bot_headers() -> dict[str, str]:
    timestamp = str(int(time.time()))
    mac = hashlib.pbkdf2_hmac(
        "sha256", b"test-secret-key", timestamp.encode(), 100_000, dklen=32
    ).hex()
    return {"X-Auth-MAC": mac, "X-Auth-Timestamp": timestamp}


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
                {
                    "id": guild_id,
                    "name": "@everyone",
                    "color": 0,
                    "is_default": True,
                },
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
    response = await client.patch(
        "/api/v1/bot/guilds/200",
        headers=ADMIN_HEADERS,
        json={"owner_role_id": "200"},
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


@pytest.mark.asyncio
async def test_bot_runtime_state_sends_only_changed_config_and_token(
    client, db_session
):
    async with db_session() as db:
        token = await db.scalar(select(Setting).where(Setting.key == "discord.bot_token"))
        token.value = "initial-token"
        await db.commit()

    headers = bot_headers()
    response = await client.get("/api/v1/bot/runtime-state", headers=headers)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    initial = response.json()
    assert initial["discord_token"] == "initial-token"
    assert initial["config"]["remote"]["command_prefix"] == "!"

    response = await client.get(
        "/api/v1/bot/runtime-state",
        headers=bot_headers(),
        params={
            "config_revision": initial["config_revision"],
            "token_revision": initial["token_revision"],
        },
    )
    assert response.status_code == 204
    assert response.headers["cache-control"] == "no-store"

    response = await client.post(
        "/api/v1/bot/guilds/sync",
        headers=ADMIN_HEADERS,
        json={
            "guilds": [
                {
                    "guild_id": "100",
                    "name": "Community",
                    "channels": [],
                    "roles": [],
                }
            ]
        },
    )
    assert response.status_code == 200

    response = await client.get(
        "/api/v1/bot/runtime-state",
        headers=bot_headers(),
        params={
            "config_revision": initial["config_revision"],
            "token_revision": initial["token_revision"],
        },
    )
    assert response.status_code == 200
    config_update = response.json()
    assert "config" in config_update
    assert "discord_token" not in config_update
    assert config_update["config"]["guilds"][0]["guild_id"] == "100"

    async with db_session() as db:
        token = await db.scalar(select(Setting).where(Setting.key == "discord.bot_token"))
        token.value = "rotated-token"
        await db.commit()

    response = await client.get(
        "/api/v1/bot/runtime-state",
        headers=bot_headers(),
        params={
            "config_revision": config_update["config_revision"],
            "token_revision": config_update["token_revision"],
        },
    )
    assert response.status_code == 200
    token_update = response.json()
    assert token_update["discord_token"] == "rotated-token"
    assert "config" not in token_update


@pytest.mark.asyncio
async def test_bot_runtime_state_rejects_non_hmac_auth(client):
    response = await client.get(
        "/api/v1/bot/runtime-state", headers=ADMIN_HEADERS
    )
    assert response.status_code == 403
