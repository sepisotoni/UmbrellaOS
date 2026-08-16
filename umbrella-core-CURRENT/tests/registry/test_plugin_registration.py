"""tests/registry/test_plugin_registration.py — plugin manifest -> real
CapabilityRegistry entries, exercised through CapabilityRegistry.call()
exactly the way a REST/CLI/AI adapter would, per the design doc's "no
shadow API" goal (a registered plugin capability must be indistinguishable
from a core one to CapabilityRegistry.call()).

Uses a fake in-memory SandboxExecutor — the real subprocess-based sandbox
is a separate module/doc; this file only needs to prove the registration
contract's wiring is correct, per SandboxExecutor's Protocol boundary.
"""
import pytest

from api.middleware.errors import PermissionDeniedException, ValidationException
from registry.context import CallContext
from registry.registry import CapabilityAlreadyRegisteredError, CapabilityRegistry
from services.plugins.manifest import parse_manifest
from services.plugins.registration import (
    PluginRegistrationError,
    register_plugin_capabilities,
)


class FakeSandbox:
    """Records every call it receives and returns a canned result (or
    raises a canned exception) per entrypoint — enough to prove the
    registration wrapper marshals params/actor_id correctly and that a
    sandbox failure flows through CapabilityRegistry.call()'s normal
    error/audit path."""

    def __init__(self):
        self.calls = []
        self.results: dict[str, dict] = {}
        self.raises: dict[str, Exception] = {}

    async def run(self, *, plugin_id, entrypoint, params, actor_id):
        self.calls.append({"plugin_id": plugin_id, "entrypoint": entrypoint, "params": params, "actor_id": actor_id})
        if entrypoint in self.raises:
            raise self.raises[entrypoint]
        return self.results.get(entrypoint, {})


def _queue_tools_manifest(**overrides) -> dict:
    raw = {
        "schema_version": 1,
        "plugin_id": "queue-tools",
        "name": "Queue Tools",
        "version": "1.0.0",
        "author": "example-author",
        "capabilities": [
            {
                "local_name": "queue_status",
                "summary": "Report current queue depth.",
                "entrypoint": "handlers:queue_status",
                "params": {"target_user_id": {"type": "string", "required": False}},
                "result": {"queue_depth": {"type": "integer"}},
                "required_permission": "players.view",
            }
        ],
    }
    raw.update(overrides)
    return raw


async def _admin_context(db_session) -> CallContext:
    async with db_session() as db:
        # is_superuser context — sidesteps needing to seed a real user/role
        # for tests only exercising the registration/call wiring itself,
        # matching CallContext.from_web_auth's own admin-key branch.
        return CallContext(
            actor_id="test-actor", actor_type="system", source="system",
            permissions=set(), is_superuser=True, db=db,
        )


@pytest.mark.asyncio
async def test_registers_capability_with_namespaced_name(db_session):
    registry = CapabilityRegistry()
    sandbox = FakeSandbox()
    manifest = parse_manifest(_queue_tools_manifest())
    async with db_session() as db:
        names = await register_plugin_capabilities(manifest, sandbox, db, registry=registry)
    assert names == ["plugin.queue-tools.queue_status"]
    assert registry.get("plugin.queue-tools.queue_status") is not None


@pytest.mark.asyncio
async def test_call_reaches_sandbox_and_validates_result(db_session):
    registry = CapabilityRegistry()
    sandbox = FakeSandbox()
    sandbox.results["handlers:queue_status"] = {"queue_depth": 7}
    manifest = parse_manifest(_queue_tools_manifest())
    async with db_session() as db:
        await register_plugin_capabilities(manifest, sandbox, db, registry=registry)
        ctx = await _admin_context(db_session)
        ctx.db = db
        result = await registry.call("plugin.queue-tools.queue_status", ctx, {"target_user_id": "u1"})

    assert result.queue_depth == 7
    assert sandbox.calls == [
        {
            "plugin_id": "queue-tools",
            "entrypoint": "handlers:queue_status",
            "params": {"target_user_id": "u1"},
            "actor_id": "test-actor",
        }
    ]


@pytest.mark.asyncio
async def test_sandbox_never_receives_db_or_permissions(db_session):
    """Direct assertion of the design doc's boundary rule: only plain,
    JSON-safe data (params dict, actor_id string) crosses into the
    sandbox call — never the live ctx.db session or ctx.permissions."""
    registry = CapabilityRegistry()
    sandbox = FakeSandbox()
    sandbox.results["handlers:queue_status"] = {"queue_depth": 0}
    manifest = parse_manifest(_queue_tools_manifest())
    async with db_session() as db:
        await register_plugin_capabilities(manifest, sandbox, db, registry=registry)
        ctx = await _admin_context(db_session)
        ctx.db = db
        await registry.call("plugin.queue-tools.queue_status", ctx, {})

    call = sandbox.calls[0]
    assert set(call.keys()) == {"plugin_id", "entrypoint", "params", "actor_id"}
    assert isinstance(call["actor_id"], str)
    assert isinstance(call["params"], dict)


@pytest.mark.asyncio
async def test_malformed_sandbox_result_raises(db_session):
    registry = CapabilityRegistry()
    sandbox = FakeSandbox()
    sandbox.results["handlers:queue_status"] = {"queue_depth": "not-an-int-and-not-coercible"}
    manifest = parse_manifest(_queue_tools_manifest())
    async with db_session() as db:
        await register_plugin_capabilities(manifest, sandbox, db, registry=registry)
        ctx = await _admin_context(db_session)
        ctx.db = db
        with pytest.raises(ValueError):
            await registry.call("plugin.queue-tools.queue_status", ctx, {})


@pytest.mark.asyncio
async def test_sandbox_exception_propagates_as_call_failure(db_session):
    registry = CapabilityRegistry()
    sandbox = FakeSandbox()
    sandbox.raises["handlers:queue_status"] = RuntimeError("plugin blew up")
    manifest = parse_manifest(_queue_tools_manifest())
    async with db_session() as db:
        await register_plugin_capabilities(manifest, sandbox, db, registry=registry)
        ctx = await _admin_context(db_session)
        ctx.db = db
        with pytest.raises(RuntimeError, match="plugin blew up"):
            await registry.call("plugin.queue-tools.queue_status", ctx, {})


@pytest.mark.asyncio
async def test_unknown_required_permission_rejects_registration(db_session):
    registry = CapabilityRegistry()
    sandbox = FakeSandbox()
    manifest = parse_manifest(_queue_tools_manifest(
        capabilities=[{
            "local_name": "queue_status",
            "summary": "x",
            "entrypoint": "handlers:queue_status",
            "required_permission": "totally_made_up_permission",
        }]
    ))
    async with db_session() as db:
        with pytest.raises(PluginRegistrationError):
            await register_plugin_capabilities(manifest, sandbox, db, registry=registry)
    # Nothing should have been registered — all-or-nothing per capability.
    with pytest.raises(Exception):
        registry.get("plugin.queue-tools.queue_status")


@pytest.mark.asyncio
async def test_registration_enforces_permission_check(db_session):
    """A caller without the declared required_permission is rejected the
    same way any core capability rejects it — no plugin-specific
    permission-check code path exists."""
    registry = CapabilityRegistry()
    sandbox = FakeSandbox()
    sandbox.results["handlers:queue_status"] = {"queue_depth": 1}
    manifest = parse_manifest(_queue_tools_manifest())
    async with db_session() as db:
        await register_plugin_capabilities(manifest, sandbox, db, registry=registry)
        ctx = CallContext(
            actor_id="low-priv", actor_type="staff", source="rest",
            permissions=set(), is_superuser=False, db=db,
        )
        with pytest.raises(PermissionDeniedException):
            await registry.call("plugin.queue-tools.queue_status", ctx, {})
    assert sandbox.calls == []  # handler must not run if permission check fails


@pytest.mark.asyncio
async def test_registration_enforces_params_validation(db_session):
    registry = CapabilityRegistry()
    sandbox = FakeSandbox()
    manifest = parse_manifest(_queue_tools_manifest())
    async with db_session() as db:
        await register_plugin_capabilities(manifest, sandbox, db, registry=registry)
        ctx = await _admin_context(db_session)
        ctx.db = db
        with pytest.raises(ValidationException):
            # target_user_id is declared type "string"; an int should fail validation.
            await registry.call("plugin.queue-tools.queue_status", ctx, {"target_user_id": {"nested": "dict"}})
    assert sandbox.calls == []


@pytest.mark.asyncio
async def test_duplicate_registration_raises_like_core_capabilities(db_session):
    registry = CapabilityRegistry()
    sandbox = FakeSandbox()
    manifest = parse_manifest(_queue_tools_manifest())
    async with db_session() as db:
        await register_plugin_capabilities(manifest, sandbox, db, registry=registry)
        with pytest.raises(CapabilityAlreadyRegisteredError):
            await register_plugin_capabilities(manifest, sandbox, db, registry=registry)


@pytest.mark.asyncio
async def test_two_plugins_cannot_collide_even_with_same_local_name(db_session):
    registry = CapabilityRegistry()
    sandbox = FakeSandbox()
    manifest_a = parse_manifest(_queue_tools_manifest(plugin_id="plugin-a"))
    manifest_b = parse_manifest(_queue_tools_manifest(plugin_id="plugin-b"))
    async with db_session() as db:
        names_a = await register_plugin_capabilities(manifest_a, sandbox, db, registry=registry)
        names_b = await register_plugin_capabilities(manifest_b, sandbox, db, registry=registry)
    assert names_a == ["plugin.plugin-a.queue_status"]
    assert names_b == ["plugin.plugin-b.queue_status"]


@pytest.mark.asyncio
async def test_no_required_permission_means_any_authenticated_actor(db_session):
    """Mirrors CallContext.has_permission's documented meaning of
    required_permission=None — no plugin-specific carve-out."""
    registry = CapabilityRegistry()
    sandbox = FakeSandbox()
    sandbox.results["handlers:queue_status"] = {"queue_depth": 3}
    manifest = parse_manifest(_queue_tools_manifest(
        capabilities=[{
            "local_name": "queue_status",
            "summary": "x",
            "entrypoint": "handlers:queue_status",
            "result": {"queue_depth": {"type": "integer"}},
            "required_permission": None,
        }]
    ))
    async with db_session() as db:
        await register_plugin_capabilities(manifest, sandbox, db, registry=registry)
        ctx = CallContext(
            actor_id="any-user", actor_type="staff", source="rest",
            permissions=set(), is_superuser=False, db=db,
        )
        result = await registry.call("plugin.queue-tools.queue_status", ctx, {})
    assert result.queue_depth == 3
