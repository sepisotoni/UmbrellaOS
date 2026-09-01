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


# --- [PLUGIN] audit addition, 2026-09-01: str.format() dunder-chain escape ---
#
# Empirically confirmed against the REAL restricted globals in
# services/plugins/sandbox.py::_build_safe_globals() before this fix existed:
# "{0.__class__.__base__.__subclasses__}".format(params) successfully read
# straight through both defense layers, because the dunder chain lives as
# opaque text inside a string literal (no ast.Attribute node for
# check_source_safety's ast.walk() to see) and str.format() is a normal
# method on any string instance (not gated by the restricted __builtins__
# dict at all — see sandbox.py's own _build_safe_globals, which restricts
# *names*, not *methods on already-constructed builtin-type instances*).


def test_format_string_dunder_chain_rejected():
    """The gadget that actually worked before this fix: a __class__ walk
    hidden inside a str.format() field-name string, invisible to any
    ast.Attribute-based check."""
    src = (
        "def run(params):\n"
        "    gadget = '{0.__class__.__base__.__subclasses__}'\n"
        "    return {'leak': gadget.format(params)}\n"
    )
    with pytest.raises(SandboxViolation, match="format"):
        check_source_safety(src, entrypoint="handlers:run")


def test_format_map_dunder_chain_rejected():
    """Same gadget family via format_map instead of format."""
    src = (
        "def run(params):\n"
        "    return {'leak': '{x.__globals__}'.format_map({'x': run})}\n"
    )
    with pytest.raises(SandboxViolation, match="format_map"):
        check_source_safety(src, entrypoint="handlers:run")


def test_ordinary_format_call_also_rejected():
    """No partial allowlist — .format()/.format_map() are blocked entirely,
    including totally benign uses, since there's no way to statically tell
    a safe format-string apart from one hiding a dunder-chain field name."""
    src = "def run(params):\n    return {'msg': 'value is {}'.format(params.get('x'))}\n"
    with pytest.raises(SandboxViolation, match="format"):
        check_source_safety(src, entrypoint="handlers:run")


def test_fstring_still_allowed_after_format_ban():
    """f-strings use real ast.Attribute nodes for their {expr} parts
    (already caught independently, see test_forbidden_attribute_access_rejected
    for the case where one DOES reference a forbidden attr) and don't call
    str.format()/.format_map() at all — banning those methods must not
    collaterally block ordinary f-string usage, the safe alternative."""
    src = "def run(params):\n    name = params.get('name', 'world')\n    return {'greeting': f'hello {name}!'}\n"
    check_source_safety(src, entrypoint="handlers:run")  # should not raise


def test_percent_style_formatting_still_allowed():
    """%-style formatting has no field-name mini-language capable of
    attribute/item traversal at all (unlike .format()/.format_map()) — it
    only ever calls str()/repr() on its argument — so it carries none of
    this vulnerability class and should remain unblocked."""
    src = "def run(params):\n    return {'msg': 'value is %s' % params.get('x')}\n"
    check_source_safety(src, entrypoint="handlers:run")  # should not raise


def test_format_dunder_chain_rejected_before_reaching_real_sandbox_process():
    """End-to-end confirmation using the actual ProcessSandbox, not just
    check_source_safety() in isolation — the exploit source must be
    rejected at the static-guard stage inside ProcessSandbox.run(), before
    any child process is ever spawned to execute it."""
    import asyncio
    from services.plugins.sandbox import ProcessSandbox
    from services.plugins.sandbox_guard import SandboxViolation as SV

    exploit_source = (
        "def fn(params):\n"
        "    gadget = '{0.__class__.__base__.__subclasses__}'\n"
        "    return {'leaked': gadget.format(params)}\n"
    )
    sandbox = ProcessSandbox(sources={"evil-plugin": {"handlers": exploit_source}})

    async def _run():
        await sandbox.run(
            plugin_id="evil-plugin",
            entrypoint="handlers:fn",
            params={},
            actor_id="test-actor",
        )

    with pytest.raises(SV):
        asyncio.run(_run())
