"""
main.py — umbrella-discord entry point.
"""

import asyncio
import logging

import discord

from bot.bot import UmbrellaBot
from bot.config import BotTokenUnavailable, Settings, fetch_bot_runtime_state
from bot.services.umbrella_core_client import UmbrellaCoreClient, UmbrellaCoreError

logging.basicConfig(level=logging.INFO)

CORE_RETRY_INTERVAL_SECONDS = 30
BOT_RESTART_DELAY_SECONDS = 5


async def run_bot(settings: Settings) -> None:
    core = UmbrellaCoreClient(
        settings.umbrella_core_url,
        settings.umbrella_core_api_key,
        timeout=90.0,
    )

    while True:
        try:
            runtime_state = await fetch_bot_runtime_state(core)
            if runtime_state is None:
                raise UmbrellaCoreError(
                    "Core returned no initial bot runtime state"
                )
            token = runtime_state.discord_token
            if token is None:
                raise BotTokenUnavailable(
                    "Core setting 'discord.bot_token' is not configured"
                )
        except BotTokenUnavailable as exc:
            logging.error(
                "%s; retrying Core in %d seconds.",
                exc,
                CORE_RETRY_INTERVAL_SECONDS,
            )
            await asyncio.sleep(CORE_RETRY_INTERVAL_SECONDS)
            continue
        except UmbrellaCoreError as exc:
            logging.error(
                "Could not retrieve bot runtime state from Core (status=%s); "
                "retrying in %d seconds.",
                exc.status_code,
                CORE_RETRY_INTERVAL_SECONDS,
            )
            await asyncio.sleep(CORE_RETRY_INTERVAL_SECONDS)
            continue

        bot = UmbrellaBot(settings, runtime_state, core=core)
        restart_delay = BOT_RESTART_DELAY_SECONDS
        try:
            await bot.start(token)
        except UmbrellaCoreError as exc:
            logging.error(
                "Core was unavailable during bot startup (status=%s); "
                "retrying in %d seconds.",
                exc.status_code,
                CORE_RETRY_INTERVAL_SECONDS,
            )
            restart_delay = CORE_RETRY_INTERVAL_SECONDS
        except discord.LoginFailure:
            logging.error(
                "Discord rejected the bot token from Core; retrying in %d seconds.",
                CORE_RETRY_INTERVAL_SECONDS,
            )
            restart_delay = CORE_RETRY_INTERVAL_SECONDS
        finally:
            await bot.close()

        await asyncio.sleep(restart_delay)


def main() -> None:
    settings = Settings()
    asyncio.run(run_bot(settings))


if __name__ == "__main__":
    main()
