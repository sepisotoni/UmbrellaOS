"""
services/ai/action_guard.py - The hard safety ceiling on what the AI layer
may do autonomously, enforced in code, not as a prompt instruction the
model could ignore.

This deliberately builds on Phase 0's Capability Registry rather than
maintaining a separate moderation-specific blocklist: every capability
already declares `destructive` and `reversible` (registry/spec.py) - flags
the AI orchestrator itself needs to decide Suggest vs. Autonomous mode.
This guard is the single place that reads those same flags and turns them
into an actual, unconditional block, so a new destructive capability added
in any future phase (a ban capability, a delete-world capability, whatever
comes next) is automatically covered without this file ever needing to
change - the same "declare once, every consumer benefits" property the
registry gives every other adapter.

No confidence score, no dual-review agreement, and no prompt-level
instruction can override this. If autonomous execution of a destructive,
irreversible action is ever truly wanted, that is a deliberate design
change to this file, reviewed as such - not a runtime toggle.
"""
from __future__ import annotations

from dataclasses import dataclass

from registry.registry import CapabilityNotFoundError, registry
from registry.spec import CapabilitySpec

# A hard ceiling on any duration-like parameter the AI might set, applied
# defensively regardless of which capability it's calling - e.g. a
# moderation timeout, a maintenance window. Expressed in seconds. This is
# intentionally generic rather than tied to a specific not-yet-built
# moderation capability, so it's already in force the moment one exists.
MAX_AI_SETTABLE_DURATION_SECONDS = 60 * 60  # 1 hour

_DURATION_LIKE_PARAM_NAMES = {"duration_seconds", "timeout_seconds", "grace_period_seconds", "expires_in_days"}


class ActionGuardViolation(Exception):
    """Raised when a proposed AI action would violate a hard safety
    invariant. Never caught and silently downgraded anywhere in the AI
    layer - a violation always aborts the action."""


@dataclass(frozen=True)
class GuardDecision:
    allowed_autonomously: bool
    reason: str


def evaluate(capability_name: str, params: dict, autonomous_mode: bool) -> GuardDecision:
    """
    Decide whether a proposed capability call may proceed autonomously.

    Always call this before invoking a capability from AI-initiated code.

    `registry/adapters/ai.py:call_tool()` is that call site - every
    AI-initiated capability invocation goes through it, and it calls
    `require_autonomous_allowed()` below before `registry.call()` ever
    runs. Nothing else should invoke a capability from AI-initiated code
    without going through that adapter.
    """
    try:
        spec: CapabilitySpec = registry.get(capability_name)
    except CapabilityNotFoundError:
        return GuardDecision(allowed_autonomously=False, reason=f"unknown capability {capability_name!r}")

    if spec.destructive and not spec.reversible:
        return GuardDecision(
            allowed_autonomously=False,
            reason=(
                f"{capability_name!r} is destructive and irreversible - the AI layer may propose this "
                "action for human confirmation, but may never execute it autonomously. This is a hard "
                "invariant, not a per-call configurable setting."
            ),
        )

    for param_name, value in params.items():
        if param_name in _DURATION_LIKE_PARAM_NAMES and isinstance(value, (int, float)):
            limit = MAX_AI_SETTABLE_DURATION_SECONDS
            # expires_in_days is in days, not seconds - normalize before comparing.
            effective_seconds = value * 86400 if param_name == "expires_in_days" else value
            if effective_seconds > limit:
                return GuardDecision(
                    allowed_autonomously=False,
                    reason=(
                        f"{param_name}={value} exceeds the AI layer's hard cap of {limit} seconds "
                        f"for {capability_name!r} - a human must set a longer duration explicitly."
                    ),
                )

    if not autonomous_mode:
        return GuardDecision(
            allowed_autonomously=False,
            reason="autonomous mode is not enabled for this task - proceeding as a human-reviewed suggestion",
        )

    return GuardDecision(allowed_autonomously=True, reason="passed all hard safety checks")


def require_autonomous_allowed(capability_name: str, params: dict, autonomous_mode: bool) -> None:
    """Raises ActionGuardViolation if the call may not proceed
    autonomously. Call this at the point AI-initiated code would
    otherwise directly invoke a capability without human confirmation -
    `registry/adapters/ai.py:call_tool()` is that point; see evaluate()
    above."""
    decision = evaluate(capability_name, params, autonomous_mode)
    if not decision.allowed_autonomously:
        raise ActionGuardViolation(decision.reason)
