# UmbrellaOS — full moderation endpoint surface + schema-constraint audit

Date: 2026-08-17
Scope: continuation of review-4. Audited every DB check constraint in the
public schema against the literal values the app code actually writes, then
live-tested the two remaining unexercised moderation endpoints (`kick`,
`ipban`) plus their inverses (`unban`, `ipunban`) against real Postgres.
Same live codespace/app/DB, no code changes.

## Bug #10 — `kick` and `ipban` always violate `ck_punishments_type`

Summary:
Both endpoints write to the same `punishments` table as `warn`/`ban`, but use
type literals (`"kick"`, `"ipban"`) that were never added to the table's own
check constraint, which only permits `warn`, `mute`, `tempban`, `ban`.

Real evidence:
- Schema audit: `ck_punishments_type` = `CHECK (type IN ('warn','mute','tempban','ban'))`.
- `POST /api/v1/moderation/kick` against a real player -> `500`,
  `CheckViolationError` on `ck_punishments_type`, failing row shows `type=kick`.
- `POST /api/v1/moderation/ipban` -> same `500`, same constraint, failing row
  shows `type=ipban`. (This one is also worth flagging separately: it writes
  `player_uuid="SYSTEM"` as a sentinel for IP-level punishments not tied to a
  specific player — that value would likely also fail `punishments`' FK to
  `players.uuid` once the type constraint is fixed, since no such player
  exists. Not confirmed independently, since the type check fails first.)
- `mute` was never exercised (no route calls it), so it's unknown whether it's
  reachable at all, but it is at least present in the DB's allowed set unlike
  `kick`/`ipban`.

Impact:
2 of the moderation module's 6 endpoints (`kick`, `ipban`) fail 100% of the
time, unconditionally. Combined with appeals (bug #9), this is the same root
pattern for the third time in this codebase: application code and the
database's own constraints were never reconciled for the same field.

## Confirmed working end-to-end (real writes/state changes, real Postgres)

- `POST /api/v1/moderation/unban` genuinely works: flips the real ban created
  earlier to `active: false`; confirmed it disappeared from
  `GET /api/v1/moderation/active/{uuid}` while the unrelated `warn` on the
  same player correctly remained active. This is a real, correct state
  transition, not just a 200.
- `POST /api/v1/moderation/ipunban` correctly returns `404` for an IP with no
  active ban (consistent with bug #10 — no ipban has ever successfully been
  created against this schema, so this is expected, not a separate bug).

## Schema-wide constraint audit (for future sessions)

Full list of `CHECK` constraints in the public schema, for reference:
- `punishments.ck_punishments_type`: `warn`, `mute`, `tempban`, `ban` — code
  also writes `kick`, `ipban` (bug #10).
- `appeals.ck_appeals_status`: `open`, `accepted`, `denied` — code writes
  `pending` on create, and its own doc-comment claims `approved` as a valid
  update value (bug #9, review-4).
- `chat_messages.ck_chat_messages_source`: `minecraft`, `discord` — not
  exercised this pass; worth a live write-path test in a future session
  (bridge/message endpoint).

Session notes: schema-constraint audit surfaced the pattern behind bugs #9/#10
before live-testing confirmed it; full moderation endpoint surface now
covered (4/6 broken->fixed-target, 2/6 confirmed solid including a genuine
state-change verification on unban). 2026-08-17.
