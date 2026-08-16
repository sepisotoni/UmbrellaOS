"""tests/registry/test_plugin_sandbox_guard.py — static AST safety check."""
import pytest

from services.plugins.sandbox_guard import SandboxViolation, check_source_safety


def test_clean_source_passes():
    src = "def run(params):\n    return {'ok': True, 'n': params.get('n', 0) + 1}\n"
    check_source_safety(src, entrypoint="handlers:run")  # should not raise


@pytest.mark.parametrize("stmt", ["import os", "import sys", "from os import path", "import subprocess"])
def test_import_statements_rejected(stmt):
    src = f"{stmt}\ndef run(params):\n    return {{}}\n"
    with pytest.raises(SandboxViolation):
        check_source_safety(src, entrypoint="handlers:run")


@pytest.mark.parametrize("expr", ["eval('1')", "exec('1')", "open('x')", "__import__('os')", "globals()"])
def test_forbidden_names_rejected(expr):
    src = f"def run(params):\n    {expr}\n    return {{}}\n"
    with pytest.raises(SandboxViolation):
        check_source_safety(src, entrypoint="handlers:run")


@pytest.mark.parametrize("attr", ["__class__", "__globals__", "__subclasses__", "__bases__", "__builtins__"])
def test_forbidden_attribute_access_rejected(attr):
    src = f"def run(params):\n    x = params.{attr}\n    return {{}}\n"
    with pytest.raises(SandboxViolation):
        check_source_safety(src, entrypoint="handlers:run")


def test_known_escape_gadget_rejected():
    """The classic `().__class__.__bases__[0].__subclasses__()` chain used
    to walk from a harmless object back to builtins/os."""
    src = (
        "def run(params):\n"
        "    leak = ().__class__.__bases__[0].__subclasses__()\n"
        "    return {'leak': str(leak)}\n"
    )
    with pytest.raises(SandboxViolation):
        check_source_safety(src, entrypoint="handlers:run")


def test_syntax_error_raises_sandbox_violation_not_syntax_error():
    with pytest.raises(SandboxViolation):
        check_source_safety("def run(params)\n    return {}\n", entrypoint="handlers:run")


# --- Phase 9 hardening additions ---


@pytest.mark.parametrize("attr", ["__init_subclass__", "__subclasshook__", "__getattr__", "__setattr__"])
def test_phase9_forbidden_attribute_access_rejected(attr):
    src = f"def run(params):\n    x = params.{attr}\n    return {{}}\n"
    with pytest.raises(SandboxViolation):
        check_source_safety(src, entrypoint="handlers:run")


def test_oversized_source_rejected():
    # Comfortably clears the 65536-byte cap without needing a real payload.
    src = "def run(params):\n    x = 1  # " + ("a" * 70_000) + "\n    return {}\n"
    with pytest.raises(SandboxViolation, match="exceeds the maximum permitted size"):
        check_source_safety(src, entrypoint="handlers:run")


def test_source_under_size_cap_not_rejected_for_size():
    src = "def run(params):\n    return {'ok': True}\n"
    check_source_safety(src, entrypoint="handlers:run")  # should not raise
