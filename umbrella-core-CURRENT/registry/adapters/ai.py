"""
registry/adapters/ai.py — AI Tool Registry: the third adapter over the
Capability Registry, alongside REST (registry/adapters/rest.py) and CLI
(registry/adapters/cli.py).

This is the piece `services/ai/action_guard.py` and `services/ai/orchestrator.py`
have carried a TODO for since Phase 5's foundational slice: the point where
an AI-initiated call actually reaches a capability. Nothing before this file
existed let the AI layer invoke anything — orchestrator.run() only
generated and dual-reviewed text.

Two invariants this file exists to make structurally true, not just
documented convention:

1. An AI-initiated call can never exceed the permissions of the human it's
   acting for. `call_tool()` builds its CallContext via the exact same
   `CallContext.from_web_auth()` every other adapter uses, with the *acting*
   user's own identity — there is no separate elevated "AI identity" and no
   code path that grants one. This is registry/context.py's own stated
   design invariant for the "ai" source, made real here.

2. A destructive+irreversible capability can never be executed
   autonomously, regardless of confidence, agreement, or prompt content.
   `call_tool()` runs every call through `action_guard.require_autonomous_allowed()`
   before `registry.call()` ever sees it - closing the TODO left in both
   `action_guard.py` and `orchestrator.py`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.errors import ValidationException
from models import User
from models.api_key import ApiKey
from registry.context import CallContext
from registry.registry import registry
from services.ai.action_guard import ActionGuardViolation, require_autonomous_allowed


@dataclass(frozen=True)
class ToolDefinition:
    """One capability, shaped for an LLM tool-use/function-calling schema
    (matches Anthropic's `tools` parameter shape - `name`/`description`/
    `input_schema` - since that's the primary provider today; the shape is
    generic JSON Schema underneath, so adapting it for OpenRouter or Gemini's
    slightly different tool-schema envelopes is a formatting step at the
    call site, not a reason to duplicate this list per provider)."""

    name: str
    description: str
    input_schema: dict[str, Any]
    destructive: bool
    reversible: bool


class ToolCallDenied(Exception):
    """Raised when action_guard blocks a call before it ever reaches the
    registry. Distinct from ActionGuardViolation (which this wraps) so
    callers building an AI-facing error message can catch one exception
    type for every reason a tool call didn't happen, rather than needing
    to know action_guard's exception type specifically."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def list_tools(ctx_permissions: set[str] | None = None, *, is_superuser: bool = False) -> list[ToolDefinition]:
    """
    Every registered capability, as a tool definition. If `ctx_permissions`
    is given (and `is_superuser` is False), the list is filtered to only
    what that permission set can actually call - an AI acting on behalf of
    a low-permission user should never be *offered* a tool it would then
    get a 403 trying to use; the model shouldn't have to learn that by
    trial and error, and a smaller, honest tool list is also a smaller
    surface for it to reason about.
    """
    tools = []
    for spec in registry.list():
        if not is_superuser and ctx_permissions is not None:
            if spec.required_permission is not None and spec.required_permission not in ctx_permissions:
                continue
        tools.append(
            ToolDefinition(
                name=spec.name,
                description=spec.summary,
                input_schema=spec.params_model.model_json_schema(),
                destructive=spec.destructive,
                reversible=spec.reversible,
            )
        )
    return tools


async def call_tool(
    name: str,
    raw_params: dict[str, Any],
    *,
    acting_on_behalf_of: User | str | ApiKey,
    db: AsyncSession,
    autonomous_mode: bool,
) -> Any:
    """
    The single entry point for the AI layer to invoke a capability.

    Order of operations, deliberate:
    1. Resolve the capability spec and validate params against it - the
       same validation registry.call() would do, done here first because
       action_guard needs correctly-typed params (an int duration, not a
       string that merely looks like one) to enforce its duration cap
       correctly.
    2. action_guard.require_autonomous_allowed() - the hard safety ceiling.
       Runs before registry.call() ever sees this, not as a check inside
       a capability handler that a future handler could forget to add.
    3. registry.call() - identical path REST/CLI/Discord already use, with
       a CallContext built from *acting_on_behalf_of*'s own identity, never
       a separate elevated one.

    Raises:
        CapabilityNotFoundError: `name` isn't registered.
        ValidationException: `raw_params` doesn't satisfy the capability's
            declared params_model.
        ToolCallDenied: action_guard blocked this call (destructive+
            irreversible, a duration cap exceeded, or autonomous_mode is
            off for what would otherwise be an autonomous action).
        PermissionDeniedException: `acting_on_behalf_of` lacks the
            required permission - raised by registry.call() itself, same
            as any other adapter.
    """
    spec = registry.get(name)

    try:
        params = spec.params_model.model_validate(raw_params)
    except ValidationError as exc:
        # FIX: see registry/registry.py's identical fix for the full
        # rationale — exc.errors() defaults to embedding the raw exception
        # object in ctx["error"] for ValueError-raising custom validators,
        # which isn't JSON-serializable and would crash the error handler
        # (500) instead of returning the intended 422.
        raise ValidationException(
            f"Invalid parameters for capability '{name}'",
            details=exc.errors(include_context=False),
        ) from exc

    try:
        require_autonomous_allowed(name, params.model_dump(mode="json"), autonomous_mode)
    except ActionGuardViolation as exc:
        raise ToolCallDenied(str(exc)) from exc

    ctx = await CallContext.from_web_auth(acting_on_behalf_of, db, source="ai")
    result = await registry.call(name, ctx, params)
    return result.model_dump(mode="json") if isinstance(result, BaseModel) else result
