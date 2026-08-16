"""
services/plugin_kv/service.py — plain CRUD for PluginKvEntry rows, scoped
to a single (plugin_id, key) pair. Mirrors
services/dashboard_layout/service.py's split (trivial CRUD lives here,
called by the capability layer) and its upsert-on-set semantics.

Every method takes `plugin_id` explicitly rather than resolving it from
a CallContext — same registry-agnostic boundary DashboardLayoutService
keeps. Key-vocabulary validation (is this key one the plugin actually
declared in `config_fields`?) belongs at the capability layer
(`capabilities/plugin_config.py`), not here — same separation
DashboardLayoutService keeps for its own page_id allow-list check.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.plugin_kv import PluginKvEntry


class PluginKvService:
    @staticmethod
    async def get(db: AsyncSession, *, plugin_id: str, key: str) -> PluginKvEntry | None:
        result = await db.execute(
            select(PluginKvEntry).where(
                PluginKvEntry.plugin_id == plugin_id, PluginKvEntry.key == key
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(db: AsyncSession, *, plugin_id: str) -> list[PluginKvEntry]:
        result = await db.execute(
            select(PluginKvEntry).where(PluginKvEntry.plugin_id == plugin_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def set(db: AsyncSession, *, plugin_id: str, key: str, value: Any) -> PluginKvEntry:
        """Upsert: one row per (plugin_id, key), enforced by the table's
        unique constraint. Not an audit trail — the capability call itself
        is audited (audited=True on the config.set CapabilitySpec), this
        table only ever holds current state."""
        value_json = json.dumps(value)
        existing = await PluginKvService.get(db, plugin_id=plugin_id, key=key)
        if existing is not None:
            existing.value_json = value_json
            await db.flush()
            return existing

        entry = PluginKvEntry(plugin_id=plugin_id, key=key, value_json=value_json)
        db.add(entry)
        await db.flush()
        return entry

    @staticmethod
    def parse_value(entry: PluginKvEntry) -> Any:
        return json.loads(entry.value_json)
