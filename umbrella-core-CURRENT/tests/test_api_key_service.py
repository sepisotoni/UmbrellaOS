import pytest

from services.api_key_service import ApiKeyError, ApiKeyService


@pytest.mark.asyncio
async def test_create_api_key_returns_plaintext_once(db_session):
    async with db_session() as db:
        key, plaintext = await ApiKeyService.create_api_key(db, "bot-key", ["hosting.server.view"])
        await db.commit()
        assert plaintext.startswith("umbr_")
        assert key.key_prefix == plaintext[:12]
        assert key.key_hash != plaintext  # never store the plaintext itself


@pytest.mark.asyncio
async def test_create_api_key_rejects_wildcard_permission(db_session):
    async with db_session() as db:
        with pytest.raises(ApiKeyError):
            await ApiKeyService.create_api_key(db, "bad-key", ["*"])


@pytest.mark.asyncio
async def test_verify_api_key_round_trip(db_session):
    async with db_session() as db:
        _, plaintext = await ApiKeyService.create_api_key(db, "bot-key", ["hosting.server.view"])
        await db.commit()

    async with db_session() as db:
        verified = await ApiKeyService.verify_api_key(db, plaintext)
        await db.commit()
        assert verified.permissions == ["hosting.server.view"]
        assert verified.last_used_at is not None


@pytest.mark.asyncio
async def test_verify_rejects_unknown_key(db_session):
    async with db_session() as db:
        with pytest.raises(ApiKeyError):
            await ApiKeyService.verify_api_key(db, "umbr_not-a-real-key")


@pytest.mark.asyncio
async def test_verify_rejects_revoked_key(db_session):
    async with db_session() as db:
        key, plaintext = await ApiKeyService.create_api_key(db, "bot-key", ["hosting.server.view"])
        await db.commit()
        key_id = key.id

    async with db_session() as db:
        await ApiKeyService.revoke_api_key(db, key_id)
        await db.commit()

    async with db_session() as db:
        with pytest.raises(ApiKeyError):
            await ApiKeyService.verify_api_key(db, plaintext)


@pytest.mark.asyncio
async def test_verify_rejects_expired_key(db_session):
    async with db_session() as db:
        _, plaintext = await ApiKeyService.create_api_key(
            db, "bot-key", ["hosting.server.view"], expires_in_days=-1
        )
        await db.commit()

    async with db_session() as db:
        with pytest.raises(ApiKeyError):
            await ApiKeyService.verify_api_key(db, plaintext)


@pytest.mark.asyncio
async def test_revoke_unknown_key_raises_404(db_session):
    async with db_session() as db:
        with pytest.raises(ApiKeyError):
            await ApiKeyService.revoke_api_key(db, "00000000-0000-0000-0000-000000000000")


@pytest.mark.asyncio
async def test_list_api_keys(db_session):
    async with db_session() as db:
        await ApiKeyService.create_api_key(db, "key-a", [])
        await ApiKeyService.create_api_key(db, "key-b", [])
        await db.commit()

    async with db_session() as db:
        keys = await ApiKeyService.list_api_keys(db)
        names = {k.name for k in keys}
        assert {"key-a", "key-b"}.issubset(names)
