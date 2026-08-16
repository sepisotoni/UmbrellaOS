"""
services/scheduler_loop.py — The background task that periodically checks
for due schedules and runs them, wired into main.py's app lifespan.

Kept as a thin wrapper around SchedulerService.run_due_schedules (already
fully tested on its own, tests/test_scheduler_service.py) — this module's
own job is just "loop, with a way to stop," which is deliberately the only
thing it's responsible for getting right.
"""
import asyncio
import logging

from database import AsyncSessionLocal
from services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL_SECONDS = 30


async def run_scheduler_loop(
    stop_event: asyncio.Event, poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS
) -> None:
    """
    Runs until stop_event is set. Each iteration opens its own DB session
    (not one held across the whole loop's lifetime) so a long-lived
    session doesn't accumulate stale state across many poll cycles.
    """
    while not stop_event.is_set():
        try:
            async with AsyncSessionLocal() as db:
                ran = await SchedulerService.run_due_schedules(db)
                await db.commit()
                if ran:
                    logger.info("scheduler: ran %d due schedule(s): %s", len(ran), ran)
        except Exception:
            # A failure in the loop itself (e.g. a DB connectivity blip)
            # must not kill the background task permanently — the next
            # iteration tries again. Per-schedule failures are already
            # caught and recorded individually inside run_due_schedules;
            # this is a further outer guard against the polling
            # infrastructure itself failing.
            logger.exception("scheduler: error running due schedules, will retry next interval")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=poll_interval_seconds)
        except asyncio.TimeoutError:
            pass  # normal case: timed out waiting, loop again
