"""
main.py — Umbrella Core entry point.

Startup sequence:
1. Create DB tables (dev) or rely on Alembic (prod).
2. Seed default settings if none exist.
3. Seed default roles and permissions if none exist.
4. Mount all API routers.
5. Start uvicorn.
"""
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import get_db, create_tables, AsyncSessionLocal
from services import SettingsService, RolesService
import models  # noqa: F401

# Import routers
from api.routers.health import router as health_router
from api.routers.settings import router as settings_router
from api.routers.roles import router as roles_router
from api.routers.audit import router as audit_router
from api.routers.plugin import router as plugin_router
from api.routers.players import router as players_router
from api.routers.punishments import router as punishments_router
from api.routers.appeals import router as appeals_router
from api.routers.moderation import router as moderation_router
from api.routers.auth import router as auth_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Runs startup logic before the app accepts requests,
    and cleanup after shutdown.
    """
    # --- Startup ---
    print("[Umbrella Core] Starting up...")

    # Create tables (safe in dev; in prod, use Alembic migrations instead)
    await create_tables()
    print("[Umbrella Core] Database tables ready")

    # Seed defaults
    async with AsyncSessionLocal() as db:
        await SettingsService.seed_defaults(db)
        await RolesService.seed_defaults(db)
    print("[Umbrella Core] Defaults seeded")

    print(f"[Umbrella Core] Ready — listening on {settings.app_host}:{settings.app_port}")

    yield

    # --- Shutdown ---
    print("[Umbrella Core] Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Umbrella Core",
    description="Central backend for UmbrellaMC — all clients talk to this.",
    version="1.0.0",
    lifespan=lifespan,
    # Disable docs in production
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS — restrict to your dashboard domain in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://your-dashboard.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(health_router)
app.include_router(settings_router)
app.include_router(roles_router)
app.include_router(audit_router)
app.include_router(plugin_router)
app.include_router(players_router)
app.include_router(punishments_router)
app.include_router(appeals_router)
app.include_router(moderation_router)
app.include_router(auth_router)


@app.get("/")
async def root():
    return {
        "service": "umbrella-core",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled (set DEBUG=true to enable)",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
