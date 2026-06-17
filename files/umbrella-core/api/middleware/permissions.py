"""
api/middleware/permissions.py — Permission and role-based access control.

Provides:
- Permission checking dependencies
- Role validation
- Permission-based endpoint protection
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import User, Role, Permission
from typing import Optional, List
from .errors import PermissionDeniedException


async def get_current_user_from_token(
    session_token: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Extract current user from session token.
    Returns None if no token provided or token invalid.
    """
    if not session_token:
        return None
    
    from models import Session as SessionModel
    from datetime import datetime
    
    stmt = select(SessionModel).where(
        SessionModel.token == session_token,
        SessionModel.revoked == False,
    )
    result = await db.execute(stmt)
    db_session = result.scalar_one_or_none()
    
    if not db_session or not db_session.is_valid():
        return None
    
    # Fetch user
    stmt = select(User).where(User.id == db_session.user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def require_permission(
    permission_key: str,
    user: Optional[User] = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency: validates user has specific permission.
    Raises PermissionDeniedException if user lacks permission.
    """
    if not user or not user.is_active:
        raise PermissionDeniedException("User not authenticated or inactive")
    
    # Fetch user's role with permissions
    stmt = select(Role).where(Role.id == user.role_id)
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()
    
    if not role:
        raise PermissionDeniedException("User role not found")
    
    # Check if role has this permission
    stmt = select(Permission).where(
        Permission.permission_key == permission_key
    )
    result = await db.execute(stmt)
    permission = result.scalar_one_or_none()
    
    if not permission:
        raise PermissionDeniedException(f"Permission '{permission_key}' does not exist")
    
    # Verify role has this permission
    if permission not in role.permissions:
        raise PermissionDeniedException(
            f"User role '{role.name}' lacks permission '{permission_key}'"
        )
    
    return user


async def require_role(
    role_name: str,
    user: Optional[User] = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency: validates user has specific role.
    Raises PermissionDeniedException if user doesn't have role.
    """
    if not user or not user.is_active:
        raise PermissionDeniedException("User not authenticated or inactive")
    
    # Fetch user's role
    stmt = select(Role).where(Role.id == user.role_id)
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()
    
    if not role or role.name != role_name:
        raise PermissionDeniedException(
            f"User role '{role.name if role else 'none'}' is not '{role_name}'"
        )
    
    return user


async def get_user_permissions(
    user: Optional[User] = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> List[str]:
    """
    Dependency: returns list of permission keys for current user.
    """
    if not user or not user.is_active:
        return []
    
    # Fetch role with permissions
    stmt = select(Role).where(Role.id == user.role_id)
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()
    
    if not role:
        return []
    
    return [p.permission_key for p in role.permissions]


def permission_required(permission_key: str):
    """
    Decorator for permission-based endpoint protection.
    Usage: @app.get("/endpoint", dependencies=[Depends(permission_required("read:user"))])
    """
    async def verify(user: User = Depends(require_permission(permission_key))):
        return user
    return verify
