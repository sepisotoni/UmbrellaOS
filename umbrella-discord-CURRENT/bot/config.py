"""
bot/config.py — umbrella-discord's settings. Deliberately much smaller
than Moo-assistant's bot/config.py: no AI provider keys, no model routing
config, no knowledge-channel constants - all of that lives in
umbrella-core now (config/settings.py + the dashboard-configurable
SettingsService values), reached over UmbrellaCoreClient rather than
constructed here in-process.

The Core URL and API key are kept as hard env vars; the Discord bot token
and other runtime settings are fetched from Core.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic_settings import BaseSettings, SettingsConfigDict

from bot.services.umbrella_core_client import UmbrellaCoreError

if TYPE_CHECKING:
    from bot.services.umbrella_core_client import UmbrellaCoreClient


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    umbrella_core_url: str
    umbrella_core_api_key: str


class BotTokenUnavailable(RuntimeError):
    """Raised when Core has no usable Discord bot token configured."""


async def fetch_discord_bot_token(core: "UmbrellaCoreClient") -> str:
    try:
        setting = await core.get("/api/v1/settings/discord.bot_token")
    except UmbrellaCoreError as exc:
        if exc.status_code == 404:
            raise BotTokenUnavailable(
                "Core setting 'discord.bot_token' is not configured"
            ) from exc
        raise

    token = setting.get("value")
    if not isinstance(token, str) or not token.strip() or token.strip() == "***":
        raise BotTokenUnavailable(
            "Core setting 'discord.bot_token' is empty or masked"
        )
    return token.strip()


@dataclass
class RemoteConfig:
    """
    Bot-wide configuration fetched from Core. Guild-specific configuration
    is stored separately in GuildConfig.
    """

    callback_url: str | None
    callback_port: int
    command_prefix: str


@dataclass
class GuildConfig:
    guild_id: int
    name: str
    channels: list[dict[str, Any]]
    roles: list[dict[str, Any]]
    staff_alert_channel_id: int | None
    verified_role_id: int | None
    owner_role_id: int | None
    admin_role_id: int | None
    moderator_role_id: int | None
    helper_role_id: int | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "GuildConfig":
        def _snowflake(value: Any) -> int | None:
            return int(value) if value not in (None, "") else None

        return cls(
            guild_id=int(data["guild_id"]),
            name=str(data["name"]),
            channels=data.get("channels", []),
            roles=data.get("roles", []),
            staff_alert_channel_id=_snowflake(data.get("staff_alert_channel_id")),
            verified_role_id=_snowflake(data.get("verified_role_id")),
            owner_role_id=_snowflake(data.get("owner_role_id")),
            admin_role_id=_snowflake(data.get("admin_role_id")),
            moderator_role_id=_snowflake(data.get("moderator_role_id")),
            helper_role_id=_snowflake(data.get("helper_role_id")),
        )


async def fetch_bot_config(core: "UmbrellaCoreClient") -> RemoteConfig:
    """
    Fetch all RemoteConfig values from core's settings API. Falls back to
    safe defaults for keys that are missing or empty, but propagates other
    Core errors so startup can wait for Core to become available.

    Called once from UmbrellaBot.setup_hook; the result is stored as
    self.remote so cogs can read it without making their own API calls.
    """
    # Fetch bot-wide settings individually to avoid coupling to the
    # settings list endpoint's response shape.
    keys = [
        "discord.callback_url",
        "discord.callback_port",
        "discord.command_prefix",
    ]

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
        except UmbrellaCoreError as exc:
            if exc.status_code != 404:
                raise
            values[key] = ""

    return RemoteConfig(
        callback_url=values.get("discord.callback_url") or None,
        callback_port=_int_default(values.get("discord.callback_port", ""), 8080),
        command_prefix=values.get("discord.command_prefix") or "!",
    )
