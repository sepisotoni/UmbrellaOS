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
from .mc_commands import MCCommand  # noqa: F401
from .translation import PlayerLanguage  # noqa: F401
from .ai_config import AIConfigAction  # noqa: F401
from .plugin_heartbeat import PluginHeartbeat  # noqa: F401
from .plugin_command import PluginCommand  # noqa: F401
from .hosting import Node, ServerTemplate, Allocation, Server, Backup  # noqa: F401
from .api_key import ApiKey  # noqa: F401
from .webhook import WebhookSubscription  # noqa: F401
from .automation import Schedule  # noqa: F401
from .ai import AIModelConfig, ConstitutionRule, AIDecisionLog, ConstitutionTier  # noqa: F401
from .moderation_intelligence import (  # noqa: F401
    ModerationReport,
    ModerationAnalysis,
    StaffEscalation,
    ModerationAction,
    ReportStatus,
    RecommendedAction,
    ModerationActionType,
)
from .knowledge import (  # noqa: F401
    KnownIssue,
    WhitelistEntry,
    WhitelistStatus,
    KnowledgeEntry,
    KnowledgeVersion,
    KnowledgeReviewStatus,
)
from .events import Event  # noqa: F401
from .investigation import Investigation, InvestigationFinding  # noqa: F401
from .memory import MemoryEntry, MemoryScope  # noqa: F401
from .server_metrics import ServerMetricSnapshot  # noqa: F401
from .marketplace import PluginListing, PluginVersion, PluginInstall  # noqa: F401
from .log_entry import LogEntry  # noqa: F401
from .security_event import SecurityEvent  # noqa: F401
from .dashboard_layout import DashboardLayout  # noqa: F401
from .plugin_kv import PluginKvEntry  # noqa: F401
from .plugin_execution import PluginExecutionRecord  # noqa: F401
from .feature_flag import FeatureFlag  # noqa: F401
from .anticheat_violation import AnticheatViolation  # noqa: F401
from .bot_registration import BotRegistration  # noqa: F401
from .plugin_console_line import PluginConsoleLine  # noqa: F401

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
    "MCCommand",
    "PlayerLanguage",
    "AIConfigAction",
    "PluginHeartbeat",
    "PluginCommand",
    "Node",
    "ServerTemplate",
    "Allocation",
    "Server",
    "Backup",
    "ApiKey",
    "Schedule",
    "AIModelConfig",
    "ConstitutionRule",
    "AIDecisionLog",
    "ConstitutionTier",
    "ModerationReport",
    "ModerationAnalysis",
    "StaffEscalation",
    "ModerationAction",
    "ReportStatus",
    "RecommendedAction",
    "ModerationActionType",
    "KnownIssue",
    "WhitelistEntry",
    "WhitelistStatus",
    "KnowledgeEntry",
    "KnowledgeVersion",
    "KnowledgeReviewStatus",
    "Investigation",
    "InvestigationFinding",
    "MemoryEntry",
    "MemoryScope",
    "ServerMetricSnapshot",
    "PluginListing",
    "PluginVersion",
    "PluginInstall",
    "LogEntry",
    "SecurityEvent",
    "DashboardLayout",
    "PluginKvEntry",
    "PluginExecutionRecord",
    "FeatureFlag",
    "AnticheatViolation",
    "BotRegistration",
    "PluginConsoleLine",
]
