"""
tests/test_translation.py — Translation API tests.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from models import PlayerLanguage, Setting
from datetime import datetime


@pytest.mark.asyncio
async def test_post_translation_language_sets_player_language(client: AsyncClient, db_session):
    """POST /translation/language sets player language preference."""
    response = await client.post(
        "/api/v1/translation/language",
        json={
            "player_uuid": "00000000-0000-0000-0000-000000000001",
            "language_code": "es",
            "language_name": "Spanish",
        },
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["player_uuid"] == "00000000-0000-0000-0000-000000000001"
    assert data["language_code"] == "es"
    assert data["language_name"] == "Spanish"
    assert data["auto_translate_incoming"] == True
    assert data["auto_translate_outgoing"] == False


@pytest.mark.asyncio
async def test_post_translation_language_updates_existing(client: AsyncClient, db_session):
    """POST /translation/language updates existing language preference."""
    # Create initial language preference
    async with db_session() as db:
        player_lang = PlayerLanguage(
            player_uuid="00000000-0000-0000-0000-000000000001",
            language_code="en",
            language_name="English",
            auto_translate_incoming=True,
            auto_translate_outgoing=False,
        )
        db.add(player_lang)
        await db.commit()
    
    # Update to Spanish with different settings
    response = await client.post(
        "/api/v1/translation/language",
        json={
            "player_uuid": "00000000-0000-0000-0000-000000000001",
            "language_code": "es",
            "language_name": "Spanish",
            "auto_translate_incoming": False,
            "auto_translate_outgoing": True,
        },
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["language_code"] == "es"
    assert data["auto_translate_incoming"] == False
    assert data["auto_translate_outgoing"] == True


@pytest.mark.asyncio
async def test_post_translation_language_unauthenticated_returns_401(client: AsyncClient):
    """POST /translation/language without auth returns 401."""
    response = await client.post(
        "/api/v1/translation/language",
        json={
            "player_uuid": "00000000-0000-0000-0000-000000000001",
            "language_code": "es",
            "language_name": "Spanish",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_translation_language_returns_preference(client: AsyncClient, db_session):
    """GET /translation/language/{uuid} returns player's language preference."""
    # Create language preference
    async with db_session() as db:
        player_lang = PlayerLanguage(
            player_uuid="00000000-0000-0000-0000-000000000001",
            language_code="fr",
            language_name="French",
            auto_translate_incoming=True,
            auto_translate_outgoing=False,
        )
        db.add(player_lang)
        await db.commit()
    
    response = await client.get(
        "/api/v1/translation/language/00000000-0000-0000-0000-000000000001",
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["player_uuid"] == "00000000-0000-0000-0000-000000000001"
    assert data["language_code"] == "fr"
    assert data["language_name"] == "French"


@pytest.mark.asyncio
async def test_get_translation_language_default_returns_english(client: AsyncClient, db_session):
    """GET /translation/language/{uuid} returns default English when not set."""
    response = await client.get(
        "/api/v1/translation/language/00000000-0000-0000-0000-000000000001",
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["language_code"] == "en"
    assert data["language_name"] == "English"
    assert data["auto_translate_incoming"] == True
    assert data["auto_translate_outgoing"] == False


@pytest.mark.asyncio
async def test_get_translation_language_unauthenticated_returns_401(client: AsyncClient):
    """GET /translation/language/{uuid} without auth returns 401."""
    response = await client.get(
        "/api/v1/translation/language/00000000-0000-0000-0000-000000000001",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_translation_translate_with_no_api_key_returns_original(
    client: AsyncClient, db_session
):
    """POST /translation/translate with no API key returns original text unchanged."""
    # Ensure no API key is set
    async with db_session() as db:
        existing = await db.scalar(
            select(Setting).where(Setting.key == "ai.anthropic_api_key")
        )
        if existing:
            await db.delete(existing)
            await db.commit()
    
    response = await client.post(
        "/api/v1/translation/translate",
        json={
            "text": "Hello world",
            "target_language": "es",
        },
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["original"] == "Hello world"
    assert data["translated"] == "Hello world"
    assert data["was_translated"] == False


@pytest.mark.asyncio
async def test_post_translation_translate_english_to_english_returns_original(
    client: AsyncClient, db_session
):
    """POST /translation/translate to English returns original text unchanged."""
    # Set API key
    async with db_session() as db:
        existing = await db.scalar(
            select(Setting).where(Setting.key == "ai.anthropic_api_key")
        )
        if existing:
            existing.value = "test-key"
        else:
            setting = Setting(
                key="ai.anthropic_api_key",
                value="test-key",
                category="ai",
                description="Test",
                sensitive=False,
                requires_restart=False,
            )
            db.add(setting)
        await db.commit()
    
    # Mock the translation service to avoid actual API call
    import services.translation_service
    original_translate = services.translation_service.translate_message
    
    async def mock_translate(text, target_language, db):
        if target_language == "en":
            return text, False
        return f"[{target_language.upper()}] {text}", True
    
    services.translation_service.translate_message = mock_translate
    
    try:
        response = await client.post(
            "/api/v1/translation/translate",
            json={
                "text": "Hello world",
                "target_language": "en",
            },
            headers={"X-Admin-Key": "test-secret-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["original"] == "Hello world"
        assert data["translated"] == "Hello world"
        assert data["was_translated"] == False
    finally:
        services.translation_service.translate_message = original_translate


@pytest.mark.asyncio
async def test_post_translation_translate_with_player_uuid(
    client: AsyncClient, db_session
):
    """POST /translation/translate with player_uuid works correctly."""
    # Set API key
    async with db_session() as db:
        existing = await db.scalar(
            select(Setting).where(Setting.key == "ai.anthropic_api_key")
        )
        if existing:
            existing.value = "test-key"
        else:
            setting = Setting(
                key="ai.anthropic_api_key",
                value="test-key",
                category="ai",
                description="Test",
                sensitive=False,
                requires_restart=False,
            )
            db.add(setting)
        await db.commit()
    
    # Test that it accepts player_uuid parameter (will return original since API key is fake)
    response = await client.post(
        "/api/v1/translation/translate",
        json={
            "text": "Hello world",
            "target_language": "es",
            "player_uuid": "00000000-0000-0000-0000-000000000001",
        },
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["original"] == "Hello world"
    # Since the API key is fake, it will return the original text
    assert data["translated"] == "Hello world"  # Will fail to translate and return original
    assert data["was_translated"] == False


@pytest.mark.asyncio
async def test_post_translation_translate_unauthenticated_returns_401(client: AsyncClient):
    """POST /translation/translate without auth returns 401."""
    response = await client.post(
        "/api/v1/translation/translate",
        json={
            "text": "Hello",
            "target_language": "es",
        },
    )
    assert response.status_code == 401
