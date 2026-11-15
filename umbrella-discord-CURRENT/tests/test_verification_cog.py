"""Tests for code detection and Core-to-Discord verification relaying."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.verification_cog import VerificationCog
from bot.services.umbrella_core_client import UmbrellaCoreError


def _make_message(content="123456"):
    message = MagicMock()
    message.guild = None
    message.author = MagicMock(id=42, bot=False)
    message.content = content
    message.channel.send = AsyncMock()
    return message


def _make_cog(result=None, error=None):
    mock_bot = MagicMock()
    mock_bot.guild_configs = {}
    mock_bot.core.invoke = AsyncMock(return_value=result)
    if error is not None:
        mock_bot.core.invoke.side_effect = error
    cog = VerificationCog.__new__(VerificationCog)
    cog.bot = mock_bot
    cog._sync_nickname = AsyncMock()
    cog._assign_verified_role = AsyncMock()
    return cog


def test_looks_like_code_accepts_six_digits():
    assert VerificationCog._looks_like_code("123456") is True


def test_looks_like_code_rejects_wrong_length():
    assert VerificationCog._looks_like_code("12345") is False
    assert VerificationCog._looks_like_code("1234567") is False


def test_looks_like_code_rejects_non_digits():
    assert VerificationCog._looks_like_code("12345a") is False
    assert VerificationCog._looks_like_code("abcdef") is False


def test_looks_like_code_rejects_empty_and_whitespace():
    assert VerificationCog._looks_like_code("") is False
    assert VerificationCog._looks_like_code("      ") is False


def test_looks_like_code_rejects_code_with_surrounding_text():
    # on_message already strips whitespace before calling this, but the
    # pure function itself should still reject "my code is 123456" etc.
    assert VerificationCog._looks_like_code("code: 123456") is False


@pytest.mark.asyncio
async def test_message_listener_relays_core_text_and_keeps_discord_actions():
    message = _make_message()
    cog = _make_cog(
        result={
            "player_username": "Steve",
            "discord_message": "Verified by Core.",
        }
    )

    await cog.on_message(message)

    cog.bot.core.invoke.assert_awaited_once()
    message.channel.send.assert_awaited_once_with("Verified by Core.")
    cog._sync_nickname.assert_awaited_once_with(message.author, "Steve")
    cog._assign_verified_role.assert_awaited_once_with(message.author)


@pytest.mark.asyncio
async def test_message_listener_relays_core_validation_message():
    message = _make_message()
    cog = _make_cog(
        error=UmbrellaCoreError(
            "That code is no longer valid.",
            status_code=404,
            code="NOT_FOUND",
        )
    )

    await cog.on_message(message)

    message.channel.send.assert_awaited_once_with("That code is no longer valid.")
    cog._sync_nickname.assert_not_awaited()
    cog._assign_verified_role.assert_not_awaited()


@pytest.mark.asyncio
async def test_message_listener_silently_skips_when_core_disables_verification():
    message = _make_message()
    cog = _make_cog(
        error=UmbrellaCoreError(
            "Verification is disabled.",
            status_code=409,
            code="VERIFICATION_DISABLED",
        )
    )

    await cog.on_message(message)

    message.channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_message_listener_does_not_send_non_code_messages_to_core():
    message = _make_message("my code is 123456")
    cog = _make_cog()

    await cog.on_message(message)

    cog.bot.core.invoke.assert_not_awaited()
    message.channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_verified_role_uses_each_guilds_own_role_mapping():
    members = [MagicMock(), MagicMock()]
    roles = [MagicMock(id=111), MagicMock(id=222)]
    guilds = [
        MagicMock(
            id=1,
            get_member=MagicMock(return_value=members[0]),
            get_role=MagicMock(return_value=roles[0]),
        ),
        MagicMock(
            id=2,
            get_member=MagicMock(return_value=members[1]),
            get_role=MagicMock(return_value=roles[1]),
        ),
    ]
    for member in members:
        member.add_roles = AsyncMock()

    cog = VerificationCog.__new__(VerificationCog)
    cog.bot = MagicMock(
        guilds=guilds,
        guild_configs={
            1: MagicMock(verified_role_id=111),
            2: MagicMock(verified_role_id=222),
        },
    )

    await cog._assign_verified_role(MagicMock(id=9))

    assert members[0].add_roles.await_args.args[0].id == 111
    assert members[1].add_roles.await_args.args[0].id == 222
