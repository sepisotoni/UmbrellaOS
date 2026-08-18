# Phase 13, Step 2 of 3 — Command Queue + Ban Enforcement

You are a scoped sub-chat. **Read `CLAUDE.md` at the repo root first, in
full**, then `PROJECT-PRINCIPLES-AND-WORKING-RULES.md`. Read-only repo
access, hand back a diff/manifest, don't push.

**This is Step 2 of 3, strictly in series.** Step 1 (scaffold,
`CoreApiClient`, `HeartbeatManager`, `ConfigManager`) is done and
independently verified/applied before you start — read its handback
doc in `dispatches/PHASE13-MINECRAFT-PLUGIN/` (Step 1's handback will
be placed alongside this file once it lands) before touching anything.
**Extend `CoreApiClient`, don't replace or restructure it** unless
Step 1's handback specifically flags a reason to. Step 3 (GrimAC) does
not start until your handback is verified and applied — don't start on
GrimAC work yourself, even if it looks related.

## Required reading

`minecraft-plugin/MINECRAFT-PLUGIN-SCOPING-AND-HANDOFF.md` on the
**`archive` branch**, in full — same as Step 1 was given. It has the
real, source-verified endpoint contract. This dispatch doc summarizes
your slice of it; that doc is the source of truth for details.

**Do not open, reference, or derive structure from the old
`minecraft-plugin/` Java source if you encounter it** — abandoned
first attempt, not a basis for this build.

## The one design decision already made for you

The scoping doc flags a real gap: the plugin needs to check "is this
player currently banned," but the only existing endpoint for that
(`GET /punishments?...`) requires real RBAC (`punishments.view`), not
the plugin-key auth every other plugin-facing endpoint uses. **The
decision has been made: go with the doc's option 1** — add a
plugin-key-authorized read-only endpoint, e.g.
`GET /plugin/punishments/{player_uuid}/active`, matching the auth
pattern every other plugin-facing endpoint already uses. Do not build
against option 2 (a service-account identity) — that was considered
and explicitly not chosen, because it invents a concept (service
accounts) that doesn't exist anywhere else in this project yet.

This likely means a small, real addition on the `umbrella-core` side
(the new endpoint itself) alongside the plugin-side consumer of it —
both are in scope for this dispatch, since the plugin-side ban check
is meaningless without it.

## Scope — build exactly this, nothing more

1. **`CommandPoller`**: periodic `GET /mc/commands/pending` → execute
   the command in-game → `POST /mc/commands/{id}/complete` to ack.
2. **Ban enforcement**: using the new plugin-key-authorized endpoint
   above, check ban status at join (and anywhere else it's the natural
   enforcement point) and actually kick/block banned players.

## Explicitly out of scope for this dispatch

- GrimAC bridge — Step 3.
- Anything beyond the new ban-check endpoint on the core side — don't
  expand into other core changes even if you notice something adjacent
  worth doing. Flag it in your handback, don't build it.
- The deferred direct-connection (`connection_mode`) idea — not in
  scope for any of the three steps.

## Testing

JUnit/Mockito for isolable logic (command parsing/dispatch,
`CoreApiClient` extensions). Note in your handback what's only
unit-tested vs. verified live against a real Paper server.

## One thing to be aware of, not to act on

This project has some known, already-diagnosed bugs elsewhere in the
codebase, scheduled for a dedicated cleanup sweep later — not this
dispatch. If something on the core side looks broken in a way
unrelated to what you're building, don't investigate or fix it — note
it briefly in your handback and move on.

## Handoff mechanics — how you pass this to Step 3

Same protocol Step 1 used to hand off to you — continue it. Package
into one zip:

1. Your diff/manifest.
2. Your handback doc (what you built, the new endpoint's exact shape,
   live-verification results, deviations, anything noticed but not
   acted on).
3. A copy of `dispatches/PHASE13-MINECRAFT-PLUGIN/STEP3-GRIMAC-BRIDGE.md`
   verbatim.
4. **An explicit declaration that Step 2 is complete**, at the top of
   your handback doc — e.g. "Step 2 (command queue + ban enforcement)
   is complete and independently live-verified as described below."

The head chat still independently verifies before applying anything to
`main` — this doesn't skip that step, it just means the same zip that
goes to the head chat also starts Step 3's sub-chat directly.

## Deliverable for handback

- Command queue round-trip working end-to-end against a real core
  instance (issue a command → it executes in-game → ack reaches core).
- A banned player is actually kicked/blocked at join, against the new
  endpoint.
- Diff/manifest package, plus a handback doc for Step 3 covering: what
  you built, the new endpoint's exact shape as implemented, any
  deviation from this scope and why, and anything noticed but not
  acted on.
