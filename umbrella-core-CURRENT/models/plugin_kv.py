"""
models/plugin_kv.py — PluginKvEntry: one row per (plugin_id, key), the
actual backing store for the `storage: "kv"` manifest mode
(`services/plugins/manifest.py::PluginManifest.storage`).

**Genuinely new as of Phase 10 step 7's Tier 2 work.** This table was
referenced by name in two places before this file existed — the manifest
schema's `storage: str = "kv"` default, and
`DASHBOARD-PLUGIN-UI-SCOPING.md`'s Tier 2 section ("writes the new value
into the plugin's own `kv` storage (Decision 2 from Part 1)") — but
`docs/adr/phase-7-notes-from-phase-5.md`'s "Open gap: plugins bringing
their own data/schema" section shows the three storage-shape options were
never actually decided between, only sketched. Checked the whole codebase
before writing this: no prior kv table, model, or service exists anywhere.
Tier 2's config-write capability is the first real consumer, so this file
picks Option 1 from that ADR ("generic key-value/document store, scoped
per plugin") — the option a manifest already defaults to — rather than
leaving Tier 2 with nowhere to actually write.

Deliberately global per plugin_id, not per-user (contrast
`models/dashboard_layout.py`, which is per-user by design) — a plugin's
config is one shared value the plugin's own logic reads on its next
invocation, not a per-viewer preference.

`value_json` stores whatever JSON-serializable value the key holds.
Tier 2 config fields are currently boolean-only
(`services/plugins/manifest.py::_ALLOWED_CONFIG_FIELD_TYPES`), so in
practice this holds `"true"`/`"false"` today, but the column itself
doesn't assume that — a future non-Tier-2 consumer of `storage: "kv"`
(a plugin's own sandboxed code reading/writing its own arbitrary keys)
isn't restricted to booleans, only Tier 2's *dashboard-facing config
toggle* capability is.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class PluginKvEntry(Base):
    __tablename__ = "plugin_kv_entries"
    __table_args__ = (
        UniqueConstraint("plugin_id", "key", name="uq_plugin_kv_entries_plugin_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    plugin_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False)

    # JSON-encoded value. Text, matching Setting.value and
    # DashboardLayout.layout_json's existing convention in this codebase
    # rather than a new JSON column type.
    value_json: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<PluginKvEntry plugin_id={self.plugin_id!r} key={self.key!r}>"
