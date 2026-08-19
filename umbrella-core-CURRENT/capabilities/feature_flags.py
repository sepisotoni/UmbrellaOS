"""
capabilities/feature_flags.py — Capability-registry surface for feature flags.

Four capabilities:
    feature_flags.get     — read a flag's state (permission: feature_flags.view)
    feature_flags.set     — create/update a flag (permission: feature_flags.manage)
    feature_flags.list    — list all flags      (permission: feature_flags.view)
    feature_flags.delete  — delete a flag       (permission: feature_flags.manage, destructive)

All real work is delegated to services/feature_flag_service.py. This module
only translates between the capability-registry calling convention
(CallContext + Pydantic params) and the service layer.
"""
from __future__ import annotations

from pydantic import BaseModel

from registry.context import CallContext
from registry.decorator import capability
import services.feature_flag_service as svc


# ---------------------------------------------------------------------------
# Shared result shape
# ---------------------------------------------------------------------------


class FeatureFlagResult(BaseModel):
    id: str
    name: str
    enabled: bool
    description: str

    @classmethod
    def from_model(cls, flag) -> "FeatureFlagResult":
        return cls(
            id=flag.id,
            name=flag.name,
            enabled=flag.enabled,
            description=flag.description,
        )


# ---------------------------------------------------------------------------
# feature_flags.get
# ---------------------------------------------------------------------------


class GetFlagParams(BaseModel):
    name: str


class GetFlagResult(BaseModel):
    name: str
    enabled: bool


@capability(
    name="feature_flags.get",
    summary="Return the enabled state of a named feature flag (False if not found).",
    params_model=GetFlagParams,
    result_model=GetFlagResult,
    required_permission="feature_flags.view",
    destructive=False,
    audited=False,
)
async def get_flag(ctx: CallContext, params: GetFlagParams) -> GetFlagResult:
    enabled = await svc.get_flag(ctx.db, params.name)
    return GetFlagResult(name=params.name, enabled=enabled)


# ---------------------------------------------------------------------------
# feature_flags.set
# ---------------------------------------------------------------------------


class SetFlagParams(BaseModel):
    name: str
    enabled: bool
    description: str = ""

    def audit_target(self) -> str:
        return self.name


@capability(
    name="feature_flags.set",
    summary="Create or update a feature flag by name (upsert).",
    params_model=SetFlagParams,
    result_model=FeatureFlagResult,
    required_permission="feature_flags.manage",
    destructive=False,
    audit_category="feature_flags",
)
async def set_flag(ctx: CallContext, params: SetFlagParams) -> FeatureFlagResult:
    flag = await svc.set_flag(ctx.db, params.name, params.enabled, params.description)
    return FeatureFlagResult.from_model(flag)


# ---------------------------------------------------------------------------
# feature_flags.list
# ---------------------------------------------------------------------------


class ListFlagsParams(BaseModel):
    pass


@capability(
    name="feature_flags.list",
    summary="List all feature flags, ordered by name.",
    params_model=ListFlagsParams,
    result_model=list[FeatureFlagResult],
    required_permission="feature_flags.view",
    destructive=False,
    audited=False,
)
async def list_flags(ctx: CallContext, params: ListFlagsParams) -> list[FeatureFlagResult]:
    flags = await svc.list_flags(ctx.db)
    return [FeatureFlagResult.from_model(f) for f in flags]


# ---------------------------------------------------------------------------
# feature_flags.delete
# ---------------------------------------------------------------------------


class DeleteFlagParams(BaseModel):
    name: str

    def audit_target(self) -> str:
        return self.name


class DeleteFlagResult(BaseModel):
    deleted: bool


@capability(
    name="feature_flags.delete",
    summary="Permanently delete a feature flag by name.",
    params_model=DeleteFlagParams,
    result_model=DeleteFlagResult,
    required_permission="feature_flags.manage",
    destructive=True,
    reversible=False,
    audit_category="feature_flags",
)
async def delete_flag(ctx: CallContext, params: DeleteFlagParams) -> DeleteFlagResult:
    existed = await svc.delete_flag(ctx.db, params.name)
    return DeleteFlagResult(deleted=existed)
