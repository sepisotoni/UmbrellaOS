from unittest.mock import AsyncMock

import pytest

from bot.bot import UmbrellaBot
from bot.config import BotTokenUnavailable, Settings, fetch_discord_bot_token
from bot.services.umbrella_core_client import UmbrellaCoreError
import main


@pytest.mark.asyncio
async def test_fetch_discord_bot_token_reads_core_setting():
    core = AsyncMock()
    core.get.return_value = {"value": "  token-from-core  "}

    token = await fetch_discord_bot_token(core)

    assert token == "token-from-core"
    core.get.assert_awaited_once_with("/api/v1/settings/discord.bot_token")


@pytest.mark.parametrize("value", [None, "", "   ", "***"])
@pytest.mark.asyncio
async def test_fetch_discord_bot_token_rejects_empty_or_masked_values(value):
    core = AsyncMock()
    core.get.return_value = {"value": value}

    with pytest.raises(BotTokenUnavailable):
        await fetch_discord_bot_token(core)


@pytest.mark.asyncio
async def test_fetch_discord_bot_token_reports_missing_core_setting():
    core = AsyncMock()
    core.get.side_effect = UmbrellaCoreError("not found", status_code=404)

    with pytest.raises(BotTokenUnavailable, match="not configured"):
        await fetch_discord_bot_token(core)


@pytest.mark.asyncio
async def test_token_watcher_closes_bot_when_core_token_changes(monkeypatch):
    core = AsyncMock()
    core.get.return_value = {"value": "new-token"}
    bot = UmbrellaBot(
        Settings(umbrella_core_url="https://core.test", umbrella_core_api_key="key"),
        "old-token",
        core=core,
    )
    close = AsyncMock()
    bot.close = close
    monkeypatch.setattr("bot.bot.asyncio.sleep", AsyncMock())

    await bot._watch_discord_token()

    close.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_bot_waits_for_core_before_starting_discord(monkeypatch):
    class StopRun(Exception):
        pass

    settings = Settings(
        umbrella_core_url="https://core.test",
        umbrella_core_api_key="key",
    )
    fetch_token = AsyncMock(
        side_effect=[UmbrellaCoreError("offline"), "token-from-core"]
    )
    sleep = AsyncMock()
    bot = type(
        "FakeBot",
        (),
        {
            "start": AsyncMock(side_effect=StopRun),
            "close": AsyncMock(),
        },
    )()
    monkeypatch.setattr(main, "fetch_discord_bot_token", fetch_token)
    monkeypatch.setattr(main, "UmbrellaBot", lambda *args, **kwargs: bot)
    monkeypatch.setattr(main.asyncio, "sleep", sleep)

    with pytest.raises(StopRun):
        await main.run_bot(settings)

    assert fetch_token.await_count == 2
    sleep.assert_awaited_once_with(main.CORE_RETRY_INTERVAL_SECONDS)
    bot.close.assert_awaited_once()
