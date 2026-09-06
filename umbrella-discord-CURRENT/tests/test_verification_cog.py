"""
tests/test_verification_cog.py — Tests for the pure-function pieces of
VerificationCog (_looks_like_code, _format_error, _format_success). See
test_investigation_cog.py's module docstring for why the actual on_message
listener isn't tested here (needs a live discord.Message/gateway
connection). _sync_nickname is also not tested here for the same reason -
it's inherently a live-guild operation (guild.get_member, member.edit),
not a pure function.
"""
import pytest
from unittest.mock import MagicMock

from bot.cogs.verification_cog import VerificationCog
from bot.services.umbrella_core_client import UmbrellaCoreError


def _make_cog():
    """Return a VerificationCog instance with a mocked bot — enough for pure-function tests."""
    mock_bot = MagicMock()
    mock_bot.remote.verified_role_id = None
    cog = VerificationCog.__new__(VerificationCog)
    cog.bot = mock_bot
    # _t falls back to returning the key so format_error uses its fallback strings
    cog._t = lambda key: ""
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


def test_format_error_permission_denied():
    exc = UmbrellaCoreError("Missing permission: verification.link.manage", status_code=403, code="PERMISSION_DENIED")
    message = _make_cog()._format_error(exc)
    assert "contact staff" in message


def test_format_error_not_found():
    exc = UmbrellaCoreError("Verification code not found: 000000", status_code=404, code="NOT_FOUND")
    message = _make_cog()._format_error(exc)
    assert "Verification failed" in message


def test_format_error_validation():
    exc = UmbrellaCoreError("Verification code has expired.", status_code=422, code="VALIDATION_ERROR")
    message = _make_cog()._format_error(exc)
    assert "Verification failed" in message


def test_format_error_conflict():
    exc = UmbrellaCoreError(
        "This Discord account is already linked to a different Minecraft account and cannot be relinked.",
        status_code=409, code="CONFLICT",
    )
    message = _make_cog()._format_error(exc)
    assert "Verification failed" in message


def test_format_error_generic():
    exc = UmbrellaCoreError("Could not reach umbrella-core: connection refused")
    message = _make_cog()._format_error(exc)
    assert "Verification failed" in message
    assert "connection refused" in message


def test_format_success_new_link():
    result = {"player_uuid": "uuid-1", "player_username": "Steve", "already_linked": False}
    message = VerificationCog._format_success(result)
    assert "Verified!" in message
    assert "Steve" in message


def test_format_success_already_linked():
    result = {"player_uuid": "uuid-1", "player_username": "Steve", "already_linked": True}
    message = VerificationCog._format_success(result)
    assert "already verified" in message
    assert "Steve" in message
