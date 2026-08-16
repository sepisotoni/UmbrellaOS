"""
cli.py — UmbrellaOS CLI entry point.

    python cli.py platform system whoami
    python cli.py platform audit search --params '{"limit": 10}'
    python cli.py list

Imports `capabilities` first (registering every capability), then builds the
Typer app from whatever's registered — the CLI's command surface is always
exactly what's in the Capability Registry, never a hand-maintained subset.
"""
import capabilities  # noqa: F401 — import for registration side effect
from registry.adapters.cli import build_cli

app = build_cli()

if __name__ == "__main__":
    app()
