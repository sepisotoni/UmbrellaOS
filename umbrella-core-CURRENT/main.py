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
import logging
from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import get_db, create_tables, AsyncSessionLocal
from services import SettingsService, RolesService
from api.middleware.errors import register_error_handlers
from api.middleware.rate_limit import RateLimitMiddleware
from api.middleware.metrics import MetricsMiddleware
from api.middleware.tracing import TracingMiddleware
from api.middleware.waf import WAFMiddleware
from services.rate_limit_service import RateLimiter
import models  # noqa: F401
import capabilities  # noqa: F401 - registers every @capability with the registry
from services.plugins.runtime import reload_installed_plugins
from registry.adapters.rest import router as capabilities_router
from api.routers.hosting_console_ws import router as hosting_console_ws_router
from services.scheduler_loop import run_scheduler_loop
from services.operational_intelligence.sampler_loop import run_sampler_loop
import services.events  # noqa: F401 - registers built-in event subscribers before the dispatcher starts
from services.events import run_event_dispatcher_loop
from services.log_aggregation_service import DBLogHandler, run_log_flush_loop

# Root-logger handler that feeds the log-aggregation queue (Phase 9, item
# 3). Module-level singleton so it's the same instance added/removed
# across the lifespan handler above.
_db_log_handler = DBLogHandler()

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
from api.routers.bridge import router as bridge_router
from api.routers.verification import router as verification_router
from api.routers.alt_detection import router as alt_detection_router
from api.routers.analytics import router as analytics_router
from api.routers.replay import router as replay_router
from api.routers.snapshot import router as snapshot_router
from api.routers.ai_tasks import router as ai_tasks_router
from api.routers.mc_commands import router as mc_commands_router
from api.routers.translation import router as translation_router
from api.routers.ai_config import router as ai_config_router
from api.routers.anticheat import router as anticheat_router
from api.routers.dashboard import router as dashboard_router
from api.routers.server_control import router as server_control_router
from api.routers.staff import router as staff_router
from api.routers.metrics import router as metrics_router
from api.routers.logs import router as logs_router
from api.routers.security import router as security_router
from api.routers.feature_flags import router as feature_flags_router

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

    # Re-register already-installed marketplace plugins' capabilities
    # (Phase 7 item 3) — CapabilityRegistry and the plugin sandbox are
    # both in-memory, so nothing about an install survives a restart on
    # its own; this restores every `plugin_installs` row back to a live,
    # callable capability. Runs after defaults-seeding so
    # register_plugin_capabilities' permission-key validation has the
    # real permission table to check against. See
    # services/plugins/runtime.py for why a single bad install can't take
    # the rest of startup down with it.
    async with AsyncSessionLocal() as db:
        reloaded = await reload_installed_plugins(db)
        await db.commit()
    print(f"[Umbrella Core] Reloaded {len(reloaded)} marketplace plugin capabilit{'y' if len(reloaded) == 1 else 'ies'}")

    print(f"[Umbrella Core] Ready — listening on {settings.app_host}:{settings.app_port}")

    # Background scheduler loop (Phase 4) — runs due Schedule rows through
    # the same registry.call() path every other adapter uses. Started here
    # rather than as a separate process so it shares this app's DB engine
    # and settings, and is cleanly stopped on shutdown via stop_event
    # rather than being killed mid-iteration.
    scheduler_stop_event = asyncio.Event()
    scheduler_task = asyncio.create_task(run_scheduler_loop(scheduler_stop_event))

    # Background server-metrics sampler (Phase 5) — periodically snapshots
    # PluginHeartbeat into ServerMetricSnapshot history, the time series
    # predictive crash prevention and NL operational queries read from.
    # Same lifecycle pattern as the scheduler loop above.
    sampler_stop_event = asyncio.Event()
    sampler_task = asyncio.create_task(run_sampler_loop(sampler_stop_event))

    # Background event dispatcher (Phase 7, Decision 1) — reads undispatched
    # rows from the events outbox table and fans them out to in-process
    # subscribers. Same lifecycle pattern as the two loops above.
    event_dispatcher_stop_event = asyncio.Event()
    event_dispatcher_task = asyncio.create_task(run_event_dispatcher_loop(event_dispatcher_stop_event))

    # Background log-flush loop (Phase 9, item 3) — drains the in-process
    # queue DBLogHandler feeds into models.log_entry.LogEntry rows. Same
    # lifecycle pattern as the loops above; attaching the handler to the
    # root logger happens once, here, rather than at import time, so tests
    # importing this module don't get every test's log output aggregated
    # into a real DB by default.
    logging.getLogger().addHandler(_db_log_handler)
    log_flush_stop_event = asyncio.Event()
    log_flush_task = asyncio.create_task(run_log_flush_loop(log_flush_stop_event))

    yield

    # --- Shutdown ---
    print("[Umbrella Core] Shutting down...")
    scheduler_stop_event.set()
    await scheduler_task
    sampler_stop_event.set()
    await sampler_task
    event_dispatcher_stop_event.set()
    await event_dispatcher_task
    logging.getLogger().removeHandler(_db_log_handler)
    log_flush_stop_event.set()
    await log_flush_task


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

# Register global error handlers
register_error_handlers(app)

# CORS — restrict to your dashboard domain in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if hasattr(settings, "cors_origins") else ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting (Phase 3) — per-client-IP, Redis-backed. Constructed from
# the same redis_url the rest of the app already uses; see
# services/rate_limit_service.py for the fixed-window algorithm and its
# documented trade-offs.
import redis.asyncio as _redis_asyncio  # local import: only this module needs it

_rate_limiter = RateLimiter(_redis_asyncio.from_url(settings.redis_url))
app.add_middleware(
    RateLimitMiddleware,
    rate_limiter=_rate_limiter,
    requests_per_window=settings.rate_limit_requests_per_window,
    window_seconds=settings.rate_limit_window_seconds,
    api_key_requests_per_window=settings.rate_limit_api_key_requests_per_window,
    api_key_window_seconds=settings.rate_limit_api_key_window_seconds,
)

# Tracing (Phase 9) — establishes trace/span context first, so every
# other middleware and the security-event records they may write during
# this request are stamped with the same trace_id.
app.add_middleware(TracingMiddleware)

# WAF-style hardening (Phase 9) — rejects obviously malicious requests
# (path traversal, SQLi/XSS patterns, oversized bodies) before they reach
# rate limiting or auth, so an attacker can't burn a legitimate request's
# worth of rate-limit budget or auth-failure noise on a payload that was
# never going anywhere near application logic.
app.add_middleware(WAFMiddleware)

# Metrics (Phase 9) — records every request; must be added before routers
# so it wraps them, mirroring RateLimitMiddleware's own ordering note.
app.add_middleware(MetricsMiddleware)

# Mount routers
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(logs_router)
app.include_router(security_router)
app.include_router(settings_router)
app.include_router(roles_router)
app.include_router(audit_router)
app.include_router(plugin_router)
app.include_router(players_router)
app.include_router(punishments_router)
app.include_router(appeals_router)
app.include_router(moderation_router)
app.include_router(auth_router)
app.include_router(bridge_router)
app.include_router(verification_router)
app.include_router(alt_detection_router)
app.include_router(analytics_router)
app.include_router(replay_router)
app.include_router(snapshot_router)
app.include_router(ai_tasks_router)
app.include_router(mc_commands_router)
app.include_router(translation_router)
app.include_router(ai_config_router)
app.include_router(anticheat_router)
app.include_router(dashboard_router)
app.include_router(server_control_router)
app.include_router(staff_router)
app.include_router(capabilities_router)
app.include_router(feature_flags_router)
app.include_router(hosting_console_ws_router)


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
