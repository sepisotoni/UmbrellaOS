"""
capabilities/dashboard_layout.py — Phase 10 step 6: custom per-page
dashboard layouts. Lets a staff member reorder/hide the widgets on a
customizable dashboard page and have that arrangement persist across
sessions, per-user (not shared, not a role setting).

Same personal-setting shape as capabilities/identity.py's `identity.mfa.*`
capabilities: always acts on the calling staff member's own row, never a
target user_id param, `required_permission=None` (any authenticated staff
actor may manage their own layout — this is self-scoped preference data,
not an elevated grant), and the admin-key bootstrap tier is rejected the
same way MFA rejects it (`_current_staff_user` below is the identical
pattern, kept local rather than imported cross-module per this codebase's
existing per-file convention — see identity.py's own copy for precedent).

`page_id` is checked against the explicit allow-list in
`services/dashboard_layout/pages.py` — customizing a page that either
doesn't exist or has no widget concept (e.g. "topology") is a 400, not a
silently-accepted row nobody will ever read back.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy import select

from api.middleware.errors import AppException
from models.user import User
from registry.context import CallContext
from registry.decorator import capability
from services.dashboard_layout.pages import CUSTOMIZABLE_PAGES, is_customizable
from services.dashboard_layout.service import DashboardLayoutService


class DashboardLayoutError(AppException):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, "DASHBOARD_LAYOUT_ERROR", status_code)


async def _current_staff_user(ctx: CallContext) -> User:
    """Identical shape to capabilities/identity.py::_current_staff_user —
    a dashboard layout is exactly as personal as an MFA enrollment: there
    is no "set someone else's layout" capability, and the admin-key tier
    (no underlying User row) has nothing to attach one to."""
    if ctx.actor_type != "staff":
        raise DashboardLayoutError("dashboard layouts apply to staff accounts only", 400)
    result = await ctx.db.execute(select(User).where(User.discord_id == ctx.actor_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise DashboardLayoutError("no matching user account found for the current session", 404)
    return user


def _require_customizable(page_id: str) -> None:
    if not is_customizable(page_id):
        allowed = ", ".join(sorted(CUSTOMIZABLE_PAGES))
        raise DashboardLayoutError(
            f"'{page_id}' is not a customizable page (allowed: {allowed})", 400
        )


class LayoutWidgetEntry(BaseModel):
    # "{plugin_id}:{capability_name}" — the same composite key
    # umbrella-dashboard/components/widgets/widget-grid.tsx already uses as
    # its React `key`, so the dashboard side has no new identity concept to
    # invent for matching a saved entry back to a live DashboardSlotResult.
    widget_key: str
    visible: bool = True


# --------------------------------------------------------------------------
# dashboard.layout.get
# --------------------------------------------------------------------------


class GetDashboardLayoutParams(BaseModel):
    page_id: str


class DashboardLayoutResult(BaseModel):
    page_id: str
    # None = no saved layout for this user/page — the dashboard falls back
    # to the page's default arrangement (services/dashboard_layout/pages.py).
    # Distinct from an empty list, which would mean "saved layout with
    # every widget explicitly hidden."
    widgets: list[LayoutWidgetEntry] | None = None


@capability(
    name="dashboard.layout.get",
    summary="Get the calling user's saved widget layout for a customizable dashboard page, if any.",
    params_model=GetDashboardLayoutParams,
    result_model=DashboardLayoutResult,
    required_permission=None,
    destructive=False,
    audited=False,
)
async def get_layout(ctx: CallContext, params: GetDashboardLayoutParams) -> DashboardLayoutResult:
    _require_customizable(params.page_id)
    user = await _current_staff_user(ctx)
    layout = await DashboardLayoutService.get(ctx.db, user_id=user.id, page_id=params.page_id)
    if layout is None:
        return DashboardLayoutResult(page_id=params.page_id, widgets=None)
    widgets = [LayoutWidgetEntry(**w) for w in DashboardLayoutService.parse_widgets(layout)]
    return DashboardLayoutResult(page_id=params.page_id, widgets=widgets)


# --------------------------------------------------------------------------
# dashboard.layout.set
# --------------------------------------------------------------------------


class SetDashboardLayoutParams(BaseModel):
    page_id: str
    widgets: list[LayoutWidgetEntry] = Field(default_factory=list)

    def audit_target(self) -> str:
        return self.page_id


@capability(
    name="dashboard.layout.set",
    summary="Save the calling user's widget order/visibility for a customizable dashboard page.",
    params_model=SetDashboardLayoutParams,
    result_model=DashboardLayoutResult,
    required_permission=None,
    destructive=False,
    audit_category="dashboard",
)
async def set_layout(ctx: CallContext, params: SetDashboardLayoutParams) -> DashboardLayoutResult:
    _require_customizable(params.page_id)
    user = await _current_staff_user(ctx)
    widgets_payload = [w.model_dump() for w in params.widgets]
    await DashboardLayoutService.set(
        ctx.db, user_id=user.id, page_id=params.page_id, widgets=widgets_payload
    )
    return DashboardLayoutResult(page_id=params.page_id, widgets=params.widgets)


# --------------------------------------------------------------------------
# dashboard.layout.reset
# --------------------------------------------------------------------------


class ResetDashboardLayoutParams(BaseModel):
    page_id: str

    def audit_target(self) -> str:
        return self.page_id


class ResetDashboardLayoutResult(BaseModel):
    reset: bool


@capability(
    name="dashboard.layout.reset",
    summary="Delete the calling user's saved layout for a page, reverting it to the default arrangement.",
    params_model=ResetDashboardLayoutParams,
    result_model=ResetDashboardLayoutResult,
    required_permission=None,
    destructive=True,
    reversible=True,  # the user can always re-customize and save again
    audit_category="dashboard",
)
async def reset_layout(
    ctx: CallContext, params: ResetDashboardLayoutParams
) -> ResetDashboardLayoutResult:
    _require_customizable(params.page_id)
    user = await _current_staff_user(ctx)
    existed = await DashboardLayoutService.reset(ctx.db, user_id=user.id, page_id=params.page_id)
    return ResetDashboardLayoutResult(reset=existed)
