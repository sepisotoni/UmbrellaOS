"""
main.py — umbrella-discord entry point.
"""
import logging

from bot.bot import UmbrellaBot
from bot.config import Settings

logging.basicConfig(level=logging.INFO)


def main() -> None:
    settings = Settings()
    bot = UmbrellaBot(settings)
    bot.run(settings.discord_bot_token)


if __name__ == "__main__":
    main()
