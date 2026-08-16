#!/usr/bin/env python3
"""
scripts/export_openapi_schema.py — Dumps `main.app.openapi()` to a JSON
file (Phase 7 completion, Task A). This is the schema `umbrella-sdk-ts/`
is generated from.

Deliberately imports `main.app` directly rather than hitting a running
server's `/openapi.json`: `app.openapi()` is a pure function of the
already-mounted routers (see main.py's module-level `app.include_router`
calls) and FastAPI caches/builds it the same way whether it's called here
or by a live request — no uvicorn process, no DB, no Redis needed to
produce the schema. `/openapi.json` itself stays reachable in production
too (only `docs_url`/`redoc_url` are gated on `settings.debug` in
main.py's `FastAPI(...)` construction) — this script is a convenience for
CI/local generation, not the only way to get the schema.

Usage:
    python scripts/export_openapi_schema.py [--output openapi.json]

Exit code is 0 on successful export, 1 if `main.app.openapi()` raises.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Repo root (parent of scripts/) needs to be on sys.path so `import main`
# resolves regardless of the caller's cwd — matches how `uvicorn main:app`
# is normally invoked from the repo root, but this script is meant to be
# runnable as `python scripts/export_openapi_schema.py` from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("openapi.json"),
        help="Path to write the schema JSON to (default: openapi.json, relative to cwd).",
    )
    args = parser.parse_args()

    # Local import, after arg parsing: importing `main` runs every
    # `from api.routers.X import router` at module scope (that's how the
    # routers get mounted), which in turn imports `config.get_settings()`
    # at module scope — so a --help invocation doesn't pay that cost or
    # require a configured environment just to print usage.
    import main as app_module

    try:
        schema = app_module.app.openapi()
    except Exception as exc:  # pragma: no cover - defensive, see docstring
        print(f"Failed to build OpenAPI schema: {exc!r}", file=sys.stderr)
        return 1

    args.output.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    print(f"Wrote OpenAPI schema ({len(schema.get('paths', {}))} paths) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
