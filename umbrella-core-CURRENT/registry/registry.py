"""
registry/registry.py — CapabilityRegistry: the single call path every
adapter (REST, CLI, Discord, AI) uses to invoke UmbrellaOS business logic.

Architectural invariant, enforced here rather than documented as convention:
`CapabilityRegistry.call()` is the *only* way a capability's handler is ever
invoked. Adapters register capabilities (via the `@capability` decorator at
import time) and invoke them (via `call()`) — they never import and call a
handler function directly. That's what makes it structurally true, not just
convention, that:

    - RBAC is enforced (one check, here, before every handler invocation)
    - audit logging happens (one write, here, after every handler invocation)
    - parameter validation happens (one validation, here, before the handler
      ever sees untrusted input)

regardless of which of REST/CLI/Discord/AI initiated the call.
"""
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ValidationError

from api.middleware.errors import (
    PermissionDeniedException,
    ResourceNotFoundException,
    ValidationException,
)
from registry.audit import record_audit_event
from registry.context import CallContext
from registry.spec import CapabilitySpec

logger = logging.getLogger(__name__)


def _resolve_audit_target(params: BaseModel) -> str | None:
    """
    A params model may optionally expose an `audit_target()` method
    returning the identifier of whatever it acted on (a server ID, a player
    ID). This is opt-in per params model — most capabilities have no single
    natural "target" and simply return None, which is a valid AuditLog.target.
    """
    target_fn = getattr(params, "audit_target", None)
    return target_fn() if callable(target_fn) else None


class CapabilityNotFoundError(ResourceNotFoundException):
    """
    Raised when `get()`/`call()` is given a name with no registered
    capability. Subclasses the existing `ResourceNotFoundException` (rather
    than a plain LookupError) so it flows through the app's existing global
    error handler and becomes a proper 404 `ErrorResponse` for REST callers,
    with no capability-specific exception handler needed.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(resource="Capability", identifier=name)


class CapabilityAlreadyRegisteredError(ValueError):
    """
    Raised at import/registration time (not at call time) when two
    `@capability` declarations share a name. This is a programming error to
    catch during development/CI, not a runtime condition an adapter needs to
    handle — capability registration happens once, at process startup.
    """


class CapabilityRegistry:
    def __init__(self) -> None:
        self._capabilities: dict[str, CapabilitySpec] = {}

    def register(self, spec: CapabilitySpec) -> None:
        if spec.name in self._capabilities:
            raise CapabilityAlreadyRegisteredError(
                f"Capability '{spec.name}' is already registered. Capability "
                "names must be globally unique across every domain — this is "
                "almost always a copy-pasted @capability(name=...) value."
            )
        self._capabilities[spec.name] = spec
        logger.debug("Registered capability: %s", spec.name)

    def unregister(self, name: str) -> None:
        """
        Removes a previously-registered capability. Added for the
        marketplace install flow (Phase 7 item 3): uninstalling a plugin,
        or installing a new version of an already-installed one, must be
        able to cleanly remove exactly the capability names that plugin's
        previous registration added, so re-registering the same or a
        different version's capability set doesn't collide with
        `CapabilityAlreadyRegisteredError`. Every other capability in this
        codebase is registered once at import time and never removed —
        this method exists for the plugin lifecycle specifically, not as
        a general-purpose escape hatch other domains should reach for.

        Raises CapabilityNotFoundError if `name` isn't registered, same as
        `get()` — removing something that was never there is treated as a
        caller bug, not a silent no-op.
        """
        if name not in self._capabilities:
            raise CapabilityNotFoundError(name)
        del self._capabilities[name]
        logger.debug("Unregistered capability: %s", name)

    def get(self, name: str) -> CapabilitySpec:
        try:
            return self._capabilities[name]
        except KeyError:
            raise CapabilityNotFoundError(name) from None

    def list(self) -> list[CapabilitySpec]:
        """Every registered capability, sorted by name. What REST's
        `GET /capabilities`, the CLI's command-tree builder, and (Phase 5)
        the AI Tool Registry all introspect."""
        return sorted(self._capabilities.values(), key=lambda s: s.name)

    async def call(
        self,
        name: str,
        ctx: CallContext,
        raw_params: dict[str, Any] | BaseModel,
    ) -> Any:
        """
        Validate, authorize, invoke, and audit a single capability call.

        Raises:
            CapabilityNotFoundError: `name` isn't registered.
            PermissionDeniedException: `ctx` lacks the required permission.
            ValidationException: `raw_params` doesn't satisfy the
                capability's declared params_model.
            Exception: whatever the handler itself raises, after recording
                a failed-outcome audit row (if `spec.audited`).
        """
        spec = self.get(name)

        # 1. Authorization — enforced here, once, before the handler ever runs.
        if not ctx.has_permission(spec.required_permission):
            raise PermissionDeniedException(
                f"Missing permission: {spec.required_permission}",
                details={"capability": name},
            )

        # 2. Parameter validation against the capability's declared schema.
        #    Adapters pass either a raw dict (REST body, CLI --params JSON)
        #    or an already-validated model instance (internal callers).
        if isinstance(raw_params, spec.params_model):
            params = raw_params
        else:
            try:
                params = spec.params_model.model_validate(raw_params)
            except ValidationError as exc:
                # FIX: exc.errors() defaults to including the raw exception
                # object in each error's ctx["error"] when a custom
                # field_validator raises a plain ValueError/AssertionError.
                # That raw exception isn't JSON-serializable, so any capability
                # with such a validator (api/validators.py::validate_player_uuid
                # is the first, but not necessarily the last) would crash
                # api/middleware/errors.py's handler with
                # "PydanticSerializationError: Unable to serialize unknown
                # type" instead of returning the intended 422 — turning a
                # normal validation failure into a 500. include_context=False
                # drops the ctx key entirely; the human-readable msg is
                # already in each error dict without it.
                raise ValidationException(
                    f"Invalid parameters for capability '{name}'",
                    details=exc.errors(include_context=False),
                ) from exc

        # 3. Invoke. This is the only line in the entire codebase that should
        #    ever call `spec.handler` directly.
        try:
            result = await spec.handler(ctx, params)
        except Exception:
            if spec.audited:
                await record_audit_event(
                    db=ctx.db,
                    actor=ctx.actor_id,
                    actor_type=ctx.actor_type,
                    action=name,
                    target=_resolve_audit_target(params),
                    details={
                        "source": ctx.source,
                        "request_id": ctx.request_id,
                        "params": params.model_dump(mode="json"),
                        "outcome": "error",
                    },
                    category=spec.audit_category,
                )
            raise

        # 4. Audit the successful call. Automatic — a new capability gets
        #    this for free rather than a developer remembering to add it.
        if spec.audited:
            await record_audit_event(
                db=ctx.db,
                actor=ctx.actor_id,
                actor_type=ctx.actor_type,
                action=name,
                target=_resolve_audit_target(params),
                details={
                    "source": ctx.source,
                    "request_id": ctx.request_id,
                    "params": params.model_dump(mode="json"),
                    "outcome": "success",
                },
                category=spec.audit_category,
            )

        return result


# Process-wide default registry. Every `@capability`-decorated function in
# `capabilities/*` registers into this instance at import time; every
# adapter (registry/adapters/*) calls against this same instance. Tests use
# their own throwaway CapabilityRegistry() instances rather than mutating
# this shared one — see tests/registry/conftest.py.
registry = CapabilityRegistry()
