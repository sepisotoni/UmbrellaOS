"""
registry/decorator.py — `@capability`: how a domain exposes one unit of
business logic to every adapter at once.

Usage:

    class RestartServerParams(BaseModel):
        server_id: str

        def audit_target(self) -> str:
            return self.server_id

    @capability(
        name="hosting.server.restart",
        summary="Restart a server, optionally with a different startup flag set.",
        params_model=RestartServerParams,
        required_permission="server.control",
        destructive=True,
        reversible=False,
    )
    async def restart_server(ctx: CallContext, params: RestartServerParams) -> ServerState:
        ...

That single declaration is what the REST adapter lists at
`GET /api/v1/capabilities`, what the CLI adapter turns into
`umbrella hosting server restart`, what gets an audit row automatically, and
(Phase 5) what becomes an AI tool — with no separate registration step for
any of those.
"""
from __future__ import annotations

from typing import Awaitable, Callable, Type, TypeVar

from pydantic import BaseModel

from registry.registry import registry as default_registry
from registry.spec import CapabilitySpec

Handler = TypeVar("Handler", bound=Callable[..., Awaitable[object]])


def capability(
    *,
    name: str,
    summary: str,
    params_model: Type[BaseModel],
    result_model: Type[BaseModel] | None = None,
    required_permission: str | None = None,
    destructive: bool = False,
    reversible: bool = True,
    audited: bool = True,
    audit_category: str = "platform",
) -> Callable[[Handler], Handler]:
    """
    Decorate an `async def handler(ctx: CallContext, params: params_model)`
    function, registering it into the process-wide CapabilityRegistry.

    Registration happens at import time (module-level decoration), which is
    why every capability module must be imported somewhere during app
    startup — see `capabilities/__init__.py`, which mirrors the existing
    `models/__init__.py` pattern of importing every module for its
    side-effect.
    """

    def _wrap(fn: Handler) -> Handler:
        spec = CapabilitySpec(
            name=name,
            summary=summary,
            params_model=params_model,
            result_model=result_model,
            handler=fn,
            required_permission=required_permission,
            destructive=destructive,
            reversible=reversible,
            audited=audited,
            audit_category=audit_category,
        )
        default_registry.register(spec)
        # Attached for introspection/tests — lets a test import a handler
        # directly and assert on its declared spec without re-looking it up
        # by name in the registry.
        fn.capability_spec = spec  # type: ignore[attr-defined]
        return fn

    return _wrap
