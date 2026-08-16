"""
services/dashboard_layout/service.py — plain CRUD for DashboardLayout rows,
scoped to a single (user_id, page_id) pair. Mirrors
services/webhooks/service.py::WebhookService's split of "trivial CRUD lives
in the service, called by the capability layer" — there's no delivery-style
side effect here to warrant a second class the way WebhookService has
WebhookDeliveryService.

Every method takes `user_id` as an explicit argument rather than reading it
off a CallContext — this file has no knowledge of the registry, same
boundary WebhookService keeps. capabilities/dashboard_layout.py resolves
"which user" via `_current_staff_user` and passes `user.id` in; that
resolution (and the page_id allow-list check) belongs at the capability
layer, not here, same reasoning as `page_id` validation living outside
models/dashboard_layout.py.
"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.dashboard_layout import DashboardLayout


class DashboardLayoutService:
    @staticmethod
    async def get(db: AsyncSession, *, user_id: str, page_id: str) -> DashboardLayout | None:
        result = await db.execute(
            select(DashboardLayout).where(
                DashboardLayout.user_id == user_id, DashboardLayout.page_id == page_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def set(
        db: AsyncSession, *, user_id: str, page_id: str, widgets: list[dict]
    ) -> DashboardLayout:
        """Upsert: one row per (user_id, page_id), enforced by the table's
        unique constraint — a second save for the same page replaces the
        first rather than accumulating history. Layout is a current-state
        preference, not an audit trail (the capability call itself is
        still audited, per the usual audit_category mechanism)."""
        layout_json = json.dumps(widgets)
        existing = await DashboardLayoutService.get(db, user_id=user_id, page_id=page_id)
        if existing is not None:
            existing.layout_json = layout_json
            await db.flush()
            return existing

        layout = DashboardLayout(user_id=user_id, page_id=page_id, layout_json=layout_json)
        db.add(layout)
        await db.flush()
        return layout

    @staticmethod
    async def reset(db: AsyncSession, *, user_id: str, page_id: str) -> bool:
        """Deletes the saved layout, reverting the page to its default
        arrangement (see services/dashboard_layout/pages.py). Returns
        whether a row actually existed to delete — resetting an
        already-default page is not an error, just a no-op."""
        existing = await DashboardLayoutService.get(db, user_id=user_id, page_id=page_id)
        if existing is None:
            return False
        await db.delete(existing)
        await db.flush()
        return True

    @staticmethod
    def parse_widgets(layout: DashboardLayout) -> list[dict]:
        return json.loads(layout.layout_json)
