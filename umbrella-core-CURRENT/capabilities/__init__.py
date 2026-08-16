"""
capabilities — import every capability module here for its registration
side effect, exactly mirroring the existing `models/__init__.py` pattern of
importing every model module so Alembic can discover them.

Order does not matter for capabilities (unlike models, there's no
inheritance/foreign-key dependency between capability modules), but new
domains should still add their module import here so the app's startup
(`main.py`) has a single place that guarantees every capability is
registered before the first request/CLI command is handled.
"""
from . import system  # noqa: F401
from . import hosting  # noqa: F401
from . import identity  # noqa: F401
from . import automation  # noqa: F401
from . import moderation_intelligence  # noqa: F401
from . import investigation  # noqa: F401
from . import knowledge  # noqa: F401
from . import archive_search  # noqa: F401
from . import memory  # noqa: F401
from . import operational_intelligence  # noqa: F401
from . import player_risk  # noqa: F401
from . import verification  # noqa: F401
from . import webhooks  # noqa: F401
from . import marketplace  # noqa: F401
from . import observability  # noqa: F401
from . import dashboard_layout  # noqa: F401
from . import dev_auth  # noqa: F401
from . import plugin_sandbox  # noqa: F401

__all__ = [
    "system", "hosting", "identity", "automation", "moderation_intelligence",
    "investigation", "knowledge", "archive_search", "memory", "operational_intelligence",
    "player_risk", "verification", "webhooks", "marketplace", "observability",
    "dashboard_layout", "dev_auth", "plugin_sandbox",
]
