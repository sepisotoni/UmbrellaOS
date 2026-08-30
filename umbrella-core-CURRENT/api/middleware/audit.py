"""
api/middleware/audit.py — Legacy audit logging helpers.

Provides:
- create_audit_log() / log_action() — manual audit log helpers, still used
  by some routers (e.g. staff, roles) for actions outside the Capability
  Registry.
- AuditContext — batch helper for grouping several audit writes together.

Despite the module name, there is no Starlette/FastAPI middleware class
here and no automatic per-request audit logging — every write is an
explicit call site choosing to log. Automatic auditing exists, but lives
in registry/registry.py's CapabilityRegistry.call(), which audits every
`@capability`-decorated handler's success/failure automatically without
the handler needing to call anything here. New capability-registry work
should audit_category= via that mechanism rather than adding call sites
to this module.

`details` is a free-form dict serialized as-is into details_json — this
module performs NO automatic redaction of secrets. Callers are responsible
for masking sensitive values before passing them in (see
services/settings_service.py's own update() for the pattern: replace with
"***" when the underlying field is marked sensitive).
"""
from sqlalchemy.ext.asyncio import AsyncSession
from models import AuditLog
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from uuid import uuid4
from enum import Enum


class AuditAction(str, Enum):
    """Standard audit action types."""
    # User actions
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    
    # Role/Permission actions
    ROLE_CREATED = "role.created"
    ROLE_UPDATED = "role.updated"
    PERMISSION_GRANTED = "permission.granted"
    PERMISSION_REVOKED = "permission.revoked"
    
    # Moderation actions
    PLAYER_KICKED = "player.kicked"
    PLAYER_WARNED = "player.warned"
    PLAYER_BANNED = "player.banned"
    PLAYER_UNBANNED = "player.unbanned"
    IP_BANNED = "ip.banned"
    IP_UNBANNED = "ip.unbanned"
    
    # Appeal actions
    APPEAL_CREATED = "appeal.created"
    APPEAL_REVIEWED = "appeal.reviewed"
    APPEAL_APPROVED = "appeal.approved"
    APPEAL_DENIED = "appeal.denied"
    
    # Settings actions
    SETTING_UPDATED = "setting.updated"
    
    # Plugin actions
    PLUGIN_INSTALLED = "plugin.installed"
    PLUGIN_UPDATED = "plugin.updated"
    PLUGIN_REMOVED = "plugin.removed"
    
    # MC command actions
    MC_COMMAND_REQUESTED = "mc_command.requested"
    MC_COMMAND_EXECUTED = "mc_command.executed"
    
    # AI config actions
    AI_CONFIG_REQUESTED = "ai_config.requested"
    AI_CONFIG_APPLIED = "ai_config.applied"
    AI_CONFIG_REJECTED = "ai_config.rejected"


async def create_audit_log(
    db: AsyncSession,
    action: AuditAction,
    actor: Optional[str] = "SYSTEM",
    actor_type: Optional[str] = "system",
    target: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """
    Create an audit log entry.
    
    Args:
        db: Database session
        action: Action type (from AuditAction enum)
        actor: Who performed the action (defaults to SYSTEM)
        actor_type: Type of actor (staff|plugin|bot|system|ai, defaults to system)
        target: UUID of affected resource
        details: Additional details (JSON)
    
    Returns:
        Created AuditLog instance
    """
    import json
    audit_log = AuditLog(
        id=str(uuid4()),
        action=action.value,
        actor=actor or "SYSTEM",
        actor_type=actor_type or "system",
        target=target,
        details_json=json.dumps(details or {}) if details else "{}",
        created_at=datetime.now(timezone.utc)
    )
    db.add(audit_log)
    await db.flush()
    return audit_log


async def log_action(
    db: AsyncSession,
    action: str,
    description: Optional[str] = None,
    actor: Optional[str] = None,
    target: Optional[str] = None,
) -> AuditLog:
    """
    Simplified audit logging.
    """
    details = {}
    if description:
        details["description"] = description
    
    return await create_audit_log(
        db=db,
        action=AuditAction(action),
        actor=actor,
        target=target,
        details=details
    )


class AuditContext:
    """Context manager for batch audit operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logs: list[AuditLog] = []
    
    async def add(
        self,
        action: AuditAction,
        actor: Optional[str] = None,
        target: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add audit log to batch."""
        log = await create_audit_log(
            self.db,
            action=action,
            actor=actor,
            target=target,
            details=details
        )
        self.logs.append(log)
    
    async def flush(self) -> None:
        """Write all logs."""
        await self.db.flush()
