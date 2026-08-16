"""
tests/test_dependency_scanning.py — Tests for scripts/scan_dependencies.py
and scripts/generate_sbom.py (Phase 9, item 6).

Both scripts' actual scan/lookup steps need network access this sandbox
doesn't have (see the scripts' own docstrings for what was and wasn't
verified live). These tests cover everything that doesn't: SBOM
generation (purely local — reads requirements.txt, writes JSON, verified
end-to-end against the real requirements.txt) and scan_dependencies.py's
severity-ranking/report-parsing logic (verified with a synthetic
pip-audit JSON report, and — importantly — a synthetic *empty-stdout
failure*, which is the specific false-negative bug this script's
docstring documents having found and fixed in this sandbox).
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import scan_dependencies  # noqa: E402
import generate_sbom  # noqa: E402


# --- generate_sbom.py ---


def test_parse_requirements_extracts_pinned_packages(tmp_path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("fastapi==0.115.5\n# a comment\n\nsqlalchemy==2.0.36\n-r other.txt\n")
    packages = generate_sbom.parse_requirements(req_file)
    assert packages == [("fastapi", "0.115.5"), ("sqlalchemy", "2.0.36")]


def test_parse_requirements_strips_extras():
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("uvicorn[standard]==0.32.0\n")
        path = Path(f.name)
    try:
        packages = generate_sbom.parse_requirements(path)
        assert packages == [("uvicorn", "0.32.0")]
    finally:
        path.unlink()


def test_build_sbom_creates_one_component_per_package():
    bom = generate_sbom.build_sbom([("fastapi", "0.115.5"), ("sqlalchemy", "2.0.36")])
    names = {c.name for c in bom.components}
    assert names == {"fastapi", "sqlalchemy"}


def test_main_generates_valid_cyclonedx_json_against_real_requirements(tmp_path):
    real_requirements = Path(__file__).parent.parent / "requirements.txt"
    output = tmp_path / "sbom.json"
    exit_code = generate_sbom.main(["--requirements", str(real_requirements), "--output", str(output)])
    assert exit_code == 0
    sbom = json.loads(output.read_text())
    assert "components" in sbom
    assert len(sbom["components"]) > 0
    assert any(c["name"] == "fastapi" for c in sbom["components"])


def test_main_errors_cleanly_on_missing_requirements_file(tmp_path):
    exit_code = generate_sbom.main(["--requirements", str(tmp_path / "nope.txt"), "--output", str(tmp_path / "out.json")])
    assert exit_code == 1


# --- scan_dependencies.py ---


def test_severity_rank_orders_low_to_critical():
    assert scan_dependencies._severity_rank({"severity": "low"}) < scan_dependencies._severity_rank({"severity": "high"})
    assert scan_dependencies._severity_rank({"severity": "high"}) < scan_dependencies._severity_rank({"severity": "critical"})


def test_severity_rank_treats_missing_severity_as_unknown_worst_case():
    assert scan_dependencies._severity_rank({}) == scan_dependencies._SEVERITY_ORDER.index("unknown")


def test_main_reports_no_findings_when_report_has_no_vulns(monkeypatch):
    monkeypatch.setattr(scan_dependencies, "run_pip_audit", lambda req: {"dependencies": [{"name": "fastapi", "version": "0.115.5", "vulns": []}]})
    exit_code = scan_dependencies.main(["--requirements", "requirements.txt"])
    assert exit_code == 0


def test_main_blocks_on_finding_at_or_above_threshold(monkeypatch, capsys):
    fake_report = {
        "dependencies": [
            {"name": "badpkg", "version": "1.0.0", "vulns": [{"id": "CVE-2024-0001", "severity": "critical"}]}
        ]
    }
    monkeypatch.setattr(scan_dependencies, "run_pip_audit", lambda req: fake_report)
    exit_code = scan_dependencies.main(["--requirements", "requirements.txt", "--fail-on", "high"])
    assert exit_code == 1
    assert "BLOCKING" in capsys.readouterr().out


def test_main_does_not_block_on_finding_below_threshold(monkeypatch):
    fake_report = {
        "dependencies": [
            {"name": "mildpkg", "version": "1.0.0", "vulns": [{"id": "CVE-2024-0002", "severity": "low"}]}
        ]
    }
    monkeypatch.setattr(scan_dependencies, "run_pip_audit", lambda req: fake_report)
    exit_code = scan_dependencies.main(["--requirements", "requirements.txt", "--fail-on", "high"])
    assert exit_code == 0


def test_run_pip_audit_raises_on_empty_stdout_with_nonzero_exit(monkeypatch):
    """The specific false-negative bug documented in this script's
    docstring: pip-audit exiting non-zero with EMPTY stdout (a tool/network
    failure) must be distinguished from a real empty result, not silently
    treated as '0 vulnerabilities found'."""
    class _FakeCompletedProcess:
        returncode = 1
        stdout = ""
        stderr = "some network error"

    monkeypatch.setattr(scan_dependencies.subprocess, "run", lambda *a, **k: _FakeCompletedProcess())
    with pytest.raises(RuntimeError, match="failed to complete a scan"):
        scan_dependencies.run_pip_audit(Path("requirements.txt"))


def test_run_pip_audit_parses_real_json_even_with_nonzero_exit(monkeypatch):
    """pip-audit's normal 'vulnerabilities found' case also exits non-zero
    — that must still parse successfully, not be treated as a tool failure."""
    class _FakeCompletedProcess:
        returncode = 1
        stdout = json.dumps({"dependencies": [{"name": "x", "version": "1.0", "vulns": []}]})
        stderr = ""

    monkeypatch.setattr(scan_dependencies.subprocess, "run", lambda *a, **k: _FakeCompletedProcess())
    report = scan_dependencies.run_pip_audit(Path("requirements.txt"))
    assert report["dependencies"][0]["name"] == "x"
