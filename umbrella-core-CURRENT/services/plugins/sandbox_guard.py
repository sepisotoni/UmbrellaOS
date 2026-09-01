"""
services/plugins/sandbox_guard.py — static (pre-execution) safety check on
plugin source code.

This is defense-in-depth *in front of* the restricted-execution boundary in
sandbox.py, not a replacement for it — see that module's docstring for why
neither layer is sufficient alone. This layer's job is narrow and
mechanical: reject source that references anything the restricted runtime
already doesn't provide, so a plugin gets a clear "not allowed" error at
install/registration time instead of a confusing NameError buried inside a
subprocess traceback at call time.

Deliberately NOT a security boundary on its own: a static check on source
text can always be defeated by a sufficiently indirect plugin author
(e.g. string-building an attribute name at runtime). The actual boundary is
the restricted `__builtins__`/globals plugin code executes with in
sandbox.py, plus the OS-level resource limits — this module exists to
fail fast on the common, non-adversarial-obfuscation case, and as one more
layer for the adversarial case rather than the only layer.
"""
from __future__ import annotations

import ast

# No import statements at all are permitted in plugin source (v1). A
# plugin needing json/re/math/datetime gets them pre-bound as globals by
# the sandbox executor instead (see sandbox.py's SAFE_GLOBALS) — this
# avoids having to maintain an "allowed module" allowlist that itself has
# to be re-audited every time a new stdlib module is considered (import
# machinery is a common sandbox-escape surface: importlib, pkgutil, and
# even seemingly-safe modules can reach `os` transitively via
# `sys.modules` introspection). Revisit only if a real plugin author hits
# this limit in practice, same posture as the manifest's param vocabulary.
_FORBIDDEN_NAMES = {
    "eval", "exec", "compile", "open", "__import__", "input",
    "vars", "globals", "locals", "getattr", "setattr", "delattr",
    "exit", "quit", "help", "breakpoint",
}

# Dunder attribute names commonly used in known Python sandbox-escape
# gadgets (walking from an innocuous object to its class, its base
# classes, and eventually back to builtins/os). Blocking attribute access
# to these by name is not a complete defense (see module docstring) but
# closes the most common, well-known escape chains
# (`().__class__.__bases__[0].__subclasses__()...`).
_FORBIDDEN_ATTRS = {
    "__class__", "__bases__", "__subclasses__", "__mro__", "__globals__",
    "__builtins__", "__code__", "__closure__", "__func__", "__self__",
    "__dict__", "__getattribute__", "__reduce__", "__reduce_ex__",
    "__import__", "__loader__", "__spec__",
    # Phase 9 additions, based on real Phase 8 adversarial hand-testing
    # (see PHASE7-COMPLETE-AND-PHASE8-HANDOFF.md: a raw dunder-chain
    # attempt and a format-string two-stage gadget were both caught, but
    # neither exercised these specific names) — __init_subclass__ and
    # __subclasshook__ are alternate entry points into the same
    # class-hierarchy-walking gadget family as __bases__/__mro__ above;
    # __getattr__/__setattr__ override lets crafted code intercept
    # attribute access itself rather than just reading a forbidden one.
    "__init_subclass__", "__subclasshook__", "__getattr__", "__setattr__",
    # [PLUGIN] audit addition, 2026-09-01: format/format_map. Empirically
    # confirmed (not theoretical) that `"{0.__class__.__base__.__subclasses__}"
    # .format(params)` reads straight through this entire allowlist against
    # the real sandbox.py runtime: str.format()'s field-name mini-language
    # walks `.attr` and `[key]` chains via CPython's internal C-level
    # attribute/item resolution, which is NOT the same code path Python-level
    # `getattr`/`ast.Attribute` checks touch — the dunder chain lives as
    # opaque TEXT inside a string constant, so ast.walk() never sees an
    # ast.Attribute node for __class__/__subclasses__/etc. at all, and
    # sandbox.py's restricted __builtins__ doesn't gate string *methods*
    # (str is itself in the safe-builtins allowlist, and .format is always
    # available on any string instance regardless of what names are
    # resolvable in scope). f-strings are unaffected by this fix — their
    # `{x.attr}` expressions are real Python source parsed into genuine
    # ast.Attribute nodes that this module's ast.walk() already recurses
    # into and catches today; this gap is specific to the *method call*
    # `"...".format(...)` / `"...".format_map(...)`, whose field-name
    # string content is invisible to static AST inspection by definition.
    # str.format()/.format_map() always return str (no live object/callable
    # ever crosses back into plugin code this way), so the confirmed impact
    # is arbitrary-attribute-chain information disclosure via repr(), not
    # remote code execution — still a real violation of this module's own
    # documented guarantee to close "the most common, well-known escape
    # chains", and blocking it costs no legitimate plugin functionality
    # (f-strings and %-style formatting remain fully available).
    "format", "format_map",
}

# Phase 9 addition, based on real Phase 8 usage: no legitimate plugin
# entrypoint approaches this size (the largest real Phase 7 test fixture
# plugin is well under 2KB); a source this large is far more likely to be
# an obfuscated payload or a pathological input meant to make ast.walk's
# traversal or compile() itself expensive than a real plugin. Checked
# before parsing, so an oversized payload never even reaches ast.parse.
_MAX_SOURCE_BYTES = 65_536


class SandboxViolation(ValueError):
    """Raised when plugin source references something the restricted
    runtime doesn't allow. Raised at registration/validation time
    (before any plugin code ever runs), not at call time."""


def check_source_safety(source: str, *, entrypoint: str) -> None:
    """Parse `source` and raise SandboxViolation on the first disallowed
    construct found. Raises SandboxViolation (not SyntaxError) for source
    that doesn't even parse, so callers only need to catch one exception
    type for "this plugin's code cannot be registered."
    """
    if len(source.encode("utf-8")) > _MAX_SOURCE_BYTES:
        raise SandboxViolation(
            f"{entrypoint}: source exceeds the maximum permitted size of "
            f"{_MAX_SOURCE_BYTES} bytes."
        )

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise SandboxViolation(f"{entrypoint}: source does not parse: {exc}") from exc

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise SandboxViolation(
                f"{entrypoint}: import statements are not permitted in plugin code "
                f"(line {node.lineno}). Pre-approved safe modules are already available "
                "as globals inside the sandbox — see sandbox.py's SAFE_GLOBALS."
            )
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
            raise SandboxViolation(
                f"{entrypoint}: reference to disallowed name {node.id!r} at line {node.lineno}."
            )
        if isinstance(node, ast.Attribute) and node.attr in _FORBIDDEN_ATTRS:
            raise SandboxViolation(
                f"{entrypoint}: access to disallowed attribute {node.attr!r} at line {node.lineno}."
            )
