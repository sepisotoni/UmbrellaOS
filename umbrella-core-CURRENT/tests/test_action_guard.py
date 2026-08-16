"""
tests/test_action_guard.py - Tests for services/ai/action_guard.py, using
real registered capabilities (not fakes) to prove the guard actually reads
their destructive/reversible flags and enforces against them.
"""
import pytest

import capabilities  # noqa: F401 - registers real capabilities this file tests against
from services.ai.action_guard import (
    ActionGuardViolation,
    evaluate,
    require_autonomous_allowed,
)


def test_destructive_irreversible_capability_is_never_autonomous():
    # hosting.server.delete: destructive=True, reversible=False (see capabilities/hosting.py)
    decision = evaluate("hosting.server.delete", {"server_id": "x"}, autonomous_mode=True)
    assert decision.allowed_autonomously is False
    assert "irreversible" in decision.reason


def test_destructive_irreversible_capability_blocked_even_with_autonomous_mode_true():
    # The mode flag alone must never override the destructive+irreversible check.
    with pytest.raises(ActionGuardViolation, match="irreversible"):
        require_autonomous_allowed("identity.apikey.revoke", {"api_key_id": "x"}, autonomous_mode=True)


def test_safe_readonly_capability_is_allowed_autonomously_when_mode_enabled():
    decision = evaluate("platform.system.whoami", {}, autonomous_mode=True)
    assert decision.allowed_autonomously is True


def test_safe_capability_still_blocked_when_autonomous_mode_disabled():
    decision = evaluate("platform.system.whoami", {}, autonomous_mode=False)
    assert decision.allowed_autonomously is False
    assert "not enabled" in decision.reason


def test_unknown_capability_is_never_allowed():
    decision = evaluate("does.not.exist", {}, autonomous_mode=True)
    assert decision.allowed_autonomously is False
    assert "unknown capability" in decision.reason


def test_duration_param_over_hard_cap_is_blocked():
    # hosting.server.stop has grace_period_seconds — reversible, non-destructive,
    # so it would otherwise pass; this proves the duration cap applies
    # independently of the destructive/reversible check.
    decision = evaluate(
        "hosting.server.stop",
        {"server_id": "x", "grace_period_seconds": 999_999},
        autonomous_mode=True,
    )
    assert decision.allowed_autonomously is False
    assert "exceeds the AI layer's hard cap" in decision.reason


def test_duration_param_within_cap_is_allowed():
    decision = evaluate(
        "hosting.server.stop",
        {"server_id": "x", "grace_period_seconds": 30},
        autonomous_mode=True,
    )
    assert decision.allowed_autonomously is True


def test_expires_in_days_is_normalized_to_seconds_before_comparison():
    # 1 day (86400s) is well over the 1-hour cap — this is really testing
    # that the day->seconds multiplication actually happens, since a bug
    # here would silently under- or over-count and either wrongly block or
    # wrongly allow.
    decision = evaluate(
        "identity.apikey.create",
        {"name": "x", "permissions": [], "expires_in_days": 1},
        autonomous_mode=True,
    )
    assert decision.allowed_autonomously is False  # 1 day = 86400s, over the 3600s cap
    assert "exceeds the AI layer's hard cap" in decision.reason


def test_require_autonomous_allowed_does_not_raise_for_a_valid_action():
    require_autonomous_allowed("platform.system.whoami", {}, autonomous_mode=True)  # must not raise
