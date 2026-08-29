"""
api/routers/bridge.py — Minecraft-Discord chat bridge endpoints.

POST  /api/v1/bridge/message    — Receive chat message from MC, Discord, or dashboard
GET   /api/v1/bridge/messages   — List recent chat messages
GET   /api/v1/bridge/settings   — Get bridge settings
PATCH /api/v1/bridge/settings   — Update bridge settings

FIX (FINDING-011): DASHBOARD source broadcasts were persisted but never
forwarded (forwarded=False, targets=[]). Staff global broadcasts from the
dashboard now forward to both minecraft and discord when bridge mode is
'full', matching the intent of broadcastGlobalMessage(). Also:
- ?source=DASHBOARD is now a valid filter in GET /messages.
- body.scope is read (treated as a hint for full-mode broadcast direction).

FIX (FINDING-012): bridge settings PATCH wrote boolean values as \"true\"/\"false\"
strings via direct Setting upserts that bypassed SettingsService. Boolean
parsing on read was exact-string \"true\" only — \"True\" or \"1\" silently
treated as false. Now uses SettingsService.update() for existing rows (which
audits and syncs .env) and preserves the \"true\"/\"false\" normalisation on write.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import ChatMessage, Setting, PlayerLanguage
from api.middleware.auth import require_admin_key
from api.dependencies.permissions import require_permission
from services.translation_service import translate_message, get_player_language
from services.settings_service import SettingsService

router = APIRouter(prefix="/api/v1/bridge", tags=["bridge"])


class BridgeMessageRequest(BaseModel):
    source: str = "DASHBOARD"  # "minecraft", "discord", or "DASHBOARD"
    player_uuid: str | None = None
    player_name: str | None = None
    discord_id: str | None = None
    message: str
    channel_id: str | None = None
    scope: str | None = None  # "minecraft", "discord", or None (both) for DASHBOARD broadcasts


class BridgeMessageResponse(BaseModel):
    forwarded: bool
    targets: list[str] = []
    message_id: int
    translated_message: str | None = None


class ChatMessageSchema(BaseModel):
    id: int
    source: str
    player_uuid: str | None
    player_name: str | None = None
    discord_id: str | None
    discord_channel_id: str | None
    message: str
    translated_message: str | None
    timestamp: datetime
    filtered: bool

    class Config:
        from_attributes = True


class BridgeSettingsResponse(BaseModel):
    mode: str
    mc_to_discord: bool
    discord_to_mc: bool
    show_avatars: bool
    discord_channel_id: str


class BridgeSettingsUpdateRequest(BaseModel):
    mode: str | None = None
    mc_to_discord: bool | None = None
    discord_to_mc: bool | None = None
    show_avatars: bool | None = None
    discord_channel_id: str | None = None


def _bool_setting(value: str | None, default: bool = True) -> bool:
    """Parse a DB settings string to bool.

    FIX (FINDING-012): previous code used exact `== "true"` comparison so
    "True", "1", "yes" all silently evaluated as False. Now accepts the same
    set of falsy strings the rest of the codebase uses (matching
    SettingsService and the Discord bot's verification.enabled check).
    """
    if value is None:
        return default
    return value.lower() not in ("false", "0", "no", "off")


@router.post("/message", response_model=BridgeMessageResponse)
async def receive_bridge_message(
    body: BridgeMessageRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> BridgeMessageResponse:
    """
    Receive a chat message from MC plugin, Discord bot, or dashboard broadcast.
    Saves to ChatMessage table and determines if/where it should be forwarded.
    """
    if body.source not in ("minecraft", "discord", "DASHBOARD"):
        raise HTTPException(
            status_code=400,
            detail="Invalid source. Must be 'minecraft', 'discord', or 'DASHBOARD'",
        )

    if body.source == "minecraft" and not body.player_uuid:
        raise HTTPException(status_code=400, detail="player_uuid required for minecraft messages")
    if body.player_uuid == "server":
        body.player_uuid = None
    if body.source == "discord" and not body.discord_id:
        raise HTTPException(status_code=400, detail="discord_id required for discord messages")

    mode_setting = await db.scalar(select(Setting).where(Setting.key == "bridge.mode"))
    bridge_mode = mode_setting.value if mode_setting else "off"

    chat_message = ChatMessage(
        source=body.source,
        player_uuid=body.player_uuid,
        player_name=body.player_name,
        discord_id=body.discord_id,
        discord_channel_id=body.channel_id,
        message=body.message,
    )
    db.add(chat_message)
    await db.flush()

    forwarded = False
    targets: list[str] = []
    translated_message = None

    if bridge_mode == "off":
        pass

    elif bridge_mode == "partial":
        # Partial: discord → minecraft only. DASHBOARD broadcasts go both ways.
        if body.source == "discord":
            forwarded = True
            targets = ["minecraft"]
        elif body.source == "DASHBOARD":
            # FIX-F011: DASHBOARD broadcasts are forwarded in partial mode too,
            # respecting body.scope as a direction hint.
            scope = (body.scope or "").lower()
            if scope == "minecraft":
                forwarded = True
                targets = ["minecraft"]
            elif scope == "discord":
                forwarded = True
                targets = ["discord"]
            else:
                forwarded = True
                targets = ["minecraft"]  # partial: MC only unless scoped

    elif bridge_mode == "full":
        mc_to_discord_val = await db.scalar(
            select(Setting.value).where(Setting.key == "bridge.mc_to_discord")
        )
        discord_to_mc_val = await db.scalar(
            select(Setting.value).where(Setting.key == "bridge.discord_to_mc")
        )
        mc_to_discord = _bool_setting(mc_to_discord_val)
        discord_to_mc = _bool_setting(discord_to_mc_val)

        if body.source == "minecraft" and mc_to_discord:
            forwarded = True
            targets = ["discord"]
            if body.player_uuid:
                player_lang = await get_player_language(body.player_uuid, db)
                if player_lang.auto_translate_outgoing and player_lang.language_code != "en":
                    translated_message, _ = await translate_message(
                        text=body.message,
                        target_language=player_lang.language_code,
                        db=db,
                    )
                    if translated_message and translated_message != body.message:
                        chat_message.translated_message = translated_message

        elif body.source == "discord" and discord_to_mc:
            forwarded = True
            targets = ["minecraft"]

        elif body.source == "DASHBOARD":
            # FIX-F011: DASHBOARD broadcasts forward to both directions in full
            # mode, filtered by body.scope and the per-direction toggle.
            scope = (body.scope or "").lower()
            if scope == "minecraft":
                if discord_to_mc:
                    forwarded = True
                    targets = ["minecraft"]
            elif scope == "discord":
                if mc_to_discord:
                    forwarded = True
                    targets = ["discord"]
            else:
                # No scope hint → broadcast to both directions (respect toggles)
                t = []
                if mc_to_discord:
                    t.append("discord")
                if discord_to_mc:
                    t.append("minecraft")
                if t:
                    forwarded = True
                    targets = t

    await db.commit()
    await db.refresh(chat_message)

    return BridgeMessageResponse(
        forwarded=forwarded,
        targets=targets,
        message_id=chat_message.id,
        translated_message=chat_message.translated_message,
    )


@router.get("/messages", response_model=list[ChatMessageSchema])
async def list_bridge_messages(
    source: str | None = Query(None, description="Filter by source: minecraft, discord, or DASHBOARD"),
    limit: int = Query(100, ge=1, le=500, description="Number of messages to return"),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("players.view")),
) -> list[ChatMessageSchema]:
    """List recent chat messages with optional source filter.

    FIX (FINDING-011): previously rejected 'DASHBOARD' as an invalid source
    filter even though DASHBOARD rows are stored. Now allows all three values.
    """
    query = select(ChatMessage)

    if source:
        # FIX-F011: accept DASHBOARD as a valid filter value
        if source not in ("minecraft", "discord", "DASHBOARD"):
            raise HTTPException(
                status_code=400,
                detail="Invalid source. Must be 'minecraft', 'discord', or 'DASHBOARD'",
            )
        query = query.where(ChatMessage.source == source)

    query = query.order_by(desc(ChatMessage.timestamp)).limit(limit)
    result = await db.execute(query)
    return [ChatMessageSchema.model_validate(m) for m in result.scalars().all()]


@router.get("/settings", response_model=BridgeSettingsResponse)
async def get_bridge_settings(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("settings.view")),
) -> BridgeSettingsResponse:
    """Get all bridge settings."""
    settings_result = await db.execute(
        select(Setting).where(Setting.key.like("bridge.%"))
    )
    settings_dict = {s.key: s.value for s in settings_result.scalars().all()}

    return BridgeSettingsResponse(
        mode=settings_dict.get("bridge.mode", "off"),
        mc_to_discord=_bool_setting(settings_dict.get("bridge.mc_to_discord")),
        discord_to_mc=_bool_setting(settings_dict.get("bridge.discord_to_mc")),
        show_avatars=_bool_setting(settings_dict.get("bridge.show_avatars")),
        discord_channel_id=settings_dict.get("bridge.discord_channel_id", ""),
    )


@router.patch("/settings", response_model=BridgeSettingsResponse)
async def update_bridge_settings(
    body: BridgeSettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("settings.manage")),
) -> BridgeSettingsResponse:
    """Update bridge settings.

    FIX (FINDING-012): previous implementation upserted Setting rows directly,
    bypassing SettingsService entirely — no audit log, no .env sync for any
    bridge.* key in ENV_KEY_MAP. Now routes updates through SettingsService.update()
    for keys that already exist (audit + env sync), and falls back to a direct
    insert only for genuinely new keys (same pattern as settings.py POST /{key}).
    Also uses \"true\"/\"false\" consistently for boolean values rather than relying
    on exact-string comparison that made \"True\" behave as false.
    """
    if body.mode is not None and body.mode not in ("off", "partial", "full"):
        raise HTTPException(status_code=400, detail="Invalid mode. Must be 'off', 'partial', or 'full'")

    actor = "dashboard"

    async def _update_setting(key: str, value: str, description: str) -> None:
        """Route through SettingsService.update if row exists, else insert."""
        result = await SettingsService.update(db=db, key=key, new_value=value, actor=actor)
        if result is None:
            # Row doesn't exist yet — insert with safe defaults
            db.add(Setting(
                key=key, value=value, category="bridge",
                description=description, sensitive=False, requires_restart=False,
            ))
            await db.flush()

    if body.mode is not None:
        await _update_setting("bridge.mode", body.mode, "Bridge mode")
    if body.mc_to_discord is not None:
        await _update_setting(
            "bridge.mc_to_discord",
            "true" if body.mc_to_discord else "false",
            "Forward MC chat to Discord",
        )
    if body.discord_to_mc is not None:
        await _update_setting(
            "bridge.discord_to_mc",
            "true" if body.discord_to_mc else "false",
            "Forward Discord chat to MC",
        )
    if body.show_avatars is not None:
        await _update_setting(
            "bridge.show_avatars",
            "true" if body.show_avatars else "false",
            "Show avatars in bridge",
        )
    if body.discord_channel_id is not None:
        await _update_setting("bridge.discord_channel_id", body.discord_channel_id, "Discord channel ID")

    return await get_bridge_settings(db, _auth)
