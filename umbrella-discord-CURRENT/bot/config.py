"""
bot/config.py — umbrella-discord's settings. Deliberately much smaller
than Moo-assistant's bot/config.py: no AI provider keys, no model routing
config, no knowledge-channel constants - all of that lives in
umbrella-core now (config/settings.py + the dashboard-configurable
SettingsService values), reached over UmbrellaCoreClient rather than
constructed here in-process.

Only three values are kept as hard env vars (see Settings below);
everything else is fetched from core's settings API at startup and
stored in a RemoteConfig instance on the bot (self.remote).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from bot.services.umbrella_core_client import UmbrellaCoreClient


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # The three env vars that must be present in the environment — they
    # cannot live in the DB because they are needed to connect to core in
    # the first place (chicken-and-egg), or are the bot's own identity.
    discord_bot_token: str
    umbrella_core_url: str = "https://umbrellaos-core.onrender.com"
    umbrella_core_api_key: str


@dataclass
class RemoteConfig:
    """
    Configuration values fetched from umbrella-core's settings API at
    startup. All fields that used to be read from .env now live here so
    they can be updated via the dashboard without a bot redeploy.
    """
    guild_id: int | None
    staff_alert_channel_id: int | None
    verified_role_id: int
    owner_role_id: int
    callback_url: str | None
    callback_port: int
    command_prefix: str


async def fetch_bot_config(core: "UmbrellaCoreClient") -> RemoteConfig:
    """
    Fetch all RemoteConfig values from core's settings API in a single
    batch GET. Falls back to safe defaults for each key that is missing
    or empty, so a partially-configured core never prevents the bot from
    starting.

    Called once from UmbrellaBot.setup_hook; the result is stored as
    self.remote so cogs can read it without making their own API calls.
    """
    # Fetch all discord.* settings in one call via the /api/v1/settings
    # list endpoint filtered to the discord category. We use individual
    # GETs to avoid coupling to endpoint shape — each is one DB read
    # that is Redis-cached for 60 s anyway.
    keys = [
        "discord.guild_id",
        "discord.staff_alert_channel_id",
        "discord.verified_role_id",
        "discord.owner_role_id",
        "discord.callback_url",
        "discord.callback_port",
        "discord.command_prefix",
    ]

    def _int_or_none(val: str) -> int | None:
        try:
            return int(val) if val else None
        except (ValueError, TypeError):
            return None

    def _int_default(val: str, default: int) -> int:
        try:
            return int(val) if val else default
        except (ValueError, TypeError):
            return default

    values: dict[str, str] = {}
    for key in keys:
        try:
            data = await core.get(f"/api/v1/settings/{key}")
            values[key] = data.get("value") or ""
        except Exception:
            values[key] = ""

    return RemoteConfig(
        guild_id=_int_or_none(values.get("discord.guild_id", "")),
        staff_alert_channel_id=_int_or_none(values.get("discord.staff_alert_channel_id", "")),
        verified_role_id=_int_default(values.get("discord.verified_role_id", ""), 0),
        owner_role_id=_int_default(values.get("discord.owner_role_id", ""), 0),
        callback_url=values.get("discord.callback_url") or None,
        callback_port=_int_default(values.get("discord.callback_port", ""), 8080),
        command_prefix=values.get("discord.command_prefix") or "!",
    )
