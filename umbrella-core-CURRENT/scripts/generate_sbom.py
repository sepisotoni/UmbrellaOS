#!/usr/bin/env python3
"""
scripts/generate_sbom.py — Generates a CycloneDX SBOM (JSON) from
requirements.txt (Phase 9, item 6: dependency/CVE scanning).

Deliberately uses `cyclonedx-python-lib` directly rather than the
`cyclonedx-bom` CLI wrapper: only the library is in this sandbox's wheel
cache (no network to fetch the CLI package separately), and the library
alone is sufficient to read requirements.txt and emit valid CycloneDX
JSON — the CLI wrapper is a convenience layer this script re-implements
the small useful part of, not a capability gap.

Usage:
    python scripts/generate_sbom.py [--requirements requirements.txt] [--output sbom.json]

Exit code is always 0 on successful generation (SBOM generation is not
itself a pass/fail gate — pip-audit, in scan_dependencies.py, is the
gate). Intended to run in CI (see .github/workflows/dependency-scan.yml)
and to be runnable locally by an operator who wants a point-in-time SBOM.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.output.json import JsonV1Dot5
from cyclonedx.schema import OutputFormat

# Matches `name==version` lines from requirements.txt, ignoring comments,
# blank lines, and non-pinned/extras-bearing lines (e.g. `-r base.txt`,
# `pkg[extra]==1.0`) — extras are stripped rather than rejected, since a
# real requirements.txt in this codebase does use them.
_REQ_LINE_RE = re.compile(
    r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*==\s*([A-Za-z0-9._+!-]+)\s*(?:#.*)?$"
)


def parse_requirements(path: Path) -> list[tuple[str, str]]:
    packages: list[tuple[str, str]] = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        match = _REQ_LINE_RE.match(stripped)
        if match:
            packages.append((match.group(1), match.group(2)))
    return packages


def build_sbom(packages: list[tuple[str, str]]) -> Bom:
    bom = Bom()
    for name, version in packages:
        bom.components.add(
            Component(
                name=name,
                version=version,
                type=ComponentType.LIBRARY,
            )
        )
    return bom


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path, default=Path("requirements.txt"))
    parser.add_argument("--output", type=Path, default=Path("sbom.json"))
    args = parser.parse_args(argv)

    if not args.requirements.exists():
        print(f"error: {args.requirements} does not exist", file=sys.stderr)
        return 1

    packages = parse_requirements(args.requirements)
    if not packages:
        print(f"warning: no pinned packages found in {args.requirements}", file=sys.stderr)

    bom = build_sbom(packages)
    output = JsonV1Dot5(bom)
    args.output.write_text(output.output_as_string(indent=2))
    print(f"wrote SBOM for {len(packages)} package(s) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
