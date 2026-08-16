"""
tests/registry/test_cli_adapter.py — Tests for the Typer-based CLI adapter.

Uses Typer's CliRunner against a Typer app built from a throwaway
CapabilityRegistry (not the shared, process-wide one, so these tests aren't
coupled to exactly which capabilities other domains have registered) and
monkeypatches the adapter's DB session factory to point at the same
in-memory SQLite the rest of the suite uses.
"""
import json

import pytest
import pytest_asyncio
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from typer.testing import CliRunner

import registry.adapters.cli as cli_adapter
from database.engine import Base
from registry.registry import CapabilityRegistry
from registry.spec import CapabilitySpec
from services import RolesService

runner = CliRunner()


class GreetParams(BaseModel):
    name: str = "world"


class GreetResult(BaseModel):
    greeting: str


async def _greet_handler(ctx, params: GreetParams) -> GreetResult:
    return GreetResult(greeting=f"hello, {params.name}")


@pytest_asyncio.fixture
async def cli_test_registry(monkeypatch):
    """
    Build a throwaway registry with one simple capability, and point the CLI
    adapter's DB session factory at a fresh in-memory SQLite engine —
    mirroring tests/conftest.py's db_session fixture, but self-contained
    here since the CLI adapter constructs its own session directly (it has
    no FastAPI dependency-injection point to override).
    """
    test_registry = CapabilityRegistry()
    test_registry.register(
        CapabilitySpec(
            name="test.cli.greet",
            summary="Return a greeting.",
            params_model=GreetParams,
            handler=_greet_handler,
            required_permission=None,
            audited=False,
        )
    )

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as db:
        await RolesService.seed_defaults(db)

    monkeypatch.setattr(cli_adapter, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(cli_adapter, "registry", test_registry)

    yield test_registry

    await engine.dispose()


def test_build_cli_creates_nested_command_groups(cli_test_registry):
    app = cli_adapter.build_cli(cli_test_registry)
    result = runner.invoke(app, ["test", "cli", "greet", "--help"])
    assert result.exit_code == 0
    assert "Return a greeting" in result.output


def test_cli_invokes_capability_and_prints_json_result(cli_test_registry):
    app = cli_adapter.build_cli(cli_test_registry)
    result = runner.invoke(app, ["test", "cli", "greet", "--params", json.dumps({"name": "umbrella"})])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["greeting"] == "hello, umbrella"


def test_cli_uses_default_params_when_omitted(cli_test_registry):
    app = cli_adapter.build_cli(cli_test_registry)
    result = runner.invoke(app, ["test", "cli", "greet"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["greeting"] == "hello, world"


def test_cli_list_command_shows_registered_capabilities(cli_test_registry):
    app = cli_adapter.build_cli(cli_test_registry)
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "test.cli.greet" in result.output


def test_cli_surfaces_capability_errors_with_nonzero_exit(cli_test_registry, monkeypatch):
    async def _always_fails(ctx, params):
        raise RuntimeError("simulated failure")

    cli_test_registry.register(
        CapabilitySpec(
            name="test.cli.broken",
            summary="Always fails",
            params_model=GreetParams,
            handler=_always_fails,
            audited=False,
        )
    )
    app = cli_adapter.build_cli(cli_test_registry)
    result = runner.invoke(app, ["test", "cli", "broken"])
    assert result.exit_code == 1
    assert "simulated failure" in result.output
