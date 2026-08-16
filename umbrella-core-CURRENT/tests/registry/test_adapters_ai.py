"""
tests/registry/test_adapters_ai.py — Tests for registry/adapters/ai.py, the
AI Tool Registry. In-process unit tests against call_tool()/list_tools()
directly (not through the REST client fixture) since this adapter has no
HTTP surface of its own - it's called in-process by the AI layer, the same
way the CLI adapter is invoked in-process by a terminal command.
"""
import pytest
from sqlalchemy import select

import capabilities  # noqa: F401 - registers every @capability with the registry
from api.middleware.errors import PermissionDeniedException, ValidationException
from models import Role, User
from registry.adapters.ai import ToolCallDenied, call_tool, list_tools
from tests.conftest import TEST_SECRET_KEY


async def _make_user(db_session, role_name: str, suffix: str = "") -> User:
    """A real User with a seeded role, for tests exercising the
    "AI acts on behalf of an actual staff member" path rather than the
    admin-key bootstrap tier."""
    async with db_session() as db:
        role = await db.scalar(select(Role).where(Role.name == role_name))
        user = User(discord_id=f"discord-ai-{role_name}{suffix}", username=f"user_{role_name}{suffix}", role_id=role.id)
        db.add(user)
        await db.flush()
        await db.commit()
        await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_call_tool_uses_the_acting_users_own_identity_not_an_elevated_one(db_session):
    """The exact invariant registry/context.py and capabilities/system.py's
    whoami handler both document: an AI-initiated call must reflect the
    identity of whoever it's acting for, never a separate elevated one."""
    user = await _make_user(db_session, "member")
    async with db_session() as db:
        result = await call_tool(
            "platform.system.whoami", {}, acting_on_behalf_of=user, db=db, autonomous_mode=True
        )
    assert result["actor_id"] == user.discord_id
    assert result["source"] == "ai"
    assert result["is_superuser"] is False


@pytest.mark.asyncio
async def test_call_tool_with_admin_key_string_gets_superuser_tier(db_session):
    """acting_on_behalf_of accepts the same admin-key string every other
    adapter's bootstrap tier does - no separate AI-only auth path."""
    async with db_session() as db:
        result = await call_tool(
            "platform.system.whoami", {}, acting_on_behalf_of=TEST_SECRET_KEY, db=db, autonomous_mode=True
        )
    assert result["is_superuser"] is True
    assert result["source"] == "ai"


@pytest.mark.asyncio
async def test_call_tool_blocks_destructive_irreversible_capability_even_with_autonomous_mode_on(db_session):
    """hosting.server.restart is destructive=True, reversible=False - the
    hard ceiling action_guard enforces. autonomous_mode=True must not be
    able to override it; this is the whole point of the guard."""
    async with db_session() as db:
        with pytest.raises(ToolCallDenied, match="destructive and irreversible"):
            await call_tool(
                "hosting.server.restart",
                {"server_id": "nonexistent"},
                acting_on_behalf_of=TEST_SECRET_KEY,
                db=db,
                autonomous_mode=True,
            )


@pytest.mark.asyncio
async def test_call_tool_denies_when_autonomous_mode_is_off_for_a_capability_that_would_otherwise_be_allowed(
    db_session,
):
    """A non-destructive capability is still denied autonomous execution
    if autonomous_mode itself is False - Suggest mode, not Autonomous mode."""
    async with db_session() as db:
        with pytest.raises(ToolCallDenied, match="autonomous mode is not enabled"):
            await call_tool(
                "platform.system.whoami", {}, acting_on_behalf_of=TEST_SECRET_KEY, db=db, autonomous_mode=False
            )
    # whoami has required_permission=None and destructive=False/reversible=True,
    # so the only reason this is denied is the explicit autonomous_mode gate -
    # confirming the guard's checks are independent of each other, not just
    # the destructive+irreversible one happening to also apply here.


@pytest.mark.asyncio
async def test_call_tool_raises_permission_denied_for_a_capability_beyond_the_acting_users_role(db_session):
    """A low-permission user's own permissions still govern what the AI can
    do on their behalf - registry.call()'s existing RBAC check, unchanged,
    just reached via this adapter instead of REST. Uses hosting.node.list
    (non-destructive, requires hosting.node.view) rather than a destructive
    capability - a destructive+irreversible one would be blocked by
    action_guard before ever reaching the RBAC check, which would test the
    wrong thing."""
    user = await _make_user(db_session, "member")
    async with db_session() as db:
        with pytest.raises(PermissionDeniedException):
            await call_tool(
                "hosting.node.list",
                {},
                acting_on_behalf_of=user,
                db=db,
                autonomous_mode=True,
            )


@pytest.mark.asyncio
async def test_call_tool_validates_params_before_action_guard_runs(db_session):
    """Malformed params raise ValidationException, the same as any other
    adapter - not a generic ToolCallDenied, and not an unhandled TypeError
    from action_guard trying to inspect params it can't trust the shape of."""
    async with db_session() as db:
        with pytest.raises(ValidationException):
            await call_tool(
                "hosting.server.restart",
                {"server_id": 12345},  # should be a string
                acting_on_behalf_of=TEST_SECRET_KEY,
                db=db,
                autonomous_mode=False,
            )


@pytest.mark.asyncio
async def test_list_tools_includes_known_capabilities_with_json_schema():
    tools = list_tools(is_superuser=True)
    names = {t.name for t in tools}
    assert "platform.system.whoami" in names
    assert "hosting.server.restart" in names

    whoami_tool = next(t for t in tools if t.name == "platform.system.whoami")
    assert whoami_tool.destructive is False
    assert isinstance(whoami_tool.input_schema, dict)
    assert "properties" in whoami_tool.input_schema

    restart_tool = next(t for t in tools if t.name == "hosting.server.restart")
    assert restart_tool.destructive is True
    assert restart_tool.reversible is False


@pytest.mark.asyncio
async def test_list_tools_filters_by_permission_when_not_superuser():
    """An AI acting on behalf of a low-permission user should not even be
    offered a tool it has no permission to call."""
    tools = list_tools(ctx_permissions=set(), is_superuser=False)
    names = {t.name for t in tools}
    # whoami requires no permission (required_permission=None) - always offered.
    assert "platform.system.whoami" in names
    # restart requires hosting.server.control - not in the empty permission set.
    assert "hosting.server.restart" not in names


@pytest.mark.asyncio
async def test_list_tools_includes_a_permitted_capability_for_a_scoped_permission_set():
    tools = list_tools(ctx_permissions={"hosting.server.control"}, is_superuser=False)
    names = {t.name for t in tools}
    assert "hosting.server.restart" in names
