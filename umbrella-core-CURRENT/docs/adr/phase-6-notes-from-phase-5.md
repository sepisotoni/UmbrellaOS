# Phase 6 — Notes carried forward from Phase 5

## Gap: no general-purpose event bus exists, despite the roadmap assuming one

The master roadmap's Phase 5 section states the moderation escalation queue should be *"delivered by
push over the Phase 2 event bus (not polling)."* Checked during Phase 5 work: **no such event bus
exists anywhere in this codebase.** Verified by searching for any `EventBus`/publish-subscribe pattern
and by reading `PHASE2_CHANGES.md` (the actual record of what Phase 2 delivered) - only `AuditLog`
(a plain DB write, no pub/sub) and `hosting_console_ws.py` (a narrow, hosting-console-specific
WebSocket, unrelated to general event delivery) exist. The roadmap's Phase 2 description mentions
"event bus, audit log" together, but only the audit log half was ever actually built.

**Decision made during Phase 5:** rather than build a one-off WebSocket push just for escalations
(risking throwaway work once Phase 6 designs its actual notification fabric with more consumers in
mind), or build a premature general-purpose event bus with only one real consumer to design against,
escalations were left poll-only for Phase 5 (`moderation_intelligence.escalation.list`, already built
and fully functional - staff can see open escalations on demand today). Push delivery is explicitly
Phase 6's job (**"Discord & Notification Fabric"** is Phase 6's own name), not a gap Phase 5 should
have silently plugged.

**What Phase 6 needs to actually decide, not inherited as a decision already made:**
- Whether the notification fabric is a real pub/sub layer (in-process, or Redis-backed given `redis`
  is already a dependency for rate limiting) versus something narrower.
- Escalations are the first concrete consumer, but Phase 6's own Discord/email/webhook delivery needs
  will likely be better design input than guessing at them now from a single use case.

Not treating this as solved - flagged here so Phase 6 doesn't have to rediscover it, and so a future
session doesn't assume "the event bus" already exists just because the roadmap's Phase 5 text implies
it should.
