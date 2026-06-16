"""
models/permissions.py — Role-based permission system.

Design decisions:
- Roles are named groups (Owner, Admin, Moderator, Helper).
- Permissions are fine-grained string keys (e.g. "ban_players").
- role_permissions is the join table linking them.
- This replaces the hardcoded umbrella.helper / .mod / .admin
  Bukkit permissions from the old plugin — Core is now the authority.

Default roles seeded by migration:
    owner     — all permissions
    admin     — all except manage_roles, manage_api_keys
    moderator — ban, mute, kick, warn, lookup
    helper    — kick, warn, lookup
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Table, Column, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.engine import Base


# Many-to-many join table: roles <-> permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String(36), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )

    def __repr__(self) -> str:
        return f"<Role name={self.name!r}>"


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    permission_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary=role_permissions, back_populates="permissions"
    )

    def __repr__(self) -> str:
        return f"<Permission key={self.permission_key!r}>"
