"""
models/events.py — Event: the durable outbox table for Phase 7's event bus
(handoff-to-new-session-phase7-START.md, Decision 1).

Any domain that needs to emit an event writes a row here in the SAME
db session/transaction as the state change it's recording — that's the
entire point of the outbox pattern: the event can never be dropped between
the state change committing and the event being recorded, because they
share one transaction (see services/events/bus.py's EventBus.publish,
which never calls db.commit() itself, exactly like every other
repository-style write in this codebase - the request/capability-call
lifecycle in database/engine.py's get_db() commits everything together).

Column set per the locked decision, plus one addition:
- id, topic, payload_json, created_at, dispatched_at, attempts, last_error
  are exactly what the decision doc specifies.
- `next_attempt_at` is an addition beyond that list. It's required to
  actually implement "retries with backoff via attempts" rather than
  faking it: without a timestamp recording when a row is safe to retry,
  "attempts" alone can't express backoff, only a count. Flagged here
  rather than silently added — this is an implementation necessity, not a
  reopening of the outbox-vs-broker decision itself.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class Event(Base):
    """One row per emitted event. `payload_json` is a JSON-encoded string
    (not a native JSON column) matching how every other free-form payload
    field in this codebase is stored — see e.g. models.ai.AIDecisionLog —
    keeping this portable across the Postgres/SQLite split the test suite
    already relies on (see database/engine.py, tests/conftest.py)."""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic: Mapped[str] = mapped_column(String(150), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # See module docstring: not in the original decision's field list,
    # added because backoff cannot be enforced without it.
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
