"""
api/routers/translation.py — Translation API endpoints.

POST /api/v1/translation/language        — Set player language preference
GET  /api/v1/translation/language/{uuid}  — Get player language preference
POST /api/v1/translation/translate       — Translate a message
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import PlayerLanguage
from api.middleware.auth import require_admin_key
from services.translation_service import translate_message, set_player_language

router = APIRouter(prefix="/api/v1/translation", tags=["translation"])


class PlayerLanguageRequest(BaseModel):
    player_uuid: str
    language_code: str
    language_name: str
    auto_translate_incoming: bool | None = None
    auto_translate_outgoing: bool | None = None


class PlayerLanguageResponse(BaseModel):
    id: int
    player_uuid: str
    language_code: str
    language_name: str
    auto_translate_incoming: bool
    auto_translate_outgoing: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TranslateRequest(BaseModel):
    text: str
    target_language: str
    player_uuid: str | None = None


class TranslateResponse(BaseModel):
    original: str
    translated: str
    was_translated: bool


@router.post("/language", response_model=PlayerLanguageResponse)
async def set_player_language_endpoint(
    body: PlayerLanguageRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> PlayerLanguageResponse:
    """
    Set or update a player's language preference.
    Called by the Minecraft plugin when a player uses /lang command.
    """
    player_lang = await set_player_language(
        player_uuid=body.player_uuid,
        language_code=body.language_code,
        language_name=body.language_name,
        db=db,
        auto_translate_incoming=body.auto_translate_incoming,
        auto_translate_outgoing=body.auto_translate_outgoing,
    )
    
    return PlayerLanguageResponse.model_validate(player_lang)


@router.get("/language/all", response_model=list[PlayerLanguageResponse])
async def get_all_player_languages(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> list[PlayerLanguageResponse]:
    """
    Get all player language preferences.
    """
    result = await db.execute(select(PlayerLanguage))
    player_langs = result.scalars().all()
    return [PlayerLanguageResponse.model_validate(lang) for lang in player_langs]


@router.get("/language/{player_uuid}", response_model=PlayerLanguageResponse)
async def get_player_language_endpoint(
    player_uuid: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> PlayerLanguageResponse:
    """
    Get a player's language preference.
    Returns default English if not set.
    """
    result = await db.execute(
        select(PlayerLanguage).where(PlayerLanguage.player_uuid == player_uuid)
    )
    player_lang = result.scalar_one_or_none()
    
    if not player_lang:
        # Return default language preference
        default_lang = PlayerLanguage(
            id=0,  # Placeholder ID for default
            player_uuid=player_uuid,
            language_code="en",
            language_name="English",
            auto_translate_incoming=True,
            auto_translate_outgoing=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        return PlayerLanguageResponse.model_validate(default_lang)
    
    return PlayerLanguageResponse.model_validate(player_lang)


@router.post("/translate", response_model=TranslateResponse)
async def translate_message_endpoint(
    body: TranslateRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> TranslateResponse:
    """
    Translate a message to the target language.
    Uses Anthropic Claude API if configured.
    """
    translated, was_translated = await translate_message(
        text=body.text,
        target_language=body.target_language,
        db=db,
    )
    
    return TranslateResponse(
        original=body.text,
        translated=translated,
        was_translated=was_translated,
    )
