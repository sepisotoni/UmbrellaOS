import pyotp
import pytest

from models.user import User
from services.mfa_service import MFAError, MFAService


async def _make_user(db) -> User:
    user = User(discord_id="discord-mfa-test", username="mfa_test_user")
    db.add(user)
    await db.flush()
    return user


@pytest.mark.asyncio
async def test_begin_enrollment_generates_secret_without_enabling(db_session):
    async with db_session() as db:
        user = await _make_user(db)
        secret, uri = await MFAService.begin_enrollment(db, user)
        await db.commit()

        assert user.mfa_secret == secret
        assert user.mfa_enabled is False
        assert "UmbrellaOS" in uri
        assert "mfa_test_user" in uri


@pytest.mark.asyncio
async def test_confirm_enrollment_with_correct_code_enables_mfa(db_session):
    async with db_session() as db:
        user = await _make_user(db)
        secret, _ = await MFAService.begin_enrollment(db, user)
        await db.commit()

    async with db_session() as db:
        user = await db.get(User, user.id)
        code = pyotp.TOTP(secret).now()
        await MFAService.confirm_enrollment(db, user, code)
        await db.commit()
        assert user.mfa_enabled is True


@pytest.mark.asyncio
async def test_confirm_enrollment_with_wrong_code_fails_and_does_not_enable(db_session):
    async with db_session() as db:
        user = await _make_user(db)
        await MFAService.begin_enrollment(db, user)
        await db.commit()

    async with db_session() as db:
        user = await db.get(User, user.id)
        with pytest.raises(MFAError):
            await MFAService.confirm_enrollment(db, user, "000000")
        assert user.mfa_enabled is False


@pytest.mark.asyncio
async def test_confirm_enrollment_without_prior_begin_fails(db_session):
    async with db_session() as db:
        user = await _make_user(db)
        await db.commit()

    async with db_session() as db:
        user = await db.get(User, user.id)
        with pytest.raises(MFAError):
            await MFAService.confirm_enrollment(db, user, "123456")


@pytest.mark.asyncio
async def test_verify_code_after_enrollment(db_session):
    async with db_session() as db:
        user = await _make_user(db)
        secret, _ = await MFAService.begin_enrollment(db, user)
        code = pyotp.TOTP(secret).now()
        await MFAService.confirm_enrollment(db, user, code)
        await db.commit()

    async with db_session() as db:
        user = await db.get(User, user.id)
        fresh_code = pyotp.TOTP(secret).now()
        assert await MFAService.verify_code(user, fresh_code) is True
        assert await MFAService.verify_code(user, "000000") is False


@pytest.mark.asyncio
async def test_verify_code_returns_false_when_mfa_not_enabled(db_session):
    async with db_session() as db:
        user = await _make_user(db)
        await db.commit()
        assert await MFAService.verify_code(user, "123456") is False


@pytest.mark.asyncio
async def test_disable_clears_secret_and_flag(db_session):
    async with db_session() as db:
        user = await _make_user(db)
        secret, _ = await MFAService.begin_enrollment(db, user)
        code = pyotp.TOTP(secret).now()
        await MFAService.confirm_enrollment(db, user, code)
        await db.commit()

    async with db_session() as db:
        user = await db.get(User, user.id)
        await MFAService.disable(db, user)
        await db.commit()
        assert user.mfa_enabled is False
        assert user.mfa_secret is None
