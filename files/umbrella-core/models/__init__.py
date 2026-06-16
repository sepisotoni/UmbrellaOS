# Import all models here so Alembic's autogenerate can discover them.
# Order matters: Base must be imported first, then all model files.
from database.engine import Base  # noqa: F401
from .setting import Setting       # noqa: F401
from .audit_log import AuditLog   # noqa: F401
from .permissions import Role, Permission, role_permissions  # noqa: F401

__all__ = ["Base", "Setting", "AuditLog", "Role", "Permission", "role_permissions"]
