"""
registry — The Capability Registry: UmbrellaOS's single business-logic call
path, shared by the REST API, the CLI, Discord, and (Phase 5) the AI Tool
Registry.

Public surface:
    capability        — decorator that declares and registers a capability
    CallContext        — identity/permissions of whoever is calling
    CapabilityRegistry  — the registry class (mostly for tests; production
                          code uses the shared `registry` instance below)
    registry            — the process-wide default CapabilityRegistry instance
"""
from registry.context import CallContext
from registry.decorator import capability
from registry.registry import (
    CapabilityAlreadyRegisteredError,
    CapabilityNotFoundError,
    CapabilityRegistry,
    registry,
)
from registry.spec import CapabilitySpec

__all__ = [
    "CallContext",
    "capability",
    "CapabilityAlreadyRegisteredError",
    "CapabilityNotFoundError",
    "CapabilityRegistry",
    "CapabilitySpec",
    "registry",
]
