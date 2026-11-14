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


@dataclass
class BotRuntimeState:
    config_revision: str
    token_revision: str
    discord_token: str | None
    token_changed: bool
    remote: RemoteConfig | None
    guild_configs: dict[int, GuildConfig] | None


async def fetch_bot_runtime_state(
    core: "UmbrellaCoreClient",
    *,
    config_revision: str | None = None,
    token_revision: str | None = None,
) -> BotRuntimeState | None:
    """Fetch one conditional snapshot of Core-managed bot configuration."""
    data = await core.get_bot_runtime_state(
        config_revision=config_revision,
        token_revision=token_revision,
    )
    if data is None:
        return None

    is_initial_state = config_revision is None and token_revision is None
    next_config_revision = data.get("config_revision")
    next_token_revision = data.get("token_revision")
    if not isinstance(next_config_revision, str) or not isinstance(
        next_token_revision, str
    ):
        raise UmbrellaCoreError("umbrella-core returned invalid bot revisions")

    token_changed = "discord_token" in data
    if is_initial_state and not token_changed:
        raise UmbrellaCoreError("Core omitted the initial Discord bot token")
    raw_token = data.get("discord_token")
    if token_changed and raw_token is not None and not isinstance(raw_token, str):
        raise UmbrellaCoreError("umbrella-core returned an invalid Discord token")
    token = None
    if isinstance(raw_token, str):
        token = raw_token.strip() or None

    remote = None
    guild_configs = None
    if "config" in data:
        config = data["config"]
        if not isinstance(config, dict):
            raise UmbrellaCoreError("umbrella-core returned invalid bot config")
        remote_data = config.get("remote")
        guild_data = config.get("guilds")
        if not isinstance(remote_data, dict) or not isinstance(guild_data, list):
            raise UmbrellaCoreError("umbrella-core returned invalid bot config")
        try:
            callback_port = int(remote_data.get("callback_port", 8080))
            remote = RemoteConfig(
                callback_url=remote_data.get("callback_url"),
                callback_port=callback_port,
                command_prefix=remote_data.get("command_prefix") or "!",
            )
            guild_configs = {
                guild.guild_id: guild
                for guild in map(GuildConfig.from_api, guild_data)
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise UmbrellaCoreError(
                "umbrella-core returned invalid bot config"
            ) from exc
    elif is_initial_state:
        raise UmbrellaCoreError("Core omitted the initial bot config")

    return BotRuntimeState(
        config_revision=next_config_revision,
        token_revision=next_token_revision,
        discord_token=token,
        token_changed=token_changed,
        remote=remote,
        guild_configs=guild_configs,
    )
