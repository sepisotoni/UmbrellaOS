"""
services/operational_intelligence/sampler_loop.py — Background task that
periodically snapshots PluginHeartbeat into ServerMetricSnapshot history,
wired into main.py's app lifespan. Mirrors services/scheduler_loop.py's
exact structure - same reasoning for each choice, not reinvented here.
"""
import asyncio
import logging

from config import get_settings
from database import AsyncSessionLocal
from services.operational_intelligence.metrics import purge_old_snapshots, sample_all_servers

logger = logging.getLogger(__name__)

# How often the retention sweep runs, relative to the sample interval -
# every 60th sample tick is frequent enough that retention never lags far
# behind server_metric_retention_hours, without running a DELETE on every
# single tick when nothing has necessarily expired yet.
_PURGE_EVERY_N_TICKS = 60


async def run_sampler_loop(stop_event: asyncio.Event) -> None:
    """Runs until stop_event is set. Each iteration opens its own DB
    session, matching run_scheduler_loop's rationale exactly."""
    tick = 0
    while not stop_event.is_set():
        tick += 1
        try:
            async with AsyncSessionLocal() as db:
                count = await sample_all_servers(db)
                if tick % _PURGE_EVERY_N_TICKS == 0:
                    purged = await purge_old_snapshots(db)
                    if purged:
                        logger.info("server metrics: purged %d expired snapshot(s)", purged)
                await db.commit()
                if count:
                    logger.debug("server metrics: recorded %d snapshot(s)", count)
        except Exception:
            # Same reasoning as run_scheduler_loop: a failure here (e.g. a
            # DB connectivity blip) must not kill the background task
            # permanently - the next tick tries again.
            logger.exception("server metrics: error sampling, will retry next interval")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=get_settings().server_metric_sample_interval_seconds)
        except asyncio.TimeoutError:
            pass  # normal case: timed out waiting, loop again
