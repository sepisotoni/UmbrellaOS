"""
api/routers/bridge.py — Minecraft-Discord chat bridge endpoints.

POST /api/v1/bridge/message       — Receive chat message from MC or Discord
GET  /api/v1/bridge/messages      — List recent chat messages
GET  /api/v1/bridge/settings     — Get bridge settings
PATCH /api/v1/bridge/settings    — Update bridge settings
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

router = APIRouter(prefix="/api/v1/bridge", tags=["bridge"])


class BridgeMessageRequest(BaseModel):
    source: str  # "minecraft" or "discord"
    player_uuid: str | None = None
    discord_id: str | None = None
    message: str
    channel_id: str | None = None


class BridgeMessageResponse(BaseModel):
    forwarded: bool
    targets: list[str] = []
    message_id: int
    translated_message: str | None = None


class ChatMessageSchema(BaseModel):
    id: int
    source: str
    player_uuid: str | None
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


@router.post("/message", response_model=BridgeMessageResponse)
async def receive_bridge_message(
    body: BridgeMessageRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> BridgeMessageResponse:
    """
    Receive a chat message from either MC plugin or Discord bot.
    Saves to ChatMessage table and determines if it should be forwarded.
    """
    # Validate source
    if body.source not in ("minecraft", "discord"):
        raise HTTPException(status_code=400, detail="Invalid source. Must be 'minecraft' or 'discord'")
    
    # Validate that at least one identifier is provided
    if body.source == "minecraft" and not body.player_uuid:
        raise HTTPException(status_code=400, detail="player_uuid required for minecraft messages")
    if body.source == "discord" and not body.discord_id:
        raise HTTPException(status_code=400, detail="discord_id required for discord messages")

    # Get bridge mode setting
    mode_result = await db.execute(
        select(Setting).where(Setting.key == "bridge.mode")
    )
    mode_setting = mode_result.scalar_one_or_none()
    bridge_mode = mode_setting.value if mode_setting else "off"

    # Save message to database
    chat_message = ChatMessage(
        source=body.source,
        player_uuid=body.player_uuid,
        discord_id=body.discord_id,
        discord_channel_id=body.channel_id,
        message=body.message,
    )
    db.add(chat_message)
    await db.flush()

    # Determine if message should be forwarded
    forwarded = False
    targets = []
    translated_message = None

    if bridge_mode == "off":
        forwarded = False
    elif bridge_mode == "partial":
        # In partial mode, only forward discord to mc, not mc to discord
        if body.source == "discord":
            forwarded = True
            targets = ["minecraft"]
        else:
            forwarded = False
    elif bridge_mode == "full":
        # In full mode, forward both ways
        if body.source == "minecraft":
            mc_to_discord_result = await db.execute(
                select(Setting).where(Setting.key == "bridge.mc_to_discord")
            )
            mc_to_discord = mc_to_discord_result.scalar_one_or_none()
            if mc_to_discord and mc_to_discord.value == "true":
                forwarded = True
                targets = ["discord"]
                # Translate if player has translation enabled
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
        elif body.source == "discord":
            discord_to_mc_result = await db.execute(
                select(Setting).where(Setting.key == "bridge.discord_to_mc")
            )
            discord_to_mc = discord_to_mc_result.scalar_one_or_none()
            if discord_to_mc and discord_to_mc.value == "true":
                forwarded = True
                targets = ["minecraft"]

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
    source: str | None = Query(None, description="Filter by source (minecraft/discord)"),
    limit: int = Query(100, ge=1, le=500, description="Number of messages to return"),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("players.view")),
) -> list[ChatMessageSchema]:
    """List recent chat messages with optional source filter."""
    query = select(ChatMessage)

    if source:
        if source not in ("minecraft", "discord"):
            raise HTTPException(status_code=400, detail="Invalid source. Must be 'minecraft' or 'discord'")
        query = query.where(ChatMessage.source == source)

    query = query.order_by(desc(ChatMessage.timestamp)).limit(limit)

    result = await db.execute(query)
    messages = result.scalars().all()

    return [ChatMessageSchema.model_validate(m) for m in messages]


@router.get("/settings", response_model=BridgeSettingsResponse)
async def get_bridge_settings(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("settings.view")),
) -> BridgeSettingsResponse:
    """Get all bridge settings."""
    settings_result = await db.execute(
        select(Setting).where(Setting.key.like("bridge.%"))
    )
    settings = settings_result.scalars().all()

    settings_dict = {s.key: s.value for s in settings}

    return BridgeSettingsResponse(
        mode=settings_dict.get("bridge.mode", "off"),
        mc_to_discord=settings_dict.get("bridge.mc_to_discord", "true") == "true",
        discord_to_mc=settings_dict.get("bridge.discord_to_mc", "true") == "true",
        show_avatars=settings_dict.get("bridge.show_avatars", "true") == "true",
        discord_channel_id=settings_dict.get("bridge.discord_channel_id", ""),
    )


@router.patch("/settings", response_model=BridgeSettingsResponse)
async def update_bridge_settings(
    body: BridgeSettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("settings.manage")),
) -> BridgeSettingsResponse:
    """Update bridge settings."""
    # Validate mode if provided
    if body.mode is not None and body.mode not in ("off", "partial", "full"):
        raise HTTPException(status_code=400, detail="Invalid mode. Must be 'off', 'partial', or 'full'")

    # Update each setting if provided
    if body.mode is not None:
        mode_result = await db.execute(select(Setting).where(Setting.key == "bridge.mode"))
        mode_setting = mode_result.scalar_one_or_none()
        if mode_setting:
            mode_setting.value = body.mode
        else:
            db.add(Setting(key="bridge.mode", value=body.mode, category="bridge", description="Bridge mode", sensitive=False, requires_restart=False))

    if body.mc_to_discord is not None:
        mc_to_discord_result = await db.execute(select(Setting).where(Setting.key == "bridge.mc_to_discord"))
        mc_to_discord_setting = mc_to_discord_result.scalar_one_or_none()
        if mc_to_discord_setting:
            mc_to_discord_setting.value = "true" if body.mc_to_discord else "false"
        else:
            db.add(Setting(key="bridge.mc_to_discord", value="true" if body.mc_to_discord else "false", category="bridge", description="Forward MC to Discord", sensitive=False, requires_restart=False))

    if body.discord_to_mc is not None:
        discord_to_mc_result = await db.execute(select(Setting).where(Setting.key == "bridge.discord_to_mc"))
        discord_to_mc_setting = discord_to_mc_result.scalar_one_or_none()
        if discord_to_mc_setting:
            discord_to_mc_setting.value = "true" if body.discord_to_mc else "false"
        else:
            db.add(Setting(key="bridge.discord_to_mc", value="true" if body.discord_to_mc else "false", category="bridge", description="Forward Discord to MC", sensitive=False, requires_restart=False))

    if body.show_avatars is not None:
        show_avatars_result = await db.execute(select(Setting).where(Setting.key == "bridge.show_avatars"))
        show_avatars_setting = show_avatars_result.scalar_one_or_none()
        if show_avatars_setting:
            show_avatars_setting.value = "true" if body.show_avatars else "false"
        else:
            db.add(Setting(key="bridge.show_avatars", value="true" if body.show_avatars else "false", category="bridge", description="Show avatars", sensitive=False, requires_restart=False))

    if body.discord_channel_id is not None:
        discord_channel_id_result = await db.execute(select(Setting).where(Setting.key == "bridge.discord_channel_id"))
        discord_channel_id_setting = discord_channel_id_result.scalar_one_or_none()
        if discord_channel_id_setting:
            discord_channel_id_setting.value = body.discord_channel_id
        else:
            db.add(Setting(key="bridge.discord_channel_id", value=body.discord_channel_id, category="bridge", description="Discord channel ID", sensitive=False, requires_restart=False))

    await db.flush()

    # Return updated settings
    return await get_bridge_settings(db, _auth)
