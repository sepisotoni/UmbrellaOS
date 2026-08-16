"""
registry/spec.py — CapabilitySpec: the declared metadata for one capability.

This is the object every adapter (REST, CLI, Discord, AI) reads to know how
to expose a capability, without any of them needing capability-specific code.
A new domain only ever produces one of these (via the `@capability` decorator
in registry/decorator.py) — everything downstream (routing, CLI command,
permission check, audit category) is derived from it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Type

from pydantic import BaseModel


@dataclass(frozen=True)
class CapabilitySpec:
    # Globally unique, dot-separated identifier, e.g. "platform.audit.search".
    # Segment structure is meaningful: it becomes the CLI's nested command
    # groups (`umbrella platform audit search`) and the natural grouping for
    # future AI-tool listings.
    name: str

    # Human-readable one-line description. Shown in `GET /capabilities`,
    # `umbrella --help`, and is what the AI Tool Registry (Phase 5) will use
    # as the tool description handed to a model.
    summary: str

    # Pydantic model describing this capability's input. Doubles as: the
    # REST request body schema, the CLI's `--params` JSON validation target,
    # and (Phase 5) the AI tool's parameter schema.
    params_model: Type[BaseModel]

    # The async function that implements the capability. Always called as
    # `handler(ctx: CallContext, params: params_model) -> Any` — and always
    # called *only* through CapabilityRegistry.call(), never directly.
    handler: Callable[..., Awaitable[Any]]

    # Optional result schema, for adapters that want to advertise a typed
    # response (e.g. generated SDK clients in a later phase). Not required —
    # plenty of capabilities return plain dicts.
    result_model: Type[BaseModel] | None = None

    # Permission key required to invoke this capability. None means "any
    # authenticated actor" (not "anyone unauthenticated" — authentication
    # itself is handled by the adapter before a CallContext ever exists).
    required_permission: str | None = None

    # Whether invoking this capability changes state in a way that isn't
    # simply re-derivable (a restart, a ban, a delete). Read by the AI
    # orchestrator (Phase 5) to decide whether Suggest-mode confirmation is
    # required before it may call this capability autonomously.
    destructive: bool = False

    # Whether the *effect* of this capability can be undone by some other
    # capability (e.g. a ban is reversible via unban; a restart is not
    # reversible — the previous process state is gone). Also read by the
    # Phase 5 AI orchestrator's reversibility contract.
    reversible: bool = True

    # Whether every invocation should produce an audit_log row. Defaults to
    # True — most capabilities are actions worth a durable record of. Purely
    # informational, read-only introspection capabilities (like whoami) may
    # opt out to avoid audit-log noise; that decision is made explicitly per
    # capability, not left to adapter discretion.
    audited: bool = True

    # Free-text grouping used only for audit-log categorization/search —
    # deliberately not part of the audit permission model itself.
    audit_category: str = "platform"

    def __post_init__(self) -> None:
        if not self.name or "." not in self.name:
            raise ValueError(
                f"Capability name {self.name!r} must be dot-separated "
                "(e.g. 'platform.system.whoami') so it can be grouped into "
                "CLI command trees and AI tool namespaces."
            )
