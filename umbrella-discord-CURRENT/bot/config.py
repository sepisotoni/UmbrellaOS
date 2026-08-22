"""
bot/config.py — umbrella-discord's settings. Deliberately much smaller
than Moo-assistant's bot/config.py: no AI provider keys, no model routing
config, no knowledge-channel constants - all of that lives in
umbrella-core now (config/settings.py + the dashboard-configurable
SettingsService values), reached over UmbrellaCoreClient rather than
constructed here in-process.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    discord_bot_token: str
    command_prefix: str = "!"

    # Discord guild/server this bot operates in (used for verified role assignment)
    discord_guild_id: int | None = None

    # The one integration boundary this service has (see
    # bot/services/umbrella_core_client.py) - everything else is reached
    # through it, never constructed locally.
    umbrella_core_url: str = "https://umbrellaos-core.onrender.com"
    umbrella_core_api_key: str

    # Where notifications_cog.py posts newly-surfaced staff escalations.
    # Optional and unset by default: the poller keeps running either way,
    # but if this is None it skips posting AND skips mark_notified (see
    # notifications_cog.py) - an unconfigured channel must never cause
    # escalations to silently disappear from the queue unseen.
    staff_alert_channel_id: int | None = None

    # Role assigned to a player on successful Minecraft account verification.
    # Optional: if 0 or unset, role assignment is skipped silently.
    discord_verified_role_id: int = 0
