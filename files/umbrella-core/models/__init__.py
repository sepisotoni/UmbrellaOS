# Import all models here so Alembic's autogenerate can discover them.
# Order matters: Base must be imported first, then all model files.
from database.engine import Base  # noqa: F401
from .setting import Setting       # noqa: F401
from .audit_log import AuditLog   # noqa: F401
from .permissions import Role, Permission, role_permissions  # noqa: F401
from .player import Player, IPAddress, Punishment, Appeal  # noqa: F401
from .user import User, Session, DiscordOAuthPending  # noqa: F401
from .discord import DiscordAccount, ChatMessage  # noqa: F401
from .verification import VerificationCode  # noqa: F401
from .alt_detection import SuspicionEvent, AltGroup, AltGroupMember  # noqa: F401
from .analytics import AnalyticsEvent, PlayerStat  # noqa: F401
from .replay import ReplaySession, ReplayEvent  # noqa: F401
from .snapshot import PlayerSnapshot  # noqa: F401
from .ai_tasks import AITask  # noqa: F401

__all__ = [
    "Base",
    "Setting",
    "AuditLog",
    "Role",
    "Permission",
    "role_permissions",
    "Player",
    "IPAddress",
    "Punishment",
    "Appeal",
    "User",
    "Session",
    "DiscordOAuthPending",
    "DiscordAccount",
    "ChatMessage",
    "VerificationCode",
    "SuspicionEvent",
    "AltGroup",
    "AltGroupMember",
    "AnalyticsEvent",
    "PlayerStat",
    "ReplaySession",
    "ReplayEvent",
    "PlayerSnapshot",
    "AITask",
]
