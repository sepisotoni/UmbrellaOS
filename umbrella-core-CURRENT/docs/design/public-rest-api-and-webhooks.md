# Public REST API exposure + Webhooks (Phase 7, items 1–2)

## Decision 1: Auth/scope model — reuse `ApiKey`, no new key/OAuth model

`models/api_key.py` / `services/api_key_service.py` already are what a "public API key" needs
to be: an explicit, finite permission list (never `*`/wildcard — enforced at creation), revocable,
and its own module docstring already names the intended users as "the Discord bot, CLI, external
integrations." `identity.apikey.create/list/revoke` are already registered capabilities, already
reachable through the generic invoke endpoint. Building a second key or OAuth-scope model for
"public" callers specifically would be exactly the kind of duplicate surface "no shadow API" already
rules out for routes — the same reasoning extends to auth.

Dashboard session auth (cookie, human, `require_admin_key_or_session`) and API-key auth (header,
machine) are already structurally separate paths in `api/middleware/api_key_auth.py`'s
`require_capability_auth` — nothing new needed there. The scoping a third party gets is simply
whatever finite permission list an admin grants their key at creation time, same as any other
API-key consumer today (the Discord bot's key included). This is not a new mechanism, it is the
existing mechanism used as intended.

**What was actually missing, and is added here:** rate limiting was IP-only
(`api/middleware/rate_limit.py`'s own docstring already flagged per-key limiting as unbuilt future
work). For real external callers this matters — multiple integrations behind a shared corporate
NAT/IP would otherwise share one bucket, and a low-volume legitimate key could be starved by a
noisy neighbor on the same IP. `RateLimitMiddleware` now applies a second, additive check keyed by
a hash of the presented `X-Api-Key` value (never the plaintext — same hash function
`ApiKeyService` already uses) whenever that header is present, on top of the existing per-IP check,
not replacing it. Both must pass. Settings gained
`rate_limit_api_key_requests_per_window` / `rate_limit_api_key_window_seconds`, independently
configurable from the per-IP pair since a machine integration's legitimate request volume looks
different from a browser's.

## Decision 2: Versioning — already decided, not reopened

Every router in this codebase, including `registry/adapters/rest.py` itself, already uses
URL-path versioning (`/api/v1/...`). No header-based scheme is introduced. This section exists to
make explicit that the question was checked against real code and answered by existing convention,
not silently skipped.

## Decision 3: What "REST exposure" required building, concretely

`registry/adapters/rest.py` already generically exposes every registered capability — a new
capability needs zero new route code to become reachable over REST. That means most of Phase 7
item 1 was already done by Phase 0's own design; the real remaining gap was the rate-limiting
hardening above. No new "public-facing capability" flag was added to `CapabilitySpec` — the
existing per-key permission grant already is that access-control surface, and adding a second one
would let the two drift out of sync.

## Decision 4: Webhooks — dispatcher backoff reused, not reimplemented

`services/events/dispatcher.py`'s `EventDispatcher.dispatch_pending` already retries a whole event
with exponential backoff (`attempts`, `next_attempt_at`) if any in-process subscriber raises. The
webhook delivery path is built to raise into that exact mechanism rather than adding a second
retry loop.

**Problem:** existing subscription (`services/events/bus.py`'s `EventBus.subscribe(topic, handler)`)
is static, import-time, one handler per known topic. `WebhookSubscription` rows are admin-created at
runtime for arbitrary topics the bus has no way to know about in advance. Dynamically calling
`EventBus.subscribe()` from inside the create-webhook capability would work but needs
restart-rehydration (re-subscribing from DB on every boot) and de-duplication bookkeeping (don't
double-subscribe the same topic from two different `WebhookSubscription` rows).

**Decision:** add `EventBus.subscribe_global(handler)` — a new, additive registration category for
handlers that run on *every* dispatched event regardless of topic, receiving `(payload, db, topic)`
instead of the existing `(payload, db)`. This is backward compatible: existing per-topic handlers
and every existing dispatcher test are untouched, since `dispatch_pending` still calls
`EventBus.subscribers_for(topic)` handlers exactly as before, and separately (additively) also
invokes global subscribers. The webhook delivery handler is registered once, globally, at import
time (`services/events/subscribers.py`, alongside the existing logging subscriber) and on every
event queries `WebhookSubscription` for active rows matching that event's actual topic — always
correctly re-derived from live DB state, no cache to invalidate, no startup rehydration step needed.

**Delivery semantics, stated plainly:** if any one subscriber URL for a topic fails, the handler
raises, and the *entire* event is retried per the dispatcher's existing backoff — including
re-delivering to subscribers that already succeeded on an earlier attempt. This is the same
at-least-once trade-off `dispatcher.py`'s own docstring already documents for in-process handlers;
it is not a new problem introduced by webhooks. Receivers should treat delivery as idempotent using
the `X-Umbrella-Event-Id` header sent with every delivery. Payloads are signed with HMAC-SHA256
using a per-subscription secret (generated at creation, shown once, never re-retrievable — same
pattern as `ApiKeyService.create_api_key`'s plaintext-shown-once behavior) in an
`X-Umbrella-Signature` header, satisfying the roadmap's "signed payloads" line.

**CRUD surface:** `capabilities/webhooks.py` — `webhooks.subscription.create/list/update/delete`,
declared exactly like any other capability domain (see `capabilities/knowledge.py`), so it is
automatically reachable over REST/CLI/AI with no bespoke router, consistent with "no shadow API."
Scoped to a `webhooks.subscription.manage` / `webhooks.subscription.view` permission pair (view is
read-only list; manage covers create/update/delete), matching the `identity.apikey.manage`-style
single-permission-per-domain pattern used elsewhere for admin-only surfaces of this size.

**Deliberately out of scope for this pass:** wildcard/prefix topic subscriptions (a subscription is
for exactly one topic string — an admin wanting broader coverage creates multiple rows); per-webhook
custom headers or delivery-history introspection beyond what's already visible via the audit log
(every CRUD capability is `audited=True`, so subscription lifecycle is already traceable there).
Both are reasonable future refinements, not required for a working delivery + retry path.
