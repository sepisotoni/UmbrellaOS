from unittest.mock import AsyncMock, call

import discord
import pytest

from bot.bot import UmbrellaBot
from bot.config import RemoteConfig, Settings


@pytest.mark.asyncio
async def test_setup_hook_syncs_commands_globally_without_guild_setting(monkeypatch):
    settings = Settings(
        umbrella_core_url="https://core.test",
        umbrella_core_api_key="key",
    )
    bot = UmbrellaBot(settings, "token")
    bot.remote = RemoteConfig(
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
    monkeypatch.setattr("bot.bot.EXTENSIONS", ())
    monkeypatch.setattr(
        "bot.bot.fetch_bot_config",
        AsyncMock(return_value=bot.remote),
    )

    try:
        await bot.setup_hook()

        assert bot.tree.get_command("declared_globally") is not None
        assert sync.await_args_list == [call()]
    finally:
        await bot.close()
