"""
tests/test_discord_user_id_propagation.py — A regression guard, not a unit
test in the usual sense: Phase 6's slash-command -> REST-permission
mapping (see UmbrellaCoreClient.invoke()'s docstring and
registry/context.py's from_discord_user on the umbrella-core side) only
works if every cog's self.bot.core.invoke(...) call actually passes
discord_user_id. That was a purely mechanical edit across ~20 call sites
in 8 files, which is exactly the kind of change that's easy to get
partially right and not notice - a normal pure-function test wouldn't
catch a missing discord_user_id= (the formatting functions don't care),
so this inspects the actual source via Python's ast module instead of
regex (multi-line calls make regex unreliable here).

notifications_cog.py is the one deliberate exception - it's a background
poll with no invoking Discord user at all, documented in its own
poll_escalations() comment.
"""
import ast
from pathlib import Path

COGS_DIR = Path(__file__).parent.parent / "bot" / "cogs"
EXEMPT_FILES = {"notifications_cog.py"}


def _find_invoke_calls_missing_discord_user_id(source: str) -> list[int]:
    """Returns line numbers of any `self.bot.core.invoke(...)` call that
    doesn't pass a `discord_user_id` keyword argument."""
    tree = ast.parse(source)
    missing = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "invoke"):
            continue
        # Match self.bot.core.invoke(...) specifically, not just any .invoke(...)
        if not (
            isinstance(func.value, ast.Attribute)
            and func.value.attr == "core"
            and isinstance(func.value.value, ast.Attribute)
            and func.value.value.attr == "bot"
        ):
            continue

        has_discord_user_id = any(kw.arg == "discord_user_id" for kw in node.keywords)
        if not has_discord_user_id:
            missing.append(node.lineno)

    return missing


def test_every_cog_invoke_call_passes_discord_user_id():
    violations: dict[str, list[int]] = {}

    for path in sorted(COGS_DIR.glob("*.py")):
        if path.name in EXEMPT_FILES or path.name == "__init__.py":
            continue
        missing_lines = _find_invoke_calls_missing_discord_user_id(path.read_text())
        if missing_lines:
            violations[path.name] = missing_lines

    assert not violations, (
        f"self.bot.core.invoke(...) calls missing discord_user_id "
        f"(Phase 6 permission mapping won't apply to these): {violations}"
    )


def test_notifications_cog_is_the_only_exempt_file():
    """If this ever needs a second exemption, it should be a deliberate,
    documented decision (like notifications_cog.py's own comment) - this
    test exists so adding an exemption is a visible diff, not a silent one."""
    assert EXEMPT_FILES == {"notifications_cog.py"}
