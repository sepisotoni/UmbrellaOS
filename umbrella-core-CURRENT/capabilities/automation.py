"""
capabilities/automation.py — Phase 4's automation domain: scheduling any
existing capability to run on a cron expression.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from registry.context import CallContext
from registry.decorator import capability
from services.scheduler_service import SchedulerService


class CreateScheduleParams(BaseModel):
    name: str
    cron_expression: str
    capability_name: str
    capability_params: dict = Field(default_factory=dict)


class ScheduleResult(BaseModel):
    id: str
    name: str
    cron_expression: str
    capability_name: str
    capability_params: dict
    enabled: bool
    last_run_at: str | None
    last_run_status: str | None
    last_run_error: str | None

    @classmethod
    def from_model(cls, schedule) -> "ScheduleResult":
        return cls(
            id=schedule.id, name=schedule.name, cron_expression=schedule.cron_expression,
            capability_name=schedule.capability_name, capability_params=schedule.capability_params,
            enabled=schedule.enabled,
            last_run_at=schedule.last_run_at.isoformat() if schedule.last_run_at else None,
            last_run_status=schedule.last_run_status, last_run_error=schedule.last_run_error,
        )


@capability(
    name="automation.schedule.create",
    summary="Schedule any existing capability to run on a cron expression.",
    params_model=CreateScheduleParams,
    result_model=ScheduleResult,
    required_permission="automation.schedule.manage",
    destructive=False,
    audit_category="automation",
)
async def create_schedule(ctx: CallContext, params: CreateScheduleParams) -> ScheduleResult:
    schedule = await SchedulerService.create_schedule(
        ctx.db, params.name, params.cron_expression, params.capability_name, params.capability_params
    )
    return ScheduleResult.from_model(schedule)


class ListSchedulesParams(BaseModel):
    pass


@capability(
    name="automation.schedule.list",
    summary="List every scheduled automation task.",
    params_model=ListSchedulesParams,
    result_model=list[ScheduleResult],
    required_permission="automation.schedule.view",
    destructive=False,
    audited=False,
)
async def list_schedules(ctx: CallContext, params: ListSchedulesParams) -> list[ScheduleResult]:
    schedules = await SchedulerService.list_schedules(ctx.db)
    return [ScheduleResult.from_model(s) for s in schedules]


class ScheduleIDParams(BaseModel):
    schedule_id: str

    def audit_target(self) -> str:
        return self.schedule_id


class SetScheduleEnabledParams(BaseModel):
    schedule_id: str
    enabled: bool

    def audit_target(self) -> str:
        return self.schedule_id


@capability(
    name="automation.schedule.set_enabled",
    summary="Enable or disable a scheduled automation task.",
    params_model=SetScheduleEnabledParams,
    result_model=ScheduleResult,
    required_permission="automation.schedule.manage",
    destructive=False,
    audit_category="automation",
)
async def set_schedule_enabled(ctx: CallContext, params: SetScheduleEnabledParams) -> ScheduleResult:
    schedule = await SchedulerService.set_enabled(ctx.db, params.schedule_id, params.enabled)
    return ScheduleResult.from_model(schedule)


class DeleteScheduleResult(BaseModel):
    deleted: bool


@capability(
    name="automation.schedule.delete",
    summary="Delete a scheduled automation task permanently.",
    params_model=ScheduleIDParams,
    result_model=DeleteScheduleResult,
    required_permission="automation.schedule.manage",
    destructive=True,
    reversible=False,
    audit_category="automation",
)
async def delete_schedule(ctx: CallContext, params: ScheduleIDParams) -> DeleteScheduleResult:
    await SchedulerService.delete_schedule(ctx.db, params.schedule_id)
    return DeleteScheduleResult(deleted=True)
