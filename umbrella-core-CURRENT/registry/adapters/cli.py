"""
registry/adapters/cli.py — Typer-based CLI adapter over the Capability Registry.

Every capability's dot-separated name becomes a nested CLI command —
`platform.audit.search` -> `umbrella platform audit search` — generated from
the registry at startup, not hand-written per command. Adding a new
capability never requires touching this file.

Authentication: the CLI runs with the same admin-key bootstrap tier REST
uses for the plugin/dashboard bootstrap case (`settings.admin_key`). Phase 3
(Identity/RBAC/SSO) adds first-class CLI login (`umbrella auth login`)
producing a real session, at which point the CLI gains per-user identity
instead of always running as the superuser tier — deliberately not built
here, since Phase 0 has no session/login capability yet to build it against.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

import typer

from config import get_settings
from database import AsyncSessionLocal
from registry.context import CallContext
from registry.registry import CapabilityRegistry, registry
from registry.spec import CapabilitySpec

app = typer.Typer(
    name="umbrella",
    help="UmbrellaOS command-line interface — every command below calls the "
    "exact same capability the Dashboard and API use.",
    no_args_is_help=True,
)


def _get_or_create_group(
    groups: dict[str, typer.Typer], path: list[str]
) -> typer.Typer:
    """Walk (creating as needed) nested Typer sub-apps for a dot-separated
    capability name's group segments, e.g. ["platform", "audit"]."""
    current = app
    prefix = ""
    for segment in path:
        prefix = f"{prefix}.{segment}" if prefix else segment
        if prefix not in groups:
            sub_app = typer.Typer(help=f"'{prefix}' commands")
            groups[prefix] = sub_app
            current.add_typer(sub_app, name=segment)
        current = groups[prefix]
    return current


async def _invoke(spec: CapabilitySpec, params_json: str) -> Any:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        ctx = await CallContext.from_web_auth(settings.admin_key, db, source="cli")
        params: dict[str, Any] = json.loads(params_json) if params_json.strip() else {}
        result = await registry.call(spec.name, ctx, params)
        await db.commit()
        return result


def _make_command(spec: CapabilitySpec):
    def _command(
        params: str = typer.Option(
            "{}",
            "--params",
            "-p",
            help=f"JSON object matching this capability's schema. "
            f"Run 'umbrella capability schema {spec.name}' to see it.",
        ),
    ) -> None:
        try:
            result = asyncio.run(_invoke(spec, params))
        except Exception as exc:  # noqa: BLE001 - CLI boundary: surface any failure to the operator
            typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc

        if hasattr(result, "model_dump"):
            typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))
        else:
            typer.echo(json.dumps(result, indent=2, default=str))

    _command.__doc__ = spec.summary
    return _command


def build_cli(source_registry: CapabilityRegistry = registry) -> typer.Typer:
    """
    Populate the module-level Typer `app` with one command per currently
    registered capability. Called once at CLI startup (see `cli.py`), after
    `capabilities` has been imported so every capability is registered
    first.
    """
    groups: dict[str, typer.Typer] = {}
    for spec in source_registry.list():
        *group_path, leaf = spec.name.split(".")
        parent = _get_or_create_group(groups, group_path)
        parent.command(name=leaf, help=spec.summary)(_make_command(spec))

    @app.command(name="list")
    def list_capabilities() -> None:
        """List every registered capability (equivalent to GET /api/v1/capabilities)."""
        for spec in source_registry.list():
            flags = []
            if spec.destructive:
                flags.append("destructive")
            if not spec.reversible:
                flags.append("irreversible")
            suffix = f" [{', '.join(flags)}]" if flags else ""
            typer.echo(f"{spec.name}{suffix} — {spec.summary}")

    return app
