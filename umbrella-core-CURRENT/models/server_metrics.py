"""
models/server_metrics.py — Time-series history for predictive crash
prevention and natural-language operational queries (Phase 5's "novel
capabilities"), sampled periodically from PluginHeartbeat.

New infrastructure, not a Moo-assistant port: the roadmap's Phase 5 text
assumes "Phase 1's stats stream" already provides a TPS/MSPT/memory time
series to run anomaly detection over. It doesn't - models.plugin_heartbeat.
PluginHeartbeat is a single "latest known state" row per server_id,
overwritten on every heartbeat, with no history. Built here because,
unlike the Phase 2 event bus gap (deferred to Phase 6, which owns that
infrastructure generally), this one is narrowly scoped, single-purpose,
and explicitly required by Phase 5's own definition of done ("return real,
useful output against live data") - without some history, "anomaly
detection over a time series" has no series to detect anything from.

Two honest scope reductions from the roadmap's literal wording, not
silently glossed over:
1. No MSPT: Paper's heartbeat (see api/routers/plugin.py's HeartbeatRequest)
   only ever reported TPS, never MSPT - there's nowhere to get it from
   without changing the Minecraft plugin's own Java code, which is outside
   this repo.
2. No memory: DaemonClient.stats() has live container memory, but
   PluginHeartbeat.server_id is a free-form, plugin-self-reported string
   (defaults to "default") that predates the hosting domain and doesn't
   reliably map to models.hosting.Server.id - joining these would mean
   guessing at a correspondence between two different identity spaces
   that were never designed to line up. Scoped to what's actually
   reliable: TPS and online player count, both already in PluginHeartbeat
   itself, in its own identity space.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class ServerMetricSnapshot(Base):
    __tablename__ = "server_metric_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[str] = mapped_column(String(64), index=True)  # PluginHeartbeat.server_id's identity space
    tps: Mapped[float] = mapped_column(Float)
    online_count: Mapped[int] = mapped_column(Integer)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
