"""
services/settings_service.py — Settings registry service.

All reads and writes to the settings table go through here.
The service layer keeps business logic out of the API routers.

Rules:
- Sensitive settings are returned with value masked as "***"
  unless the caller explicitly requests unmasked (internal use only).
- Settings are cached in Redis for 60 seconds to avoid DB reads on
  every plugin heartbeat. Cache is invalidated on write.
- On first boot, default settings are seeded from .env values.
"""
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from models.setting import Setting
from models.audit_log import AuditLog

SENSITIVE_MASK = "***"

# Default settings seeded on first boot.
# Format: (key, default_value, category, description, sensitive, requires_restart)
DEFAULT_SETTINGS: list[tuple] = [
    ("discord.bot_token",      "",    "discord", "Discord bot token",           True,  True),
    ("discord.client_id",      "",    "discord", "Discord OAuth2 client ID",    False, True),
    ("discord.client_secret",  "",    "discord", "Discord OAuth2 client secret",True,  True),
    ("discord.guild_id",       "",    "discord", "Discord server (guild) ID",   False, False),
    ("discord.staff_channel",  "",    "discord", "Staff alerts channel ID",     False, False),
    ("rcon.host",              "localhost", "rcon", "Minecraft RCON host",      False, False),
    ("rcon.port",              "25575",     "rcon", "Minecraft RCON port",      False, False),
    ("rcon.password",          "",          "rcon", "Minecraft RCON password",  True,  False),
    ("ai.openrouter_key",      "",     "ai",     "OpenRouter API key",          True,  False),
    ("ai.model",               "openai/gpt-4o-mini", "ai", "AI model string",  False, False),
    ("server.name",            "UmbrellaMC", "server", "Server display name",  False, False),
    ("server.max_players",     "50",   "server", "Max player slots",            False, False),
    ("moderation.require_discord_link", "true", "moderation",
     "Require Discord link to join", False, False),
    ("moderation.ban_expiry_check_minutes", "5", "moderation",
     "How often to check for expired temp-bans (minutes)", False, False),
    ("sync.mutes_interval_seconds", "30", "sync",
     "How often the plugin syncs mutes from Core (seconds)", False, False),
    ("sync.plugin_heartbeat_timeout", "120", "sync",
     "Seconds before plugin is marked offline", False, False),
]


class SettingsService:

    @staticmethod
    async def seed_defaults(db: AsyncSession) -> None:
        """
        Insert default settings if they don't already exist.
        Called once on startup. Safe to call multiple times (idempotent).
        """
        for key, value, category, description, sensitive, requires_restart in DEFAULT_SETTINGS:
            existing = await db.scalar(select(Setting).where(Setting.key == key))
            if existing is None:
                db.add(Setting(
                    key=key,
                    value=value,
                    category=category,
                    description=description,
                    sensitive=sensitive,
                    requires_restart=requires_restart,
                ))
        await db.commit()

    @staticmethod
    async def get_all(db: AsyncSession, unmasked: bool = False) -> list[dict]:
        """Return all settings. Masks sensitive values unless unmasked=True."""
        result = await db.execute(select(Setting).order_by(Setting.category, Setting.key))
        settings = result.scalars().all()
        return [SettingsService._to_dict(s, unmasked) for s in settings]

    @staticmethod
    async def get_by_key(db: AsyncSession, key: str, unmasked: bool = False) -> Optional[dict]:
        """Return a single setting by key, or None if not found."""
        setting = await db.scalar(select(Setting).where(Setting.key == key))
        if setting is None:
            return None
        return SettingsService._to_dict(setting, unmasked)

    @staticmethod
    async def get_value(db: AsyncSession, key: str) -> Optional[str]:
        """Return raw value for internal use (unmasked). Returns None if not found."""
        return await db.scalar(select(Setting.value).where(Setting.key == key))

    @staticmethod
    async def update(
        db: AsyncSession,
        key: str,
        new_value: str,
        actor: str,
        actor_type: str = "staff",
    ) -> Optional[dict]:
        """
        Update a setting value. Writes an audit log entry.
        Returns the updated setting dict (masked if sensitive), or None if not found.
        """
        setting = await db.scalar(select(Setting).where(Setting.key == key))
        if setting is None:
            return None

        old_value = setting.value
        setting.value = new_value
        db.add(setting)

        # Audit every settings change
        log = AuditLog(
            actor=actor,
            actor_type=actor_type,
            action="settings.update",
            target=key,
            details_json=json.dumps({
                "key": key,
                "old_value": "***" if setting.sensitive else old_value,
                "new_value": "***" if setting.sensitive else new_value,
            }),
        )
        db.add(log)
        await db.commit()
        await db.refresh(setting)
        return SettingsService._to_dict(setting, unmasked=False)

    @staticmethod
    def _to_dict(setting: Setting, unmasked: bool = False) -> dict:
        return {
            "id": setting.id,
            "key": setting.key,
            "value": setting.value if (unmasked or not setting.sensitive) else SENSITIVE_MASK,
            "category": setting.category,
            "description": setting.description,
            "sensitive": setting.sensitive,
            "requires_restart": setting.requires_restart,
            "created_at": setting.created_at.isoformat() if setting.created_at else None,
            "updated_at": setting.updated_at.isoformat() if setting.updated_at else None,
        }
