"""
services/scheduler_service.py — Cron-driven capability invocation.

A Schedule names a capability and fixed params; this service's job is
deciding when a schedule is due and firing it through the exact same
`registry.call()` path every other adapter uses (see registry/registry.py)
— scheduled execution is not a separate code path with its own
permission/audit handling, it's another caller of the same one.
"""
from datetime import datetime, timezone

from croniter import CroniterBadCronError, croniter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.errors import AppException
from models.automation import Schedule
from registry.context import CallContext
from registry.registry import CapabilityNotFoundError, registry


class ScheduleError(AppException):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, "SCHEDULE_ERROR", status_code)


def _validate_cron(cron_expression: str) -> None:
    try:
        croniter(cron_expression)
    except (CroniterBadCronError, ValueError) as exc:
        raise ScheduleError(f"invalid cron expression {cron_expression!r}: {exc}") from exc


class SchedulerService:
    @staticmethod
    async def create_schedule(
        db: AsyncSession,
        name: str,
        cron_expression: str,
        capability_name: str,
        capability_params: dict | None = None,
    ) -> Schedule:
        _validate_cron(cron_expression)
        try:
            registry.get(capability_name)
        except CapabilityNotFoundError as exc:
            raise ScheduleError(f"unknown capability {capability_name!r}") from exc

        schedule = Schedule(
            name=name,
            cron_expression=cron_expression,
            capability_name=capability_name,
            capability_params=capability_params or {},
        )
        db.add(schedule)
        await db.flush()
        return schedule

    @staticmethod
    async def list_schedules(db: AsyncSession) -> list[Schedule]:
        result = await db.execute(select(Schedule).order_by(Schedule.name))
        return list(result.scalars().all())

    @staticmethod
    async def get_schedule(db: AsyncSession, schedule_id: str) -> Schedule:
        schedule = await db.get(Schedule, schedule_id)
        if schedule is None:
            raise ScheduleError(f"no schedule with id {schedule_id!r}", 404)
        return schedule

    @staticmethod
    async def set_enabled(db: AsyncSession, schedule_id: str, enabled: bool) -> Schedule:
        schedule = await SchedulerService.get_schedule(db, schedule_id)
        schedule.enabled = enabled
        await db.flush()
        return schedule

    @staticmethod
    async def delete_schedule(db: AsyncSession, schedule_id: str) -> None:
        schedule = await SchedulerService.get_schedule(db, schedule_id)
        await db.delete(schedule)
        await db.flush()

    @staticmethod
    def is_due(schedule: Schedule, now: datetime) -> bool:
        """
        A schedule is due if its cron expression's most recent scheduled
        fire time at or before `now` is after `last_run_at` (or it has
        never run). This tolerates the scheduler's own polling interval —
        a schedule due at 3:00:00 fires the first time the poll loop runs
        at or after 3:00:00, whatever that loop's own cadence is, rather
        than needing to align exactly with cron's tick.
        """
        if not schedule.enabled:
            return False
        cron = croniter(schedule.cron_expression, now)
        most_recent_scheduled_fire = cron.get_prev(datetime)
        if schedule.last_run_at is None:
            return True
        last_run = schedule.last_run_at
        if last_run.tzinfo is None:
            last_run = last_run.replace(tzinfo=timezone.utc)
        if most_recent_scheduled_fire.tzinfo is None:
            most_recent_scheduled_fire = most_recent_scheduled_fire.replace(tzinfo=timezone.utc)
        return most_recent_scheduled_fire > last_run

    @staticmethod
    async def run_schedule(db: AsyncSession, schedule: Schedule) -> None:
        """
        Fire one schedule through the real Capability Registry call path.
        Always records last_run_at/status/error, whether the capability
        call succeeds or raises — a schedule that keeps silently failing
        with no visible record would be strictly worse than one that fails
        loudly and visibly.
        """
        ctx = CallContext.from_system(db)
        schedule.last_run_at = datetime.now(timezone.utc)
        try:
            await registry.call(schedule.capability_name, ctx, schedule.capability_params)
        except Exception as exc:  # noqa: BLE001 - any capability failure must be recorded, not just expected ones
            schedule.last_run_status = "failed"
            schedule.last_run_error = str(exc)
            await db.flush()
            raise
        schedule.last_run_status = "success"
        schedule.last_run_error = None
        await db.flush()

    @staticmethod
    async def run_due_schedules(db: AsyncSession, now: datetime | None = None) -> list[str]:
        """
        Run every currently-due, enabled schedule. Returns the list of
        schedule IDs that were run (whether they succeeded or failed) —
        used by the background loop (main.py's wiring) for logging, and
        directly by tests to assert on what actually fired. One schedule's
        failure does not stop the others from running.
        """
        now = now or datetime.now(timezone.utc)
        schedules = await SchedulerService.list_schedules(db)
        ran: list[str] = []
        for schedule in schedules:
            if SchedulerService.is_due(schedule, now):
                ran.append(schedule.id)
                try:
                    await SchedulerService.run_schedule(db, schedule)
                except Exception:
                    continue  # already recorded on the schedule itself; move on to the next one
        return ran
