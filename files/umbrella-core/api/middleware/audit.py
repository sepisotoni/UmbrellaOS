"""
api/middleware/audit.py — Audit logging for all API actions.

Provides:
- Audit log creation helper
- Automatic audit middleware
- Action tracking
"""
from sqlalchemy.ext.asyncio import AsyncSession
from models import AuditLog
from datetime import datetime
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


async def create_audit_log(
    db: AsyncSession,
    action: AuditAction,
    staff_id: Optional[str] = "SYSTEM",
    target_uuid: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    """
    Create an audit log entry.
    
    Args:
        db: Database session
        action: Action type (from AuditAction enum)
        staff_id: User who performed action (defaults to SYSTEM)
        target_uuid: UUID of affected resource
        details: Additional details (JSON)
        ip_address: IP address of requester
        user_agent: User agent string
    
    Returns:
        Created AuditLog instance
    """
    audit_log = AuditLog(
        id=str(uuid4()),
        action=action.value,
        staff_id=staff_id or "SYSTEM",
        target_uuid=target_uuid,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=datetime.utcnow()
    )
    db.add(audit_log)
    await db.flush()
    return audit_log


async def log_action(
    db: AsyncSession,
    action: str,
    description: Optional[str] = None,
    staff_id: Optional[str] = None,
    target_id: Optional[str] = None,
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
        staff_id=staff_id,
        target_uuid=target_id,
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
        staff_id: Optional[str] = None,
        target_uuid: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add audit log to batch."""
        log = await create_audit_log(
            self.db,
            action=action,
            staff_id=staff_id,
            target_uuid=target_uuid,
            details=details
        )
        self.logs.append(log)
    
    async def flush(self) -> None:
        """Write all logs."""
        await self.db.flush()
