# UmbrellaOS — Phase 7 Handoff, Part 4: Marketplace (final Phase 7 item)

**Superseded — Phase 7 is now complete. See `PHASE7-COMPLETE-AND-PHASE8-HANDOFF.md`.**
Marketplace (this file's request) is built, independently re-verified twice —
once with unpinned dependencies by the building session, once with exact pinned
dependencies by a separate reviewing pass, both **725/725** — and its zip-slip
protection was hand-tested against two real crafted attack zips, not just
trusted from its own docstring. Use `umbrella-core-PHASE7-COMPLETE.zip` as the
current code source. Kept for this file's two locked decisions (Discord/
dashboard-slot wiring required for v1; local-disk storage, SHA-256, no
auto-update) and their reasoning, which the completion doc doesn't repeat.

Read in order: `handoff-to-new-session-phase7.md` → `-START.md` → `-PART2.md` →
`-PART3.md` (for SDK/sandboxing detail + hand-verification method) → this file →
`PHASE7-COMPLETE-AND-PHASE8-HANDOFF.md`.
Use `umbrella-core-PHASE7-REST-WEBHOOKS-COMPLETE.zip` as your code source —
REST API exposure and webhooks are now **built and independently verified**, not
just planned.

**Independently re-verified, not taken on the building session's word:** merged
the session's diff/changes package onto the SDK/sandbox baseline myself, fresh
venv, full suite — **671/671 passing**, matches the session's own report exactly
(23 new tests, zero regressions). Also spot-checked the new security-relevant
surface by hand: webhook payload signing uses `hmac.new(..., hashlib.sha256)`
over the raw request body with a `secrets.token_urlsafe(32)`-generated secret —
standard, correctly implemented, nothing to flag.

**Process note for whoever's building this phase:** this round's handoff was
delivered as a proper diff/changes package with a manifest and unified diff
(`MODIFIED_FILES.diff`), not a full project re-export — this made independent
verification meaningfully faster and safer (reviewable before merging, no risk
of accidentally reverting someone else's untracked changes). Keep doing it this
way for the marketplace work below.

## What's done (Phase 7 items 1–2, now complete)

**REST API exposure (item 1):**
- Per-API-key rate limiting, additive on top of the existing per-IP check (not
  replacing it) — `api/middleware/rate_limit.py`. Keyed by a SHA-256 hash of the
  presented key (same hash `ApiKeyService` uses for lookup), never the
  plaintext, never logged. Deliberately does not validate the key against the
  DB in the middleware (no DB session available there) — an invalid key still
  gets its own stable bucket, which incidentally also rate-limits credential
  probing, called out as a side benefit rather than the goal.
- Versioning: confirmed as already-decided by existing convention (`/api/v1/...`
  URL-path prefixing, same as every other router including the capabilities
  router) — correctly not reopened as a new decision.
- Auth: confirmed the existing `ApiKey` model (explicit finite permission list,
  never wildcard, revocable) is the right mechanism, not a new OAuth/second-key
  model — avoids a shadow-auth-surface, same anti-pattern as a shadow API.
- The actual "exposure" work turned out thinner than PART3 expected once
  investigated: `registry/adapters/rest.py` already generically exposes every
  capability at `POST /api/v1/capabilities/{name}/invoke` with zero
  per-capability code, and `identity.apikey.create/list/revoke` already existed
  and were already reachable through it. Worth remembering this pattern — most
  future "exposure" work is a config/auth problem, not new endpoint code,
  because of how Phase 0's registry was designed.

**Webhooks (item 2):**
- `models/webhook.py` — `WebhookSubscription` (topic, url, secret, active),
  migration `023_webhook_subscriptions.py`, chained off `022_events_outbox`.
- `services/webhooks/service.py` — `WebhookService` (CRUD) +
  `WebhookDeliveryService` (one-shot signed HTTP POST, no internal retry loop —
  retries come from the existing dispatcher backoff, deliberately not
  duplicated here).
- `capabilities/webhooks.py` — `webhooks.subscription.create/list/update/delete`
  declared as capabilities (same pattern as every other domain), automatically
  REST/CLI/AI-reachable with no bespoke router.
- New permission keys `webhooks.subscription.view`/`.manage`, deliberately their
  own namespace rather than folded into `identity.apikey.manage`, and
  deliberately **not** added to any `DEFAULT_ROLES` list — an admin must
  explicitly grant these, confirmed intentional via
  `test_webhook_view_permission_allows_list_but_not_create`, not an oversight.
- **The real architectural addition**: `EventBus.subscribe_global(handler)` in
  `services/events/bus.py` — a new, additive registration category, completely
  separate from per-topic `subscribe()`, for handlers that run on every
  dispatched event and receive `(payload, db, topic, event_id)`. This exists
  because `WebhookSubscription` rows are admin-created at runtime for arbitrary
  topics the bus has no way to statically pre-register for at import time —
  the global subscriber re-derives "who cares about this topic" from the DB on
  every dispatch instead, with no startup-rehydration bookkeeping and no
  staleness risk. `dispatch_pending` now invokes global subscribers inside the
  same try/except as per-topic ones, so a delivery failure retries through the
  *existing* `attempts`/`next_attempt_at` backoff — no new retry logic was
  written, as instructed.
- **Explicit, documented trade-off, not a silent gap**: delivery is
  at-least-once. A partial failure across multiple subscribers for one topic
  retries the whole event, so already-succeeded deliveries get re-POSTed.
  Receivers are expected to dedupe on the `event_id` carried in delivery
  (surfaced via the signed payload) — this is the same semantics the
  dispatcher already documented for in-process handlers, just now also true
  for external HTTP receivers.
- 23 new tests total across bus/dispatcher/rate-limit/webhook-CRUD/
  webhook-delivery, all passing, all written incrementally per-change (not
  batched).

**Explicitly declined as out of scope, stated in the design doc, not gaps found
late:** wildcard/prefix topic subscriptions, per-webhook custom headers,
delivery-history introspection beyond the audit log. Revisit only if a real
need surfaces.

## What's left in Phase 7 (final item)

**Marketplace** — listing, versioning, install flow. This is the only thing
standing between "Phase 7 done" and "Phase 8 formally closed" (recall from the
consolidated roadmap: what these handoff docs call "Phase 7" actually spans v3
Phase 7 *and* 8 — see
`roadmap-and-design-docs/UMBRELLAOS_MASTER_ROADMAP_v3_CONSOLIDATED.md` if you
haven't read it, it's the authoritative roadmap now, not the older
`UMBRELLAOS_MASTER_ROADMAP.md`).

Two real prerequisite questions, correctly left unresolved by the last two
sessions rather than defaulted under time pressure — **resolve both
deliberately before writing marketplace install-flow code, don't assume an
answer to move faster:**

1. **Does a plugin's `discord_commands`/`dashboard_ui_slots` actually need to
   work end-to-end for marketplace v1, or can "installed but its Discord
   commands don't register anywhere yet" ship as a known interim limitation?**
   Nothing currently renders either of these after a plugin registers — the
   manifest declares them, `services/plugins/registration.py` validates them
   exist and cross-reference correctly, and that's where it stops. If
   marketplace v1 needs a plugin to be genuinely *usable* post-install (which
   your own Discord-status-channel plugin idea would require), this has to be
   built first or alongside, not after — it's not optional scope you can
   punt to Phase 9+ if that's the bar. If a "list + install source code, wiring
   comes later" bar is acceptable instead, marketplace can proceed without it.
   This is a product decision (what does "installed" mean to the user), not
   just a technical one — flag it explicitly rather than picking silently.
2. **Where do plugin zip files/source actually live on disk in production?**
   `ProcessSandbox` takes `sources` as a constructor dict today, by design,
   with zero opinion about storage location — something needs to own
   "download this plugin's source from the marketplace and hand it to the
   sandbox," and needs a real answer for storage location, integrity checking
   (hash verification against what the marketplace listed), and update/
   versioning (what happens to a running install when a new version is
   published — does it require explicit admin action, or auto-update, and if
   the latter, does a sandboxed process resource limit change require
   re-provisioning anything).

## Working conventions (unchanged, still binding)

Test after every change, stop at the first new failure, don't batch. Verify
claims against real code, including every previous session's self-reported
summary — including this one's. Flag real design decisions before building past
them — items 1 and 2 above are exactly that kind of decision. Hand back changes
as a diff/manifest package the way this session did, not a full re-export — it's
faster to verify and safer to merge. Strip `.env`/`umbrella.db` before zipping
even if empty/placeholder.
