# Phase 13, Step 3 of 3 — GrimAC Bridge

You are a scoped sub-chat. **Read `CLAUDE.md` at the repo root first, in
full**, then `PROJECT-PRINCIPLES-AND-WORKING-RULES.md`. Read-only repo
access, hand back a diff/manifest, don't push.

**This is Step 3 of 3, the last step in this series.** Steps 1
(scaffold/core plumbing) and 2 (command queue/ban enforcement) are done
and independently verified/applied before you start — read both their
handback docs in `dispatches/PHASE13-MINECRAFT-PLUGIN/` before touching
anything. Extend the existing `CoreApiClient` and plugin structure,
don't restructure it, unless a prior handback specifically flags a
reason to.

## Required reading

`minecraft-plugin/MINECRAFT-PLUGIN-SCOPING-AND-HANDOFF.md` on the
**`archive` branch**, in full. The GrimAC section is the one that
matters most for you, but read the whole doc for context on the plugin
structure Steps 1–2 already built. This dispatch doc summarizes your
slice; that doc is the source of truth for the real, source-verified
GrimAC API details — **use it, don't re-derive from GrimAC's docs**,
since the scoping doc's claims were checked against 2.3.73's actual
source, not documentation that could be stale.

**Do not open, reference, or derive structure from the old
`minecraft-plugin/` Java source if you encounter it.** That old
attempt's GrimAC integration is the specific reason this step exists as
a from-scratch rebuild: it used reflection to look up a class that
doesn't exist, silently swallowed the resulting exception, and logged
"GrimAC not found" forever in production — completely dead on arrival,
never caught because reflection let a typo skip compile-time checking
entirely.

## Scope — build exactly this, nothing more

**`GrimBridge`**, following the scoping doc's confirmed-real API
exactly:
- Real `provided`-scope Maven dependency on GrimAC — **not reflection**.
  A wrong class/method name should fail the build immediately, not
  silently no-op in production.
- Runtime guard: `Bukkit.getPluginManager().isPluginEnabled("GrimAC")`
  to soft-skip if absent.
- `plugin.yml`: `softdepend: [GrimAC]`, not `depend`.
- EventBus API (the current, non-deprecated style) —
  `GrimAPI.INSTANCE.getEventBus().get(FlagEvent.class).onFlag(...)`.
- Report flags to core via the existing `POST /anticheat/flag` (already
  live on the core side, per the scoping doc's endpoint table — this
  step doesn't add new core endpoints, only consumes an existing one).
- **Violation level**: `Check.getViolations()` returns a `double`; core's
  `handle_cheat_flag` expects `vl: int`. Use the scoping doc's already-
  decided conversion — round, via `Math.round(...)`, not truncate. This
  was explicitly decided already; don't silently pick truncate instead.

## Explicitly out of scope for this dispatch

- Anything on the core side — this step only consumes an existing
  endpoint (`POST /anticheat/flag`), it doesn't add or change core.
- The deferred direct-connection (`connection_mode`) idea — not in
  scope for any of the three steps.

## Testing

JUnit/Mockito for anything isolable (the flag→report conversion logic,
`CoreApiClient` extension for the anticheat endpoint). Live verification
against a real Paper server with real GrimAC 2.3.73 installed is the
important one here, given the old attempt's bug was specifically the
kind that unit tests alone wouldn't have caught (a runtime
`ClassNotFoundException` swallowed and logged as a soft failure) — note
in your handback that you actually triggered a real flag on a real test
server and confirmed it reached core, not just that the code compiles.

## One thing to be aware of, not to act on

This project has some known, already-diagnosed bugs elsewhere in the
codebase, scheduled for a dedicated cleanup sweep later — not this
dispatch. If something looks broken in a way unrelated to what you're
building, don't investigate or fix it — note it briefly in your
handback and move on.

## Handoff mechanics — this is the final step, hands back to the head chat

There's no Step 4 — your handback goes straight back to the head chat
as the close-out for all of Phase 13. Package into one zip:

1. Your diff/manifest.
2. Your handback doc, covering the full three-step build per the
   "Deliverable for handback" section below — not just your own slice.
3. **An explicit declaration that Step 3 is complete**, at the top of
   your handback doc — e.g. "Step 3 (GrimAC bridge) is complete and
   independently live-verified as described below; Phase 13 is ready
   for head-chat review."

The head chat independently verifies everything (all three steps'
combined result, not just yours) before marking Phase 13 done in
`PHASE-STATUS-CORRECTED.md` and applying/pushing to `main`.

## Deliverable for handback

- A real GrimAC flag on a real test server reaches core via
  `POST /anticheat/flag`, end to end, confirmed live — not just
  compiled and assumed correct.
- Diff/manifest package, plus a handback doc summarizing the full
  three-step build for the head chat: what exists now across all three
  steps, what was deferred or flagged along the way, and what (if
  anything) still needs a decision before Phase 13 can be marked done
  in `PHASE-STATUS-CORRECTED.md`.
