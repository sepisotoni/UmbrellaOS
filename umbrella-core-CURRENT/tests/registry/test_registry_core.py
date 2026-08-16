"""
tests/registry/test_registry_core.py — Unit tests for CapabilityRegistry
itself: registration, permission enforcement, parameter validation, and
audit emission on both success and failure paths.

Uses a throwaway CapabilityRegistry() instance (not the shared, process-wide
`registry`) so these tests don't interact with capabilities registered by
other domains, but a real in-memory-SQLite-backed CallContext.db, so audit
rows are genuinely written and queried back, not mocked.
"""
import pytest
import pytest_asyncio
from pydantic import BaseModel

from api.middleware.errors import PermissionDeniedException, ValidationException
from models.audit_log import AuditLog
from registry.context import CallContext
from registry.registry import (
    CapabilityAlreadyRegisteredError,
    CapabilityNotFoundError,
    CapabilityRegistry,
)
from sqlalchemy import select


class EchoParams(BaseModel):
    message: str

    def audit_target(self) -> str:
        return self.message


class EchoResult(BaseModel):
    echoed: str


async def _echo_handler(ctx: CallContext, params: EchoParams) -> EchoResult:
    return EchoResult(echoed=params.message)


async def _failing_handler(ctx: CallContext, params: EchoParams) -> EchoResult:
    raise RuntimeError("handler intentionally failed")


def _make_ctx(db, *, permissions: set[str] | None = None, is_superuser: bool = False) -> CallContext:
    return CallContext(
        actor_id="test-actor",
        actor_type="staff",
        source="system",
        permissions=permissions or set(),
        is_superuser=is_superuser,
        db=db,
    )


@pytest_asyncio.fixture
async def fresh_registry() -> CapabilityRegistry:
    return CapabilityRegistry()


@pytest.mark.asyncio
async def test_register_and_get(fresh_registry):
    from registry.spec import CapabilitySpec

    spec = CapabilitySpec(
        name="test.echo.basic",
        summary="Echo back a message.",
        params_model=EchoParams,
        handler=_echo_handler,
    )
    fresh_registry.register(spec)

    fetched = fresh_registry.get("test.echo.basic")
    assert fetched.name == "test.echo.basic"
    assert fetched.summary == "Echo back a message."


def test_duplicate_registration_rejected(fresh_registry):
    # Two distinct specs sharing a name must be rejected regardless of which
    # one registered first — this is the registry's own guarantee, exercised
    # directly rather than through the @capability decorator (which always
    # targets the shared, process-wide registry and would pollute it with a
    # test capability for the rest of the test session).
    from registry.spec import CapabilitySpec

    def _handler(ctx, params):
        ...

    spec_a = CapabilitySpec(
        name="test.dup.thing", summary="a", params_model=EchoParams, handler=_handler
    )
    spec_b = CapabilitySpec(
        name="test.dup.thing", summary="b", params_model=EchoParams, handler=_handler
    )
    fresh_registry.register(spec_a)
    with pytest.raises(CapabilityAlreadyRegisteredError):
        fresh_registry.register(spec_b)


def test_capability_name_must_be_namespaced():
    from registry.spec import CapabilitySpec

    async def _handler(ctx, params):
        ...

    with pytest.raises(ValueError):
        CapabilitySpec(name="notnamespaced", summary="x", params_model=EchoParams, handler=_handler)


@pytest.mark.asyncio
async def test_get_unknown_capability_raises_not_found(fresh_registry):
    with pytest.raises(CapabilityNotFoundError):
        fresh_registry.get("does.not.exist")


@pytest.mark.asyncio
async def test_call_unknown_capability_raises_not_found(fresh_registry, db_session):
    async with db_session() as db:
        ctx = _make_ctx(db, is_superuser=True)
        with pytest.raises(CapabilityNotFoundError):
            await fresh_registry.call("does.not.exist", ctx, {})


@pytest.mark.asyncio
async def test_successful_call_returns_result_and_records_audit(fresh_registry, db_session):
    from registry.spec import CapabilitySpec

    spec = CapabilitySpec(
        name="test.echo.audited",
        summary="Echo, audited",
        params_model=EchoParams,
        handler=_echo_handler,
        required_permission=None,
        audited=True,
        audit_category="test",
    )
    fresh_registry.register(spec)

    async with db_session() as db:
        ctx = _make_ctx(db, is_superuser=True)
        result = await fresh_registry.call("test.echo.audited", ctx, {"message": "hello"})
        assert isinstance(result, EchoResult)
        assert result.echoed == "hello"

        rows = (await db.execute(select(AuditLog).where(AuditLog.action == "test.echo.audited"))).scalars().all()
        assert len(rows) == 1
        assert rows[0].actor == "test-actor"
        assert rows[0].target == "hello"  # from EchoParams.audit_target()
        assert '"outcome": "success"' in rows[0].details_json


@pytest.mark.asyncio
async def test_call_without_required_permission_is_denied_and_not_audited_as_success(
    fresh_registry, db_session
):
    from registry.spec import CapabilitySpec

    spec = CapabilitySpec(
        name="test.echo.guarded",
        summary="Echo, requires a permission",
        params_model=EchoParams,
        handler=_echo_handler,
        required_permission="test.special_permission",
        audited=True,
    )
    fresh_registry.register(spec)

    async with db_session() as db:
        ctx = _make_ctx(db, permissions=set(), is_superuser=False)
        with pytest.raises(PermissionDeniedException):
            await fresh_registry.call("test.echo.guarded", ctx, {"message": "hello"})

        rows = (
            await db.execute(select(AuditLog).where(AuditLog.action == "test.echo.guarded"))
        ).scalars().all()
        # Permission is checked *before* the handler runs and before any
        # audit write — a denied call produces no audit row at all, since
        # nothing was actually attempted.
        assert len(rows) == 0


@pytest.mark.asyncio
async def test_call_with_required_permission_present_succeeds(fresh_registry, db_session):
    from registry.spec import CapabilitySpec

    spec = CapabilitySpec(
        name="test.echo.guarded2",
        summary="Echo, requires a permission",
        params_model=EchoParams,
        handler=_echo_handler,
        required_permission="test.special_permission",
    )
    fresh_registry.register(spec)

    async with db_session() as db:
        ctx = _make_ctx(db, permissions={"test.special_permission"})
        result = await fresh_registry.call("test.echo.guarded2", ctx, {"message": "ok"})
        assert result.echoed == "ok"


@pytest.mark.asyncio
async def test_invalid_params_raise_validation_exception(fresh_registry, db_session):
    from registry.spec import CapabilitySpec

    spec = CapabilitySpec(
        name="test.echo.strict", summary="Echo", params_model=EchoParams, handler=_echo_handler
    )
    fresh_registry.register(spec)

    async with db_session() as db:
        ctx = _make_ctx(db, is_superuser=True)
        with pytest.raises(ValidationException):
            # Missing the required `message` field entirely.
            await fresh_registry.call("test.echo.strict", ctx, {})


@pytest.mark.asyncio
async def test_handler_exception_is_audited_as_error_then_reraised(fresh_registry, db_session):
    from registry.spec import CapabilitySpec

    spec = CapabilitySpec(
        name="test.echo.failing",
        summary="Always fails",
        params_model=EchoParams,
        handler=_failing_handler,
        audited=True,
    )
    fresh_registry.register(spec)

    async with db_session() as db:
        ctx = _make_ctx(db, is_superuser=True)
        with pytest.raises(RuntimeError, match="handler intentionally failed"):
            await fresh_registry.call("test.echo.failing", ctx, {"message": "boom"})

        rows = (
            await db.execute(select(AuditLog).where(AuditLog.action == "test.echo.failing"))
        ).scalars().all()
        assert len(rows) == 1
        assert '"outcome": "error"' in rows[0].details_json


@pytest.mark.asyncio
async def test_superuser_bypasses_any_required_permission(fresh_registry, db_session):
    from registry.spec import CapabilitySpec

    spec = CapabilitySpec(
        name="test.echo.superuser_only",
        summary="Requires a permission no context actually has",
        params_model=EchoParams,
        handler=_echo_handler,
        required_permission="something.nobody.has",
    )
    fresh_registry.register(spec)

    async with db_session() as db:
        ctx = _make_ctx(db, is_superuser=True)
        result = await fresh_registry.call("test.echo.superuser_only", ctx, {"message": "ok"})
        assert result.echoed == "ok"


def test_unregister_removes_capability(fresh_registry):
    from registry.spec import CapabilitySpec

    async def _h(ctx, params):
        ...

    fresh_registry.register(CapabilitySpec(name="test.remove.me", summary="x", params_model=EchoParams, handler=_h))
    fresh_registry.unregister("test.remove.me")
    with pytest.raises(CapabilityNotFoundError):
        fresh_registry.get("test.remove.me")


def test_unregister_unknown_capability_raises_not_found(fresh_registry):
    with pytest.raises(CapabilityNotFoundError):
        fresh_registry.unregister("does.not.exist")


def test_unregister_then_reregister_same_name_succeeds(fresh_registry):
    """The exact scenario the marketplace update flow depends on: a
    plugin's new version can re-declare the same capability name its old
    version used, once the old one has been unregistered."""
    from registry.spec import CapabilitySpec

    async def _h(ctx, params):
        ...

    spec_v1 = CapabilitySpec(name="plugin.demo.thing", summary="v1", params_model=EchoParams, handler=_h)
    fresh_registry.register(spec_v1)
    fresh_registry.unregister("plugin.demo.thing")

    spec_v2 = CapabilitySpec(name="plugin.demo.thing", summary="v2", params_model=EchoParams, handler=_h)
    fresh_registry.register(spec_v2)
    assert fresh_registry.get("plugin.demo.thing").summary == "v2"


def test_list_returns_sorted_specs(fresh_registry):
    from registry.spec import CapabilitySpec

    async def _h(ctx, params):
        ...

    fresh_registry.register(CapabilitySpec(name="zzz.last", summary="z", params_model=EchoParams, handler=_h))
    fresh_registry.register(CapabilitySpec(name="aaa.first", summary="a", params_model=EchoParams, handler=_h))
    names = [s.name for s in fresh_registry.list()]
    assert names == ["aaa.first", "zzz.last"]
