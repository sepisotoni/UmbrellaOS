"""
tests/test_scheduler_loop.py — Tests for services/scheduler_loop.py: proves
the loop actually runs an iteration and stops cleanly when signaled, not
just that it's syntactically plausible.
"""
import asyncio

import pytest

import capabilities  # noqa: F401 - registers capabilities the loop's schedules reference
from services.scheduler_loop import run_scheduler_loop


@pytest.mark.asyncio
async def test_loop_stops_promptly_when_stop_event_is_set():
    stop_event = asyncio.Event()
    task = asyncio.create_task(run_scheduler_loop(stop_event, poll_interval_seconds=60))

    await asyncio.sleep(0.05)  # let the loop begin its first iteration
    stop_event.set()

    await asyncio.wait_for(task, timeout=2.0)  # must not still be sleeping the full 60s interval
    assert task.done()


@pytest.mark.asyncio
async def test_loop_runs_at_least_one_iteration_before_stopping(monkeypatch):
    calls = []

    async def fake_run_due_schedules(db, now=None):
        calls.append(True)
        return []

    import services.scheduler_service as scheduler_service_module

    monkeypatch.setattr(
        scheduler_service_module.SchedulerService, "run_due_schedules", staticmethod(fake_run_due_schedules)
    )

    stop_event = asyncio.Event()
    task = asyncio.create_task(run_scheduler_loop(stop_event, poll_interval_seconds=60))
    await asyncio.sleep(0.1)
    stop_event.set()
    await asyncio.wait_for(task, timeout=2.0)

    assert len(calls) >= 1
