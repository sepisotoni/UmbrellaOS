#!/usr/bin/env python3
"""
scripts/scan_dependencies.py — pip-audit wrapper (Phase 9, item 6:
dependency/CVE scanning).

Honest limitation, stated plainly: pip-audit works by querying the OSV
(and optionally PyPI) vulnerability advisory database over the network.
This sandbox has no network access (see the Phase 9 verification
checkpoint), so this script could not be run end-to-end here — what was
verified locally is that `pip-audit` is installed, importable, and its
CLI is invocable (`pip-audit --help`); the actual scan needs to run
somewhere with network access, which is exactly what CI is for (see
.github/workflows/dependency-scan.yml, which runs this on a schedule and
on every dependency change).

This wrapper exists (rather than calling `pip-audit` directly from CI)
for one reason: turning a found vulnerability into a clear pass/fail exit
code plus a readable summary, so CI failure output tells an operator
what's wrong without them needing to parse pip-audit's JSON by hand.

Usage:
    python scripts/scan_dependencies.py [--requirements requirements.txt] [--fail-on low|medium|high|critical]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# pip-audit's own severity strings, ordered low -> critical, matching the
# CVSS-derived severity buckets it reports.
_SEVERITY_ORDER = ["low", "medium", "high", "critical", "unknown"]


def run_pip_audit(requirements: Path) -> dict:
    # Invoked as `python -m pip_audit` rather than the bare `pip-audit`
    # console script: this is robust to any environment where the venv's
    # bin/ directory isn't on PATH (exactly the failure mode hit while
    # developing this script — `pip-audit` not found even though the
    # package was correctly installed in the active venv), and CI runners
    # always invoke scripts through the same `python` that has the venv
    # active, so `sys.executable` is guaranteed correct there too.
    # `--no-deps`: audits exactly the pinned packages in requirements.txt
    # directly, without pip-audit first invoking pip to resolve/build a
    # fresh dependency tree (which needs network access even before the
    # vulnerability lookup itself, and — this matters — pip-audit does
    # NOT fail loudly if that resolution step silently produces an empty
    # dependency set; it happily reports "0 vulnerabilities found" for 0
    # audited packages. Without --no-deps, the false-negative version of
    # this script was verified here: it reported "No known vulnerabilities
    # found" while the audited set was actually empty (a failed internal
    # `pip install --upgrade pip` had been silently swallowed). Real fix,
    # not just a comment — using --no-deps here.
    result = subprocess.run(
        [
            sys.executable, "-m", "pip_audit",
            "--requirement", str(requirements),
            "--no-deps",
            "--format", "json",
        ],
        capture_output=True,
        text=True,
    )
    # pip-audit exits 1 for two genuinely different reasons: "scan ran
    # fine, found vulnerabilities" (stdout has real JSON) and "the scan
    # itself failed" (e.g. a network error reaching its vulnerability
    # service — stdout is then empty). Verified here, in this sandbox,
    # without network access: the second case produces returncode=1 with
    # EMPTY stdout, and this function's earlier version fell through to
    # `json.loads(result.stdout or "{}")` regardless, silently turning a
    # failed scan into a false "0 vulnerabilities found." Distinguishing
    # the two by whether stdout actually contains anything is the fix.
    if result.returncode != 0 and not result.stdout.strip():
        raise RuntimeError(
            "pip-audit failed to complete a scan (no report produced) — "
            "this is a tool/network failure, not a clean result. stderr:\n"
            f"{result.stderr}"
        )

    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise


def _severity_rank(vuln: dict) -> int:
    # pip-audit's JSON doesn't always include a normalized severity field
    # depending on the advisory source; treat missing as "unknown" (worst
    # case: still reported, just not used to trigger --fail-on by itself
    # unless --fail-on unknown is explicitly requested).
    sev = (vuln.get("severity") or "unknown").lower()
    return _SEVERITY_ORDER.index(sev) if sev in _SEVERITY_ORDER else _SEVERITY_ORDER.index("unknown")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path, default=Path("requirements.txt"))
    parser.add_argument(
        "--fail-on",
        choices=_SEVERITY_ORDER,
        default="high",
        help="Minimum severity that causes a non-zero exit (default: high).",
    )
    args = parser.parse_args(argv)

    try:
        report = run_pip_audit(args.requirements)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2  # distinct from 1 ("vulnerabilities found") — this is "scan did not run"
    dependencies = report.get("dependencies", [])

    findings = []
    for dep in dependencies:
        for vuln in dep.get("vulns", []):
            findings.append({**vuln, "package": dep.get("name"), "version": dep.get("version")})

    if not findings:
        print("No known vulnerabilities found.")
        return 0

    threshold_rank = _SEVERITY_ORDER.index(args.fail_on)
    blocking = [f for f in findings if _severity_rank(f) >= threshold_rank]

    print(f"Found {len(findings)} known vulnerabilit{'y' if len(findings) == 1 else 'ies'}:")
    for f in findings:
        marker = "BLOCKING" if f in blocking else "informational"
        print(f"  [{marker}] {f['package']}=={f['version']}: {f.get('id', 'unknown-id')} ({f.get('severity', 'unknown')})")

    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
