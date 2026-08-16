# UmbrellaOS — Master Status & Handoff (read this first, always)

This is the entry point for a new "head" chat taking over project
coordination from a prior chat that hit its context limit. Read this file
completely before anything else in the package — it tells you what
everything else is and whether it's still current.

## What this project is

UmbrellaOS is Sepiso Toni's custom Minecraft server administration platform:
`umbrella-core` (Python/FastAPI backend), `umbrella-discord` (py-cord bot),
`umbrella-dashboard` (Next.js 16/React 19), plus a Minecraft-side Paper
plugin. Sepiso Toni hosts on ACLClouds (a paid-tier managed panel — **has
extra port allocation, no shell access**, so no daemon can run there;
`umbrella-daemon` exists in the codebase but is not part of Sepiso Toni's
actual deployment). Development happens across many separate AI chat
sessions ("the courier workflow") — Sepiso Toni physically carries zip
packages between them since sessions can't talk to each other directly.
**Your job as the head chat: hold overall project context, scope work,
verify what comes back from build sessions, and write the next handoff.**
You are not expected to write thousands of lines of code yourself in this
chat — dispatch real build work to fresh sessions with a clear prompt,
the way this project has done for every phase so far.

## Core working discipline (this is not optional — it's the reason this
project hasn't accumulated silent bugs)

1. **Verify, don't trust.** Every "N/N tests passing" claim from a build
   session gets independently re-checked — fresh venv, apply the diff to
   a clean baseline, re-run the suite yourself — before it's treated as
   real. This has caught real problems more than once (a WAF bug, a false
   -negative in the CVE scanner, an actually-dead GrimAC integration in
   the old codebase).
2. **State real design decisions explicitly before building.** Don't let
   a build session default silently on a genuine fork (event bus vs.
   polling, per-plugin vs. generic config-write capability, etc.). If
   something's ambiguous, stop and decide it, then bake the decision into
   the handoff doc so it isn't re-litigated.
3. **Hand off as diff + manifest, not full re-exports**, once a real
   baseline exists (`MANIFEST.md` + a unified diff, `patch -p1`
   instructions). This has been consistently faster and safer to verify
   than full project re-exports.
4. **Strip `.env`/`umbrella.db` before zipping anything**, even if empty —
   this has recurred multiple times as test-run artifacts leaking into
   handoff packages.
5. **Roadmap docs can go stale — always trust the newest, explicitly
   marked-current one**, not whichever you open first. See below.

## Roadmap — which doc is actually current

**`roadmap-and-design-docs/UMBRELLAOS_MASTER_ROADMAP_v3_CONSOLIDATED.md`
is the only authoritative roadmap.** It supersedes both
`UMBRELLAOS_MASTER_ROADMAP.md` (an older 10-phase version, explicitly
marked superseded at its own top) and the roadmap table originally
embedded in `UMBRELLAOS_ECOSYSTEM_ARCHITECTURE.md` (v3's original home,
one-line-per-phase only, detail since pulled into the consolidated doc).
13 phases, numbered 0–12.

## Current phase status (verified, not self-reported)

| Phase | Status |
|---|---|
| 0–6 | ✅ Done |
| 7 (public API, webhooks) | ✅ Done — see `PHASE7-COMPLETE-AND-PHASE8-HANDOFF.md` for history |
| 8 (plugin SDK, sandboxing, marketplace, Discord command wiring) | ✅ Done |
| 9 (observability & security hardening) | ✅ Core logic done and independently verified on **exact pinned dependencies** (783/783). **One real follow-up currently dispatched to a separate active chat**: 5 dependency CVEs found on the first-ever live scan (`starlette`, `pyjwt`, `python-multipart`, `python-dotenv`, `pytest`) need version bumps, plus an optional real-OpenTelemetry-SDK swap. See `PHASE9-COMPLETE-FOLLOWUP-HANDOFF.md` — **check with Sepiso Toni whether that chat has finished before assuming Phase 9 is 100% closed.** |
| 10 (Unified Experience Layer — full dashboard rewrite) | **Scoped and locked, not yet built.** See the roadmap doc's Phase 10 section — every real design fork (topology map: two toggleable layers; search: live fan-out, not pre-built index; custom widgets: per-page, pre-populated defaults, needs a `(user_id, page_id, layout_json)` model) has been explicitly decided with Sepiso Toni, not left for a build session to guess. Ready for a build-kickoff prompt whenever Sepiso Toni wants to start it. **Confirmed: full rewrite, not an extension of the existing dashboard, and explicitly not using v0** — build directly against the real backend. |
| 11 (clustering/HA) | Not started. **Flagged as likely the single hardest phase in the whole roadmap** — distributed consensus/partition handling, a different class of correctness problem than anything built so far. |
| 12 (platform maturity) | Not started. |

**Two flagged ideas, deliberately not assigned a phase number**, captured
in the roadmap doc's "Flagged future ideas" section — don't let them
quietly become "already decided":
- Minecraft-server direct two-way push/pull comms (buildable now — Sepiso Toni
  confirmed ACLClouds' paid tier gives extra port allocations — but needs
  a new lightweight IP/port server-registration model, not the existing
  daemon-shaped `Server` table, plus an auth-gated address-update
  mechanism to avoid a real spoofing risk).
- Plugin-authored Minecraft gameplay add-ons (marketplace plugin → live
  server code). Deliberately left as an open fork: Sepiso Toni's own code only
  (low risk, a deployment pipeline) vs. third-party marketplace code
  (security-boundary-hard, on the order of what the Python sandbox took,
  except the JVM has no equivalent containment mechanism to build on).

## In-flight work outside this chat right now

**Minecraft plugin — scoped, ready to build, not yet dispatched to a
build session as of this handoff.** See
`MINECRAFT-PLUGIN-SCOPING-AND-HANDOFF.md`. There is **no current Java
plugin project** — this is a from-scratch build. Explicitly do not derive
structure from the old `UmbrellaMC` plugin source (see below) — the doc
already extracted the one useful thing from it (the exact GrimAC
integration bug: reflection against a nonexistent `PunishmentEvent`
class) and verified the real, current GrimAC 2.3.73 API directly against
real source (bundled in this package as `Grim-2_3_73.zip`) — `FlagEvent`,
`Check.getViolations()` (a `double`, not the `int` the old code and an
early draft both wrongly assumed), `GrimPlayer.getUniqueId()/getName()`.
One real open decision flagged in that doc: how the plugin authenticates
a ban-check call, since the existing `GET /punishments` endpoint requires
real RBAC (`punishments.view`), not the plugin-key mechanism every other
plugin-facing endpoint uses.

## The old `UmbrellaMC` codebase — what it is, why it matters, what NOT to do with it

Sepiso Toni has a separate, large (~165MB) zip of an **earlier, abandoned
attempt** at this same idea, called `UmbrellaMC` — different name,
different phase structure, not part of this project's lineage. It is
**not included in this package** (mostly dead weight —
`node_modules`, etc. — and its useful findings are already extracted
below). If genuinely needed again, ask Sepiso Toni to re-upload it.

**What's actually relevant from it, already captured:**
- The current `umbrella-dashboard` really did start from this old
  codebase's dashboard (uploaded as reference material at this project's
  very start, then used as a literal starting point when Phase 3 built
  the dashboard) — confirmed via byte-identical file diffs. It has been
  actively maintained since, not frozen, but it inherited real
  datedness and bugs, which is the core reasoning behind Phase 10 being a
  full rewrite rather than an extension.
- `services/anticheat_service.py` in current `umbrella-core` **was**
  genuinely rewritten/extended during the actual v3 rebuild (confirmed by
  diff — the old version only had a binary tempban toggle; current adds
  the full VL-tiered warn/kick/tempban system) — this one was **not**
  just carried over, unlike the dashboard.
- The old Minecraft plugin's GrimAC listener never worked at all — see
  the Minecraft plugin handoff doc for the full, verified explanation.

**Do not open or reference the old codebase's actual source as a basis
for new work, even if Sepiso Toni re-uploads it for some other reason** — it's
verification/history material only, per Sepiso Toni's explicit instruction
("it was written by an AI I don't like for coding, don't let it influence
the new one").

## `services/anticheat_service.py` — one live, real bug worth fixing whenever convenient

`_ai_confidence_review()` (the "AI reviews whether a flag is a real cheat"
function) is dead code — defined, never called. `handle_cheat_flag` uses
pure VL-math for its confidence score, not a live AI check, despite the
function existing and looking wired in. Verified by running the real
function against a real in-memory DB, not just reading it. Low priority,
but worth fixing (wire it in, or delete it so it stops looking
implemented) whenever someone's in that file for another reason. Also:
**this file has zero test coverage** — worth a real test file
(`tests/test_anticheat_service.py`) covering the three severity tiers,
which were manually verified to work correctly in this chat but aren't
locked in by any regression test.

## Package contents map

- `PHASE7-COMPLETE-AND-PHASE8-HANDOFF.md`, `PHASE9-COMPLETE-FOLLOWUP-HANDOFF.md`
  — phase completion history, superseded chains marked at each file's top
- `handoff-to-new-session-phase7*.md` — Phase 7 build history detail
  (event bus, plugin SDK, sandboxing decisions and reasoning)
- `DASHBOARD-PLUGIN-UI-SCOPING.md` — the three-tier plugin UI model
  (widgets/config/owned pages), folded into Phase 10's locked scope
- `MINECRAFT-PLUGIN-SCOPING-AND-HANDOFF.md` — ready-to-build MC plugin spec
- `Grim-2_3_73.zip` — real GrimAC source, for verifying the plugin build
  against real API rather than docs/memory
- `roadmap-and-design-docs/UMBRELLAOS_MASTER_ROADMAP_v3_CONSOLIDATED.md`
  — the only current roadmap; everything else in that folder is either
  superseded or supporting detail
- `umbrella-core-PHASE9-COMPLETE.zip`, `umbrella-discord-PHASE8-COMPLETE.zip`
  — current, verified code sources
- `original-daemon-and-dashboard/umbrella-dashboard-FULL.zip` — current
  dashboard source (about to be superseded by the Phase 10 rewrite, but
  still real and current until that rewrite ships)
- `wheels/` — offline install cache; **known to be stale/mismatched
  against `requirements.txt`'s exact pins** across multiple sessions —
  prefer real network `pip install -r requirements.txt` when available,
  fall back to `wheels/` only when a session genuinely has no network,
  and flag the mismatch explicitly if you do (this has been a recurring,
  correctly-flagged caveat every time it's come up)

## Suggested first message to Sepiso Toni from you (the new head chat)

Confirm you've read this file, ask whether the Phase 9 CVE-fix chat has
reported back yet (since that affects whether Phase 9 is fully closed),
and ask which of the two ready-to-dispatch items — the Minecraft plugin
build, or the Phase 10 dashboard rewrite build-kickoff — he wants to send
to a build session next.
