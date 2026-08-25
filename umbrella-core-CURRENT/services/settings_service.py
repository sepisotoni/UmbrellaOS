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
from pathlib import Path
from typing import Optional
from dotenv import set_key
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from models.setting import Setting
from models.audit_log import AuditLog

SENSITIVE_MASK = "***"

# Path to the .env file (one directory up from services/)
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

# Maps DB setting keys -> .env variable names, for settings that have
# a real environment-variable counterpart. Settings not listed here
# (e.g. server.max_players) are DB-only and never touch .env.
ENV_KEY_MAP: dict[str, str] = {
    "discord.client_id": "DISCORD_CLIENT_ID",
    "discord.client_secret": "DISCORD_CLIENT_SECRET",
    "discord.bot_token": "DISCORD_BOT_TOKEN",
    "ai.openrouter_key": "OPENROUTER_API_KEY",
    "ai.gemini_api_key": "GEMINI_API_KEY",
    "ai.anthropic_api_key": "ANTHROPIC_API_KEY",
    "rcon.host": "RCON_HOST",
    "rcon.port": "RCON_PORT",
    "rcon.password": "RCON_PASSWORD",
}


def write_env_value(key: str, value: str) -> None:
    """
    Write a setting's value into .env, if that key has a mapped env var.
    No-op for keys with no env counterpart. Safe to call on every update.
    """
    env_var = ENV_KEY_MAP.get(key)
    if env_var is None:
        return
    try:
        set_key(str(ENV_PATH), env_var, value, quote_mode="never")
    except Exception as e:
        # Never let a .env write failure break a settings update
        print(f"[SettingsService] Failed to write {env_var} to .env: {e}")

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
    ("ai.openrouter_enabled",  "true", "ai",     "Use OpenRouter as a model provider", False, False),
    ("ai.model",               "openai/gpt-4o-mini", "ai", "AI model string",  False, False),
    ("ai.anthropic_api_key",   "",     "ai",     "Anthropic API key",          True,  False),
    ("ai.anthropic_enabled",   "true", "ai",     "Use Anthropic as a model provider",  False, False),
    ("ai.gemini_api_key",      "",     "ai",     "Google Gemini API key",       True,  False),
    ("ai.gemini_enabled",      "false", "ai",    "Use Gemini as a model provider",     False, False),
    ("discord.ip_response",    "",     "discord", "Text the bot replies with when someone types !ip in Discord", False, False),
    ("server.name",            "UmbrellaMC", "server", "Server display name",  False, False),
    ("server.max_players",     "50",   "server", "Max player slots",            False, False),
    ("server.maintenance_mode", "false", "server", "Maintenance mode active",  False, False),
    ("server.control.stop_cmd", "", "server", "Shell command to stop MC server (no shell)", False, True),
    ("server.control.start_cmd", "", "server", "Shell command to start MC server", False, True),
    ("server.control.restart_cmd", "", "server", "Shell command to restart MC server", False, True),
    ("server.control.workdir", "", "server", "Working directory for control commands", False, False),
    ("moderation.require_discord_link", "true", "moderation",
     "Require Discord link to join", False, False),
    ("moderation.ban_expiry_check_minutes", "5", "moderation",
     "How often to check for expired temp-bans (minutes)", False, False),
    ("sync.mutes_interval_seconds", "30", "sync",
     "How often the plugin syncs mutes from Core (seconds)", False, False),
    ("sync.plugin_heartbeat_timeout", "120", "sync",
     "Seconds before plugin is marked offline", False, False),
    ("anticheat.enabled",          "true",  "anticheat", "Enable Grim anticheat integration",              False, False),
    ("anticheat.warn_vl_threshold", "10",   "anticheat", "VL below this = warn only (no kick/ban)",        False, False),
    ("anticheat.kick_vl_threshold", "30",   "anticheat", "VL below this = kick; at/above = tempban",       False, False),
    ("anticheat.ai_review",         "true", "anticheat", "AI analyses each flag and adjusts confidence",   False, False),
    ("anticheat.auto_tempban", "true", "anticheat",
     "Auto temp-ban on Grim detection", False, False),
    ("anticheat.tempban_hours", "24", "anticheat",
     "Temp-ban duration in hours", False, False),
    ("anticheat.review_threshold", "1", "anticheat",
     "VL threshold before review task", False, False),
    ("bridge.mode", "off", "bridge", "Chat bridge mode", False, False),
    ("bridge.mc_to_discord", "true", "bridge", "Forward MC chat to Discord", False, False),
    ("bridge.discord_to_mc", "true", "bridge", "Forward Discord chat to MC", False, False),
    ("bridge.show_avatars", "true", "bridge", "Show avatars in bridge", False, False),
    ("bridge.discord_channel_id", "", "bridge", "Bridge Discord channel ID", False, False),
    ("discord.announcements_channel", "", "discord",
     "Announcements Discord channel ID", False, False),
    ("discord.staff_alerts_channel", "", "discord",
     "Staff alerts channel ID", False, False),
    # --- Message templates (P16D) ---
    ("verification.dm_prompt",
     "Hi $PLAYER! To verify your Minecraft account, send this code in-game: $CODE (expires in $EXPIRES)",
     "verification", "DM sent to the player when verification is requested", False, False),
    ("verification.success_message",
     "\u2705 Your Minecraft account **$PLAYER** has been successfully linked!",
     "verification", "DM sent on successful verification", False, False),
    ("verification.error_already_linked",
     "\u274c This Discord account is already linked to a Minecraft account.",
     "verification", "DM sent when the Discord account is already linked", False, False),
    ("verification.error_invalid_code",
     "\u274c Invalid or expired code. Please run /verify in-game again.",
     "verification", "DM sent on bad or expired code", False, False),
    ("verification.ingame_prompt",
     "Check your Discord DMs to complete verification! Code expires in $EXPIRES.",
     "verification", "In-game message shown after /verify is run", False, False),
    ("verification.ingame_success",
     "\u2705 Your Discord account has been linked successfully!",
     "verification", "In-game message shown on successful link", False, False),
    ("verification.nickname_format",
     "$PLAYER",
     "verification", "Format applied to the Discord nickname after verification", False, False),
    ("discord.invite_url",
     "https://discord.gg/yourserver",
     "discord", "Discord invite link used in greeter and other messages", False, False),
    ("greeter.enabled",
     "true",
     "greeter", "Enable or disable the in-game greeter", False, False),
    ("greeter.first_join_message",
     "Welcome to the server, $PLAYER! Join our Discord: $DISCORD_INVITE",
     "greeter", "Message sent to a player on their very first join", False, False),
    ("greeter.return_join_message",
     "Welcome back, $PLAYER!",
     "greeter", "Message sent to a returning player on join", False, False),
    ("chat_responder.enabled",
     "true",
     "chat_responder", "Enable or disable the AI chat keyword responder", False, False),
    ("chat_responder.keywords",
     '["how to join","whats the ip","what\'s the ip","how do i rank up","discord link","how do i appeal","how do i verify","what are the rules"]',
     "chat_responder", "JSON array of keyword phrases that trigger an AI response", False, False),
    ("chat_responder.cooldown_seconds",
     "60",
     "chat_responder", "Seconds a player must wait before triggering another AI response", False, False),
    ("chat_responder.reply_method",
     "chat",
     "chat_responder", "How the AI response is delivered: chat or dm", False, False),
    ("chat_responder.response_style",
     "friendly and brief, 1-2 sentences max",
     "chat_responder", "Tone style hint passed to AI for chat responses", False, False),
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

        # Sync DB settings from .env on startup — gated behind
        # SEED_FROM_ENV=true, and automatically reset to false in .env
        # once the sync runs, so a stale .env value can't silently
        # resurface on a later boot after being intentionally changed via
        # the dashboard. This whole block is a no-op unless an operator
        # explicitly opts in for this one boot.
        #
        # Within that opt-in:
        # Default mode: GAP-FILL ONLY — only fills settings that are
        # currently EMPTY in the DB, never overwrites a value already
        # set via the dashboard.
        #
        # Emergency mode: if FORCE_ENV_OVERRIDE=true in .env, every
        # mapped setting is force-overwritten from .env instead,
        # regardless of its current DB value. Intended for one-time
        # lockout recovery.
        from config.settings import get_settings
        env = get_settings()

        if not env.seed_from_env:
            return

        # Built generically from ENV_KEY_MAP + the raw process environment
        # — not hand-picked pydantic Settings attributes. This matters
        # concretely for the AI provider keys (ai.openrouter_key,
        # ai.gemini_api_key, ai.anthropic_api_key): those are DB-only
        # settings with no pydantic Settings field at all (see
        # config/settings.py's Phase 5 comment on why provider credentials
        # live in the DB, not pydantic env config) — reading them via
        # `env.<attr>` would either not exist or silently read the wrong
        # thing. Reading the same ENV_KEY_MAP this function's write-back
        # path already uses keeps both directions of the sync using one
        # source of truth for "which .env variable does this DB key map
        # to," rather than two separate, driftable lists.
        import os

        env_values = {db_key: os.environ.get(env_var, "") for db_key, env_var in ENV_KEY_MAP.items()}

        if env.force_env_override:
            print("[SettingsService] FORCE_ENV_OVERRIDE=true — force-syncing settings from .env")
            for key, val in env_values.items():
                if not val:
                    continue
                setting = await db.scalar(select(Setting).where(Setting.key == key))
                if setting is not None:
                    setting.value = val
                    print(f"[SettingsService]   forced {key} from .env")
        else:
            print("[SettingsService] SEED_FROM_ENV=true — gap-filling empty settings from .env")
            for key, val in env_values.items():
                if not val:
                    continue
                setting = await db.scalar(select(Setting).where(Setting.key == key))
                if setting is not None and not setting.value:
                    setting.value = val

        await db.commit()

        # Auto-reset: this was a one-boot opt-in, not a standing mode.
        # Reset SEED_FROM_ENV (and FORCE_ENV_OVERRIDE, if it was also on —
        # same "recovery flag, turn off after use" reasoning that flag's
        # own docstring already described, now automated instead of
        # relying on an operator remembering to flip it back manually).
        set_key(str(ENV_PATH), "SEED_FROM_ENV", "false", quote_mode="never")
        if env.force_env_override:
            set_key(str(ENV_PATH), "FORCE_ENV_OVERRIDE", "false", quote_mode="never")
        print("[SettingsService] .env sync complete — SEED_FROM_ENV reset to false in .env.")

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

        # Keep .env in sync so a backend restart doesn't lose this value
        write_env_value(key, new_value)

        return SettingsService._to_dict(setting, unmasked=False)

    @staticmethod
    async def set_value(
        db: AsyncSession,
        key: str,
        value: str,
        category: str = "general",
        actor: str = "system",
    ) -> None:
        """Upsert a setting value (used by AI config apply)."""
        setting = await db.scalar(select(Setting).where(Setting.key == key))
        if setting is None:
            setting = Setting(
                key=key,
                value=value,
                category=category,
                description=f"Auto-created: {key}",
                sensitive=False,
                requires_restart=False,
            )
            db.add(setting)
        else:
            setting.value = value
        await db.flush()

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
