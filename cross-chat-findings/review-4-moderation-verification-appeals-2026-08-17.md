# UmbrellaOS — moderation, verification, and appeals workflow live test

Date: 2026-08-17
Scope: same live codespace/app/DB as prior reviews. Exercised the full
moderation -> punishment -> appeal lifecycle and the verification-request ->
confirm lifecycle end-to-end with real writes against live Postgres, not just
reads. One test player row was seeded directly via SQLAlchemy (bypassing the
broken verification flow described below, since that flow cannot create a
player at all) — no application code was changed.

## Bug #8 — verification.confirm can never succeed for a brand-new player (both code paths)

Summary:
`verification/request` creates a `VerificationCode` row but never a `players`
row. `verification/confirm` (and the "real fix" `verification.confirm`
capability that Phase 6 built to replace this router — see the router's own
comment at api/routers/verification.py) both then try to insert into
`discord_accounts` with that same `player_uuid`, which has a `NOT NULL` FK to
`players.uuid`. Since no player was ever created, this FK insert always fails.

Real evidence (reproduced via BOTH surfaces):
- `POST /api/v1/verification/request` for a brand-new UUID succeeds and
  returns a real 6-digit code.
- `POST /api/v1/verification/confirm` with that code -> `500`,
  `ForeignKeyViolationError` on `discord_accounts_player_uuid_fkey`.
- `POST /api/v1/capabilities/verification.confirm/invoke` (the intended
  replacement path per the router's own code comment) -> same `500`, same FK
  violation, on a fresh code/UUID pair. Confirms this is not a stale-route
  issue; the shared underlying `services/verification/service.py:confirm_verification`
  has the bug regardless of which surface calls it.
- The error also surfaces a secondary symptom: the response includes "This
  Session's transaction has been rolled back due to a previous exception
  during flush," suggesting a second DB operation is attempted against an
  already-failed session rather than cleanly propagating the first error.
- Side effect: the `VerificationCode` row is marked `used = true` before the
  failing insert, so the code is burned even though verification never
  completed — the player has no way to retry with the same code.

Impact:
Every brand-new player's very first verification attempt fails, unconditionally,
on both the legacy REST route and the capability meant to replace it. This is
a core-path outage, not an edge case — verification is presumably how most
players are expected to link at all.

## Bug #9 — appeal creation always violates the DB's own status check constraint

Summary:
`POST /api/v1/appeals` hard-codes the new row's `status` to `"pending"`
(api/routers/appeals.py:104), but the `ck_appeals_status` check constraint on
the `appeals` table only permits `'open'`, `'accepted'`, `'denied'`. There is
no code path that can create an appeal successfully.

Real evidence:
- Created a real player, a real ban via `POST /api/v1/moderation/ban` (worked,
  `201`), then `POST /api/v1/appeals` against that real punishment -> `500`,
  `CheckViolationError` on `ck_appeals_status`, quoting the literal failing
  value `pending`.
- Confirmed via `pg_get_constraintdef`: the constraint only allows
  `ARRAY['open','accepted','denied']`.
- The vocabulary mismatch isn't limited to creation: `AppealUpdateRequest`'s
  own inline comment documents `"pending", "approved", "denied"` as the
  expected status values for the resolve step (`PATCH /appeals/{id}`), but
  `"approved"` would *also* violate the constraint — only `"denied"` happens
  to match. The status vocabulary used throughout the appeals feature's code
  and comments does not match the database's actual constraint anywhere.

Impact:
The appeals feature cannot create a single appeal via its public API in its
current state — 100% failure rate, no workaround. This is more severe than
bug #8 above: verification at least degrades gracefully for already-linked
accounts, this has no successful path at all.

## Confirmed working end-to-end (real writes, real Postgres)

- `POST /api/v1/moderation/warn` and `POST /api/v1/moderation/ban` against a
  real player both succeed (`201`), with correct fields and `active: true`.
- `GET /api/v1/moderation/active/{uuid}` correctly returns both punishments
  for that player.
- `GET /api/v1/punishments` reflects both real writes.
- `POST /api/v1/verification/request` correctly detects and short-circuits an
  already-verified account (`already_verified` field present on schema; not
  separately re-tested this pass since bug #8 blocks reaching that state
  through the public API in a fresh environment).

## Methodology note

A player row could not be created through any live, public API path in this
environment (bug #8 blocks `verification`; `anticheat/flag` requires a plugin
API key not available in this session — see review-3). To still exercise the
moderation/appeals write paths, one `Player` row was inserted directly via
SQLAlchemy against the live DB. No application code was modified. This is a
test-data seeding step only, called out explicitly so it isn't mistaken for a
working player-creation path.

Session notes: two real, unconditional, reproducible bugs found in core
moderation-adjacent workflows (verification, appeals); moderation itself
(warn/ban/active) confirmed genuinely solid. 2026-08-17.
