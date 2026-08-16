"""
services/server_template_service.py — Server templates ("eggs"): the image,
startup command, and defaults a Server is created from.

Templates are versioned (see models/hosting.py's ServerTemplate.version) so
editing a template later never silently changes what an already-created
Server does — each Server pins the template_version it was created with.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.errors import AppException
from models.hosting import ServerTemplate


class ServerTemplateError(AppException):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, "SERVER_TEMPLATE_ERROR", status_code)


class ServerTemplateService:
    @staticmethod
    async def create_template(
        db: AsyncSession,
        name: str,
        image: str,
        description: str | None = None,
        startup_command: list[str] | None = None,
        default_env: dict[str, str] | None = None,
        default_memory_bytes: int = 1_073_741_824,
        default_cpu_cores: float = 1.0,
    ) -> ServerTemplate:
        template = ServerTemplate(
            name=name,
            image=image,
            description=description,
            startup_command=startup_command or [],
            default_env=default_env or {},
            default_memory_bytes=default_memory_bytes,
            default_cpu_cores=default_cpu_cores,
            version=1,
        )
        db.add(template)
        await db.flush()
        return template

    @staticmethod
    async def update_template(
        db: AsyncSession,
        template_id: str,
        **changes,
    ) -> ServerTemplate:
        """
        Apply changes and bump `version`. Existing Servers keep whatever
        template_version they were created with — this only affects
        servers created *after* the bump, by design (see module docstring).
        """
        template = await ServerTemplateService.get_template(db, template_id)
        allowed = {
            "name", "image", "description", "startup_command",
            "default_env", "default_memory_bytes", "default_cpu_cores",
        }
        for key, value in changes.items():
            if key not in allowed:
                raise ServerTemplateError(f"cannot update field {key!r}")
            setattr(template, key, value)
        template.version += 1
        await db.flush()
        return template

    @staticmethod
    async def list_templates(db: AsyncSession) -> list[ServerTemplate]:
        result = await db.execute(select(ServerTemplate).order_by(ServerTemplate.name))
        return list(result.scalars().all())

    @staticmethod
    async def get_template(db: AsyncSession, template_id: str) -> ServerTemplate:
        template = await db.get(ServerTemplate, template_id)
        if template is None:
            raise ServerTemplateError(f"no template with id {template_id!r}", 404)
        return template
