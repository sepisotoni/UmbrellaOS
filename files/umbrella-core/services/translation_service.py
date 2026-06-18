"""
services/translation_service.py — Translation service for chat messages.

Uses Anthropic Claude API to translate Minecraft chat messages to different languages.
"""
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import PlayerLanguage
from services.settings_service import SettingsService


class TranslationServiceError(Exception):
    """Raised when translation service encounters an error."""
    pass


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL_NAME = "claude-haiku-4-5-20251001"


MINECRAFT_CONTEXT = """You are translating Minecraft server chat.
Rules:
- Do NOT translate: usernames, /commands, item names like netherite, elytra, coordinates, plugin names
- Keep Minecraft slang: TPA, PvP, GG, AFK as-is
- Return ONLY the translated text, nothing else
- If already in target language, return the original text"""


async def _get_anthropic_api_key(db: AsyncSession) -> str:
    """Get Anthropic API key from settings. Returns None if not set."""
    api_key = await SettingsService.get_value(db, "ai.anthropic_api_key")
    return api_key


async def translate_message(
    text: str,
    target_language: str,
    db: AsyncSession,
) -> tuple[str, bool]:
    """
    Translate a message to the target language.
    
    Args:
        text: The text to translate
        target_language: Target language code (e.g., "es", "fr", "de")
        db: Database session
    
    Returns:
        Tuple of (translated_text, was_translated)
    """
    # Check if API key is configured
    api_key = await _get_anthropic_api_key(db)
    if not api_key:
        # No API key configured, return original text unchanged
        return text, False
    
    # If text is already in target language, return unchanged
    if target_language == "en":
        return text, False
    
    try:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        
        language_names = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "pt": "Portuguese",
        }
        language_name = language_names.get(target_language, target_language)
        
        payload = {
            "model": MODEL_NAME,
            "max_tokens": 512,
            "messages": [
                {
                    "role": "user",
                    "content": f"{MINECRAFT_CONTEXT}\n\nTranslate to {language_name}: {text}",
                }
            ],
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
            if response.status_code != 200:
                raise TranslationServiceError(
                    f"Anthropic API error: {response.status_code} {response.text}"
                )
            
            data = response.json()
            translated = data.get("content", [{}])[0].get("text", text)
            
            # Clean up any additional text (API sometimes adds explanations)
            translated = translated.strip()
            
            # If translation failed or is empty, return original
            if not translated or translated == text:
                return text, False
            
            return translated, True
    
    except Exception as e:
        # On any error, log and return original text unchanged
        import logging
        logging.error(f"Translation error: {e}")
        return text, False


async def get_player_language(
    player_uuid: str,
    db: AsyncSession,
) -> PlayerLanguage:
    """
    Get player's language preference or return default.
    
    Args:
        player_uuid: Player UUID
        db: Database session
    
    Returns:
        PlayerLanguage record (default English if not set)
    """
    result = await db.execute(
        select(PlayerLanguage).where(PlayerLanguage.player_uuid == player_uuid)
    )
    player_lang = result.scalar_one_or_none()
    
    if not player_lang:
        # Return default language preference
        return PlayerLanguage(
            player_uuid=player_uuid,
            language_code="en",
            language_name="English",
            auto_translate_incoming=True,
            auto_translate_outgoing=False,
        )
    
    return player_lang


async def set_player_language(
    player_uuid: str,
    language_code: str,
    language_name: str,
    db: AsyncSession,
    auto_translate_incoming: bool | None = None,
    auto_translate_outgoing: bool | None = None,
) -> PlayerLanguage:
    """
    Set or update player's language preference.
    
    Args:
        player_uuid: Player UUID
        language_code: Language code (e.g., "en", "es", "fr")
        language_name: Language name (e.g., "English", "Spanish", "French")
        db: Database session
        auto_translate_incoming: Optional setting
        auto_translate_outgoing: Optional setting
    
    Returns:
        Updated PlayerLanguage record
    """
    result = await db.execute(
        select(PlayerLanguage).where(PlayerLanguage.player_uuid == player_uuid)
    )
    player_lang = result.scalar_one_or_none()
    
    if player_lang:
        # Update existing record
        player_lang.language_code = language_code
        player_lang.language_name = language_name
        if auto_translate_incoming is not None:
            player_lang.auto_translate_incoming = auto_translate_incoming
        if auto_translate_outgoing is not None:
            player_lang.auto_translate_outgoing = auto_translate_outgoing
    else:
        # Create new record
        player_lang = PlayerLanguage(
            player_uuid=player_uuid,
            language_code=language_code,
            language_name=language_name,
            auto_translate_incoming=auto_translate_incoming if auto_translate_incoming is not None else True,
            auto_translate_outgoing=auto_translate_outgoing if auto_translate_outgoing is not None else False,
        )
        db.add(player_lang)
    
    await db.commit()
    await db.refresh(player_lang)
    
    return player_lang
