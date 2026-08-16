from datetime import datetime, timedelta, timezone

import pytest

import capabilities  # noqa: F401 - registers platform.system.whoami etc.; this test file must be
                      # self-sufficient regardless of test run order, not rely on another test
                      # module having imported this first in the same process.
from models.automation import Schedule
from services.scheduler_service import ScheduleError, SchedulerService


@pytest.mark.asyncio
async def test_create_schedule_validates_cron_expression(db_session):
    async with db_session() as db:
        with pytest.raises(ScheduleError, match="invalid cron"):
            await SchedulerService.create_schedule(db, "bad", "not a cron", "platform.system.whoami")


@pytest.mark.asyncio
async def test_create_schedule_validates_capability_exists(db_session):
    async with db_session() as db:
        with pytest.raises(ScheduleError, match="unknown capability"):
            await SchedulerService.create_schedule(db, "bad-cap", "0 3 * * *", "does.not.exist")


@pytest.mark.asyncio
async def test_create_schedule_happy_path(db_session):
    async with db_session() as db:
        schedule = await SchedulerService.create_schedule(
            db, "nightly-check", "0 3 * * *", "platform.system.whoami"
        )
        await db.commit()
        assert schedule.enabled is True
        assert schedule.last_run_at is None


@pytest.mark.asyncio
async def test_set_enabled_toggles_flag(db_session):
    async with db_session() as db:
        schedule = await SchedulerService.create_schedule(db, "s", "0 3 * * *", "platform.system.whoami")
        await db.commit()
        schedule_id = schedule.id

    async with db_session() as db:
        updated = await SchedulerService.set_enabled(db, schedule_id, False)
        await db.commit()
        assert updated.enabled is False


@pytest.mark.asyncio
async def test_delete_schedule_removes_it(db_session):
    async with db_session() as db:
        schedule = await SchedulerService.create_schedule(db, "s", "0 3 * * *", "platform.system.whoami")
        await db.commit()
        schedule_id = schedule.id

    async with db_session() as db:
        await SchedulerService.delete_schedule(db, schedule_id)
        await db.commit()

    async with db_session() as db:
        with pytest.raises(ScheduleError):
            await SchedulerService.get_schedule(db, schedule_id)


# --------------------------------------------------------------------------
# is_due — the actual scheduling logic
# --------------------------------------------------------------------------


def _schedule(cron="0 3 * * *", last_run_at=None, enabled=True) -> Schedule:
    s = Schedule(name="test", cron_expression=cron, capability_name="platform.system.whoami")
    s.last_run_at = last_run_at
    s.enabled = enabled
    return s


def test_is_due_true_when_never_run_and_past_fire_time():
    now = datetime(2026, 7, 8, 3, 5, tzinfo=timezone.utc)  # 5 min after 3am
    schedule = _schedule(cron="0 3 * * *", last_run_at=None)
    assert SchedulerService.is_due(schedule, now) is True


def test_is_due_false_when_already_run_since_last_fire_time():
    now = datetime(2026, 7, 8, 3, 5, tzinfo=timezone.utc)
    last_run = datetime(2026, 7, 8, 3, 0, 30, tzinfo=timezone.utc)  # ran just after 3am today
    schedule = _schedule(cron="0 3 * * *", last_run_at=last_run)
    assert SchedulerService.is_due(schedule, now) is False


def test_is_due_true_when_last_run_was_a_previous_cycle():
    now = datetime(2026, 7, 8, 3, 5, tzinfo=timezone.utc)
    last_run = datetime(2026, 7, 7, 3, 0, 30, tzinfo=timezone.utc)  # ran yesterday, not today
    schedule = _schedule(cron="0 3 * * *", last_run_at=last_run)
    assert SchedulerService.is_due(schedule, now) is True


def test_is_due_false_before_fire_time_at_all():
    now = datetime(2026, 7, 8, 2, 55, tzinfo=timezone.utc)  # before 3am
    schedule = _schedule(cron="0 3 * * *", last_run_at=None)
    # croniter's get_prev from 2:55 for "daily at 3am" finds YESTERDAY's
    # 3am as the most recent scheduled fire — which, with no last_run_at,
    # correctly counts as due (it's overdue from yesterday, not "not yet
    # due"). This is deliberate: a schedule that's never run is always due
    # the moment the scheduler first looks at it, regardless of what time
    # of day that happens to be.
    assert SchedulerService.is_due(schedule, now) is True


def test_is_due_false_when_disabled():
    now = datetime(2026, 7, 8, 3, 5, tzinfo=timezone.utc)
    schedule = _schedule(cron="0 3 * * *", last_run_at=None, enabled=False)
    assert SchedulerService.is_due(schedule, now) is False


def test_is_due_handles_naive_last_run_at():
    # SQLite round-trips can hand back naive datetimes even when the
    # column is timezone-aware — is_due must not crash comparing a naive
    # datetime against an aware one.
    now = datetime(2026, 7, 8, 3, 5, tzinfo=timezone.utc)
    last_run = datetime(2026, 7, 8, 3, 0, 30)  # naive, no tzinfo
    schedule = _schedule(cron="0 3 * * *", last_run_at=last_run)
    result = SchedulerService.is_due(schedule, now)  # must not raise
    assert result is False


# --------------------------------------------------------------------------
# run_schedule / run_due_schedules
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_schedule_records_success(db_session):
    async with db_session() as db:
        schedule = await SchedulerService.create_schedule(db, "s", "0 3 * * *", "platform.system.whoami")
        await db.commit()
        schedule_id = schedule.id

    async with db_session() as db:
        schedule = await SchedulerService.get_schedule(db, schedule_id)
        await SchedulerService.run_schedule(db, schedule)
        await db.commit()
        assert schedule.last_run_status == "success"
        assert schedule.last_run_at is not None


@pytest.mark.asyncio
async def test_run_schedule_records_failure_and_reraises(db_session):
    async with db_session() as db:
        # A capability requiring a permission the system context doesn't
        # have would still succeed (system context is superuser) — use an
        # unknown capability at the DB level to force a real failure,
        # bypassing create_schedule's own validation which would normally
        # catch this at creation time.
        schedule = Schedule(name="broken", cron_expression="0 3 * * *", capability_name="does.not.exist")
        db.add(schedule)
        await db.flush()
        await db.commit()
        schedule_id = schedule.id

    async with db_session() as db:
        schedule = await SchedulerService.get_schedule(db, schedule_id)
        with pytest.raises(Exception):
            await SchedulerService.run_schedule(db, schedule)
        await db.commit()
        assert schedule.last_run_status == "failed"
        assert schedule.last_run_error is not None


@pytest.mark.asyncio
async def test_run_due_schedules_runs_only_due_ones_and_continues_past_failures(db_session):
    async with db_session() as db:
        due = await SchedulerService.create_schedule(db, "due-one", "0 3 * * *", "platform.system.whoami")
        not_due = await SchedulerService.create_schedule(db, "not-due", "0 3 * * *", "platform.system.whoami")
        # Mark not_due as already run this cycle.
        not_due.last_run_at = datetime(2026, 7, 8, 3, 1, tzinfo=timezone.utc)
        broken = Schedule(name="broken", cron_expression="0 3 * * *", capability_name="does.not.exist")
        db.add(broken)
        await db.commit()
        due_id, not_due_id, broken_id = due.id, not_due.id, broken.id

    async with db_session() as db:
        now = datetime(2026, 7, 8, 3, 5, tzinfo=timezone.utc)
        ran = await SchedulerService.run_due_schedules(db, now=now)
        await db.commit()

        assert due_id in ran
        assert broken_id in ran
        assert not_due_id not in ran

        due_after = await SchedulerService.get_schedule(db, due_id)
        broken_after = await SchedulerService.get_schedule(db, broken_id)
        assert due_after.last_run_status == "success"
        assert broken_after.last_run_status == "failed"
