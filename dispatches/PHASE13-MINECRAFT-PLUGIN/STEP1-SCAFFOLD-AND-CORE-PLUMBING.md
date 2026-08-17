# Phase 13, Step 1 of 3 — Scaffold + Core Plumbing

You are a scoped sub-chat. **Read `CLAUDE.md` at the repo root first, in
full**, then `PROJECT-PRINCIPLES-AND-WORKING-RULES.md` — this dispatch
assumes you already know those rules. You have **read-only** repo
access. Do not push. Hand back your work as a diff/manifest package per
the working rules, for the head chat to independently verify and apply.

This is **Step 1 of 3, strictly in series**. Step 2 and Step 3 do not
start until your handback is independently verified and applied. Your
job is scoped tightly to what's below — do not start on command
polling, ban enforcement, or GrimAC. That's Step 2 and Step 3's job,
not yours, even if it looks convenient to get ahead on.

## Required reading before you write any code

`minecraft-plugin/MINECRAFT-PLUGIN-SCOPING-AND-HANDOFF.md` on the
**`archive` branch** (not `main` — it was deliberately kept off main;
your read-only access should still be able to fetch that branch). Read
it in full. It has the real, source-verified integration contract with
`umbrella-core` — endpoint shapes, auth header, everything. This
dispatch doc summarizes the Step 1 slice of it; that doc is the source
of truth for details.

**Do not open, reference, or derive structure from the old
`minecraft-plugin/` Java source if you ever encounter it.** It's an
abandoned first attempt with a confirmed-dead-on-arrival GrimAC
integration (reflection bug, silently no-op'd in production). This is a
from-scratch build, informed only by the scoping doc above, not by that
code.

## Scope — build exactly this, nothing more

1. **Project scaffold**: Maven, Java 17+, targeting the **Paper API**
   directly (not raw Bukkit). Package: `com.umbrellaos.plugin`. Basic
   `plugin.yml`, enable/disable lifecycle.
2. **`CoreApiClient`**: the one place every HTTP call to `umbrella-core`
   goes through. Attaches the `X-Plugin-Key` auth header once, here,
   not per-call-site.
3. **`HeartbeatManager`**: periodic `POST /plugin/heartbeat` — online
   status, player count, **real server tick rate** (not estimated),
   plugin version.
4. **`ConfigManager`**: `GET /plugin/config` on startup and on
   reconnect, applied to local plugin state.

## Explicitly out of scope for this dispatch

- Command polling (`GET /mc/commands/pending` etc.) — Step 2.
- Ban enforcement / punishment checks — Step 2.
- GrimAC bridge — Step 3.
- The deferred direct-connection (`connection_mode`) idea from the
  roadmap — not in scope for any of the three steps, per the scoping
  doc.

## Testing

Real unit tests (JUnit/Mockito) for anything unit-testable in
isolation — `CoreApiClient`'s request-building, `ConfigManager`'s
parsing. Full in-game behavior can't be unit tested the way the Python
side can; note in your handback what you verified live (e.g. against a
real local Paper server) vs. what's only unit-tested.

## One thing to be aware of, not to act on

This project has some known, already-diagnosed bugs elsewhere in the
codebase that are being fixed later, in a dedicated cleanup sweep — not
by this dispatch. If something looks broken on the `umbrella-core` side
in a way that seems unrelated to what you're building, don't go
digging into it or trying to fix it — note it briefly in your handback
and move on. Your scope is the four items above only.

## Deliverable for handback

- Plugin loads cleanly on a real Paper server.
- Heartbeats visibly reach core (`POST /plugin/heartbeat` succeeding).
- Config pull works on startup and on a simulated reconnect.
- Diff/manifest package, plus a short handback doc for Step 2 covering:
  what you built, how `CoreApiClient` is structured (Step 2 will extend
  it, not replace it), any deviation from this scope and why, and
  anything you noticed but didn't act on per the section above.
