# UmbrellaOS — Minecraft Plugin (Java/Paper): Scoping & Build Handoff

There is currently no live Java plugin project — Sepiso Toni does not have the
actual server-side source, only an old, abandoned first attempt (from the
pre-rebuild `UmbrellaMC` codebase) that must **not** be reused as a basis
for this: it was written by a different AI tool, and its one working
integration (GrimAC) never actually functioned (see "Known bug in the old
attempt" below). This is a from-scratch build, informed by — but not
derived from — that old code.

**Do not open, reference, or derive structure from the old
`minecraft-plugin/` source if it's ever in context alongside this doc.**
Everything below is either newly designed or independently re-verified
against real, current source (GrimAC's actual 2.3.73 codebase, and
`umbrella-core`'s actual current endpoints) — not inherited.

## What already exists and works, on the `umbrella-core` side (verified)

All under `api/routers/plugin.py`, `api/routers/anticheat.py`,
`api/routers/mc_commands.py`. Auth for all of these: header
`X-Plugin-Key: <shared secret>` (same value as `X-Admin-Key`, checked
against `settings.secret_key` — one shared secret today, not per-server;
see the flagged future item on this below).

| Direction | Endpoint | Purpose |
|---|---|---|
| Plugin → core (push) | `POST /plugin/heartbeat` | online status, player count, TPS, version, `grim_connected` |
| Plugin → core (push) | `POST /anticheat/flag` | GrimAC violation reports |
| Core → plugin (pull) | `GET /plugin/config` | non-sensitive settings sync, startup/reconnect |
| Core → plugin → core | `POST /plugin/control` (enqueue, admin/core side) → plugin polls `GET /mc/commands/pending` → `POST /mc/commands/{id}/complete` | core-initiated actions the plugin executes and acknowledges |

**Confirmed gap, needs a decision before building the punishment-enforcement
piece:** the plugin needs to check "is this player currently banned" to
actually kick someone at join/flag time. The only existing endpoint for
that, `GET /punishments?player_uuid=...&active_only=true`, requires
`require_permission("punishments.view")` — real RBAC tied to a user/role,
not the plugin-key mechanism every other plugin-facing endpoint uses.
**Two ways to close this, pick one before building the ban-check flow:**
1. Add a plugin-key-authorized read-only ban-check endpoint (e.g.
   `GET /plugin/punishments/{player_uuid}/active`), mirroring the pattern
   of the other plugin-facing endpoints — smallest, most consistent fix.
2. Issue the plugin a real service-account identity with
   `punishments.view` granted, and have it authenticate as that instead of
   (or alongside) the plugin key for this one call — more RBAC-correct,
   more setup.
Recommend (1) — it matches every other plugin-facing endpoint's auth
model and doesn't require inventing a service-account concept that
doesn't exist anywhere else in this project yet.

## GrimAC integration — verified against real 2.3.73 source, not guessed

**The old attempt's bug, confirmed by reading its actual code:** it used
reflection to look up `ac.grim.grimac.api.event.events.PunishmentEvent`
— a class that does not exist. `Class.forName(...)` threw
`ClassNotFoundException` every single time, which the code caught and
logged as "GrimAC not found," so the bridge silently never registered,
ever, in production. Not a subtle bug — completely dead on arrival.

**Root cause worth avoiding structurally, not just fixing the symptom:**
reflection was used specifically to avoid a compile-time dependency, which
is exactly what let a typo become a silent, permanent no-op instead of a
build failure. **Use a real `provided`-scope Maven dependency on GrimAC
instead**, with a runtime `Bukkit.getPluginManager().isPluginEnabled("GrimAC")`
check to soft-skip if absent. A wrong class/method name then fails the
build immediately, not silently in production forever.

**Confirmed real API** (read directly from GrimAC 2.3.73's actual source,
not from documentation that could be stale):
- `ac.grim.grimac.api.event.events.FlagEvent` — real, exists, constructed
  as `new FlagEvent(GrimPlayer player, Check check, String verbose)` and
  dispatched via `GrimAPI.INSTANCE.getEventBus().post(event)`.
- `GrimPlayer.getUniqueId()` / `GrimPlayer.getName()` — confirmed real.
- **Violation level is `Check.getViolations()`, returning a `double`** —
  not `FlagEvent.getVl()` returning an `int`, which is what both the old
  broken plugin and an earlier draft of this doc incorrectly assumed
  before the real source was checked. `handle_cheat_flag` on the core
  side takes `vl: int` — decide explicitly how to convert (round vs.
  truncate) rather than letting an implicit cast silently pick one.
- `Check.getCheckName()` — confirmed real (Lombok `@Getter` on the class,
  backed by the real `checkName` field).

**Real integration shape** (EventBus API — the newer of GrimAC's two
supported styles; the older `@EventHandler` style is being phased out per
GrimAC's own changelog, no reason to build against something already
being deprecated):

```java
if (Bukkit.getPluginManager().isPluginEnabled("GrimAC")) {
    GrimAPI.INSTANCE.getEventBus().get(FlagEvent.class).onFlag(grimPlugin,
        (grimPlayer, check, verbose, cancelled) -> {
            reportFlagToCore(
                grimPlayer.getUniqueId(),
                grimPlayer.getName(),
                check.getCheckName(),
                verbose,
                (int) Math.round(check.getViolations())
            );
            return cancelled; // don't override Grim's own decision
        });
}
```

`plugin.yml`: **`softdepend: [GrimAC]`**, not `depend` — `anticheat.enabled`
is already a real toggle on the core side, so the plugin shouldn't hard-fail
to load just because GrimAC isn't installed yet.

## Full plugin scope for this build

**In scope now** (everything core already supports, listed above):
1. Heartbeat loop — periodic `POST /plugin/heartbeat` with online status,
   player count, TPS (real server tick rate, not estimated), version.
2. Config pull — `GET /plugin/config` on startup and reconnect, applied to
   local plugin state.
3. Command-queue poller — periodic `GET /mc/commands/pending`, execute,
   `POST /mc/commands/{id}/complete`.
4. GrimAC bridge — per above, soft-dependency, real EventBus API.
5. Ban enforcement — depends on the punishment-check auth decision above
   being made first; don't build this part until that's answered.

**Explicitly deferred, not in this build** — the direct push/pull
two-way comms idea (`connection_mode` setting, core connecting straight
to the server's IP:port using the confirmed extra-port allocation, the
auth-gated address-update mechanism) from the roadmap's "flagged future
ideas" section. That needs its own core-side model (a real lightweight
server-registration table with `ip`/`port`, which doesn't exist yet — see
that roadmap section for why the existing `models/hosting.py::Server`
table doesn't fit). Building the plugin against a channel that doesn't
exist on the core side yet would be building against nothing. This build
uses the existing four-channel poll/push model only.

## Project structure

Maven (matches Paper/Bukkit ecosystem convention), Java 17+ (current
Paper API baseline), targeting the Paper API directly rather than raw
Bukkit (access to newer scheduler APIs, better long-term support).
Package suggestion: `com.umbrellaos.plugin` (kept from the old project's
naming only as a namespace choice, not its code).

Suggested module shape — a manager per responsibility, matching the
separation `services/` already uses on the core side, not a monolith:
- `HeartbeatManager` — the periodic push loop
- `ConfigManager` — pull + local settings cache
- `CommandPoller` — the pending-command loop
- `GrimBridge` — the corrected listener above
- `CoreApiClient` — one place all HTTP calls to `umbrella-core` go through
  (auth header attached here once, not per-call)

## Working conventions (unchanged, still binding)

Test after every change, stop at first failure — for a Java/Paper plugin
this means actual unit tests where logic is testable in isolation (e.g.
`CoreApiClient` request-building, config parsing) via JUnit/Mockito, even
though full in-game behavior can't be unit tested the way Python services
can. Verify claims against real source (this doc already modeled that —
every GrimAC API claim above was checked against 2.3.73's actual code, not
assumed from documentation). Flag real design decisions before building
past them — the punishment-check auth gap above is exactly that kind of
decision, don't default it silently. Hand back changes as a diff/manifest
package once there's a real baseline to diff against; for this first build,
a clean project archive with a manifest describing structure is the
equivalent starting point.
