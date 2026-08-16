"""
registry/audit.py — Writes capability invocations into the existing
AuditLog table.

Deliberately the only place the Capability Registry writes an audit row, and
deliberately reuses `models.audit_log.AuditLog` rather than introducing a
second, parallel audit schema for registry-originated actions. Prior to
Phase 0, each service wrote its own AuditLog row by hand at the point of
action (see the pre-existing `api/routers/*.py` for examples) — that pattern
is not removed by Phase 0, but every *new* capability going forward gets this
for free instead of hand-rolling it, which is the concrete fix for audit
logging having been duplicated ad hoc per service.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.audit_log import AuditLog


async def record_audit_event(
    db: AsyncSession,
    actor: str,
    actor_type: str,
    action: str,
    target: str | None,
    details: dict[str, Any],
    category: str,
) -> AuditLog:
    """
    Insert one audit_log row. Uses `db.flush()`, not `db.commit()` — the
    audit row is part of the same transaction as the capability's own
    effects (via the shared session on CallContext), so a rollback undoes
    both together rather than leaving an orphaned audit entry for an action
    that didn't actually happen.
    """
    entry = AuditLog(
        actor=actor,
        actor_type=actor_type,
        action=action,
        target=target,
        details_json=json.dumps({"category": category, **details}, default=str),
    )
    db.add(entry)
    await db.flush()
    return entry
