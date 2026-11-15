from unittest.mock import AsyncMock, Mock

import pytest

from bot.bot import UmbrellaBot
from bot.config import (
    BotRuntimeState,
    RemoteConfig,
    Settings,
    fetch_bot_runtime_state,
)
from bot.services.umbrella_core_client import UmbrellaCoreError
import main


def runtime_state(token: str = "token-from-core") -> BotRuntimeState:
    return BotRuntimeState(
        config_revision="config-v1",
        token_revision="token-v1",
        discord_token=token,
        token_changed=True,
        remote=RemoteConfig(
            callback_url=None,
            callback_port=8080,
            command_prefix="!",
        ),
        guild_configs={},
    )


@pytest.mark.asyncio
async def test_fetch_bot_runtime_state_reads_token_and_config_from_one_snapshot():
    core = AsyncMock()
    core.get_bot_runtime_state.return_value = {
        "config_revision": "config-v1",
        "token_revision": "token-v1",
        "discord_token": "  token-from-core  ",
        "config": {
            "remote": {
                "callback_url": "https://bot.example.com",
                "callback_port": 8080,
                "command_prefix": "!",
            },
            "guilds": [],
        },
    }

    state = await fetch_bot_runtime_state(core)

    assert state is not None
    assert state.discord_token == "token-from-core"
    assert state.remote is not None
    assert state.remote.callback_url == "https://bot.example.com"
    assert state.guild_configs == {}
    core.get_bot_runtime_state.assert_awaited_once_with(
        config_revision=None,
        token_revision=None,
    )


@pytest.mark.asyncio
async def test_fetch_bot_runtime_state_returns_none_when_core_has_no_changes():
    core = AsyncMock()
    core.get_bot_runtime_state.return_value = None

    state = await fetch_bot_runtime_state(
        core,
        config_revision="config-v1",
        token_revision="token-v1",
    )

    assert state is None
    core.get_bot_runtime_state.assert_awaited_once_with(
        config_revision="config-v1",
        token_revision="token-v1",
    )


@pytest.mark.asyncio
async def test_fetch_bot_runtime_state_returns_pending_events_without_config_changes():
    core = AsyncMock()
    core.get_bot_runtime_state.return_value = {
        "config_revision": "config-v1",
        "token_revision": "token-v1",
        "pending_events": [
            {
                "id": "delivery-1",
                "event": "bridge.dashboard_message",
                "payload": {"message_id": 1},
            }
        ],
    }

    state = await fetch_bot_runtime_state(
        core,
        config_revision="config-v1",
        token_revision="token-v1",
    )

    assert state is not None
    assert state.pending_events[0]["id"] == "delivery-1"


@pytest.mark.asyncio
async def test_token_watcher_closes_bot_when_core_token_changes(monkeypatch):
    core = AsyncMock()
    core.get_bot_runtime_state.return_value = {
        "config_revision": "config-v1",
        "token_revision": "token-v2",
        "discord_token": "rotated-token",
    }
    bot = UmbrellaBot(
        Settings(umbrella_core_url="https://core.test", umbrella_core_api_key="key"),
        runtime_state(),
        core=core,
    )
    close = AsyncMock()
    bot.close = close
    monkeypatch.setattr("bot.bot.asyncio.sleep", AsyncMock())

    await bot._watch_core_runtime_state()

    close.assert_awaited_once()


@pytest.mark.asyncio
async def test_runtime_state_watcher_applies_config_without_restarting(monkeypatch):
    core = AsyncMock()
    core.get_bot_runtime_state.return_value = {
        "config_revision": "config-v2",
        "token_revision": "token-v1",
        "pending_events": [
            {
                "id": "delivery-1",
                "event": "bridge.dashboard_message",
                "payload": {"message_id": 1},
            }
        ],
        "config": {
            "remote": {
                "callback_url": None,
                "callback_port": 8080,
                "command_prefix": "?",
            },
            "guilds": [],
        },
    }
    bot = UmbrellaBot(
        Settings(umbrella_core_url="https://core.test", umbrella_core_api_key="key"),
        runtime_state(),
        core=core,
    )
    monkeypatch.setattr(bot, "is_closed", Mock(side_effect=[False, True]))
    process_events = AsyncMock()
    monkeypatch.setattr(bot, "_process_pending_events", process_events)
    monkeypatch.setattr("bot.bot.asyncio.sleep", AsyncMock())

    await bot._watch_core_runtime_state()

    assert bot.remote is not None
    assert bot.remote.command_prefix == "?"
    assert bot.command_prefix == "?"
    assert bot._config_revision == "config-v2"
    process_events.assert_awaited_once_with(
        [
            {
                "id": "delivery-1",
                "event": "bridge.dashboard_message",
                "payload": {"message_id": 1},
            }
        ]
    )
    await bot.close()


@pytest.mark.asyncio
async def test_run_bot_waits_for_core_before_starting_discord(monkeypatch):
    class StopRun(Exception):
        pass

    settings = Settings(
        umbrella_core_url="https://core.test",
        umbrella_core_api_key="key",
    )
    fetch_state = AsyncMock(
        side_effect=[UmbrellaCoreError("offline"), runtime_state()]
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
    monkeypatch.setattr(main, "fetch_bot_runtime_state", fetch_state)
    monkeypatch.setattr(main, "UmbrellaBot", lambda *args, **kwargs: bot)
    monkeypatch.setattr(main.asyncio, "sleep", sleep)

    with pytest.raises(StopRun):
        await main.run_bot(settings)

    assert fetch_state.await_count == 2
    sleep.assert_awaited_once_with(main.CORE_RETRY_INTERVAL_SECONDS)
    bot.close.assert_awaited_once()
