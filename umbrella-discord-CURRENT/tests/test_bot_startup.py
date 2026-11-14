from unittest.mock import AsyncMock, call

import discord
import pytest

from bot.bot import UmbrellaBot
from bot.config import RemoteConfig, Settings


@pytest.mark.asyncio
async def test_setup_hook_copies_global_commands_into_configured_guild(monkeypatch):
    settings = Settings(
        umbrella_core_url="https://core.test",
        umbrella_core_api_key="key",
    )
    bot = UmbrellaBot(settings, "token")
    guild_id = 123456
    bot.remote = RemoteConfig(
        guild_id=guild_id,
        staff_alert_channel_id=None,
        verified_role_id=0,
        owner_role_id=0,
        callback_url=None,
        callback_port=8080,
        command_prefix="!",
    )

    async def command_callback(interaction: discord.Interaction) -> None:
        pass

    bot.tree.add_command(
        discord.app_commands.Command(
            name="declared_globally",
            description="A cog-declared command",
            callback=command_callback,
        )
    )
    sync = AsyncMock(return_value=[])
    bot.tree.sync = sync
    bot.core.push_command_manifest = AsyncMock()
    bot._push_guild_data = AsyncMock()
    monkeypatch.setattr("bot.bot.EXTENSIONS", ())
    monkeypatch.setattr(
        "bot.bot.fetch_bot_config",
        AsyncMock(return_value=bot.remote),
    )

    try:
        await bot.setup_hook()

        guild = discord.Object(id=guild_id)
        assert bot.tree.get_command("declared_globally") is None
        assert bot.tree.get_command("declared_globally", guild=guild) is not None
        assert sync.await_args_list == [call(guild=guild), call(guild=None)]
    finally:
        await bot.close()
