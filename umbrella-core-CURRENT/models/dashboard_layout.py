"""
models/dashboard_layout.py — DashboardLayout: one row per (user, page)
holding that user's saved widget arrangement for a customizable dashboard
page (Phase 10 step 6, see docs/design/phase10-decision2-config-write-capability-shape.md's
sibling doc for the step 6 handback and PHASE10-BUILD-KICKOFF-HANDOFF.md item 6).

Deliberately per-user, not per-role or global: this is workspace-layout
preference (widget order, which widgets are hidden), not a permission or
a plugin config value — no relationship to Decision 2's config-write
capability shape, which is a different concept (a plugin's own settings)
entirely.

`page_id` is validated against an explicit allow-list
(`services/dashboard_layout/pages.py::CUSTOMIZABLE_PAGES`) at the
capability layer, not here — this table has no opinion on which pages
exist, it just stores whatever page_id it's given, same separation of
concerns as Setting.key not validating against a fixed list either.

`layout_json` stores a JSON-encoded list of
`{"widget_key": str, "visible": bool}` entries — see
capabilities/dashboard_layout.py::LayoutWidgetEntry for the schema that
actually gets serialized here. A widget_key not present in a saved layout
(e.g. a plugin installed after the layout was last saved) is treated as
"append at the end, visible" by the resolution logic in
lib/dashboard-layout.ts on the dashboard side — this table only stores
what was explicitly customized, never a full snapshot that would need
migrating every time a plugin is installed or removed.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.engine import Base
from models.user import User  # noqa: F401 - resolves the "User" forward reference below


class DashboardLayout(Base):
    __tablename__ = "dashboard_layouts"
    __table_args__ = (
        UniqueConstraint("user_id", "page_id", name="uq_dashboard_layouts_user_page"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # One of services/dashboard_layout/pages.py::CUSTOMIZABLE_PAGES's keys.
    # Not a DB-level enum/FK — see module docstring for why validation lives
    # at the capability layer instead.
    page_id: Mapped[str] = mapped_column(String(64), nullable=False)

    # JSON-encoded list[LayoutWidgetEntry]. Text, not a JSON column type,
    # matching Setting.value and every other JSON-ish column in this
    # codebase (models/webhook.py, models/ai_config.py) — kept consistent
    # rather than introducing a new column-type convention for one table.
    layout_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<DashboardLayout user_id={self.user_id!r} page_id={self.page_id!r}>"
