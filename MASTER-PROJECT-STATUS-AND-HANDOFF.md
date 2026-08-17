# UmbrellaOS — Master Project Status & Handoff

**Read this file completely before doing anything else, including
before opening any other file in this package.** This is the entry
point. Everything else is referenced from here.

---

## 1. What UmbrellaOS is

UmbrellaOS is a custom Minecraft server administration platform, built
for Sepiso Toni's community server ("MOON"). Sepiso Toni is the sole developer and
project owner. The stack:

- **`umbrella-core/`** — Python/FastAPI/PostgreSQL backend. Single
  source of truth for everything: capability registry, RBAC, audit logs,
  plugin marketplace, moderation, observability. Everything else in the
  stack calls into this.
- **`umbrella-discord/`** — py-cord Discord bot. Verification
  (Discord↔Minecraft account linking), moderation commands, canned
  responses, fun commands, cogs for knowledge/operational
  intelligence/player risk.
- **`umbrella-dashboard/`** — Next.js/React web dashboard. Currently
  mid-rewrite (see Phase 10 below) — the old one is deprecated, do not
  build forward from it.
- **A Paper/Java Minecraft plugin** — not yet started. Fully scoped
  (see `minecraft-plugin/`), from-scratch build, GrimAC anticheat
  integration already verified against real source.

Hosting: ACLClouds (locked managed panel, no shell access — no daemon
layer runs in production, server status/TPS comes from the Java plugin
pushing data to core, with a core-side watchdog for offline detection).
Development happens across Sepiso Toni's local Windows PC and GitHub
Codespaces (Codespace is the reliable git target — Sepiso Toni doesn't push
local Windsurf/Cursor edits to git).

**Core design decisions, established early and unchanged since:**
integer role levels (0–4: Player/Helper/Moderator/Admin/Owner), Discord
OAuth2 with HttpOnly session cookies, `is_owner` bootstrap tied to
`INITIAL_ADMIN_DISCORD_ID`, append-only audit logs, encrypted sensitive
settings, database-driven permissions, no automatic AI actions without
approval.

---

## 2. The working discipline — READ THIS, IT'S NOT OPTIONAL

This project has been built across many separate chat sessions, courier-
style: Sepiso Toni carries zip packages between chats because each chat has a
limited context window. **This discipline is why the project has stayed
correct across dozens of handoffs, and abandoning it is the single
biggest risk to finishing cleanly.**

1. **Never trust a self-report. Verify independently, every time.**
   Every phase's real bugs were found by *actually running* the
   verification loop against a fresh environment — not by reading code,
   not by trusting a prior session's "X passed" claim. Concretely: fresh
   venv, install from wheels (or real network if available), run the
   real test suite yourself, run `pip check`, run the dependency
   scanner. Same for the frontend: fresh `npm install`, `npm audit`,
   `npm run build`, `npx tsc --noEmit`, `npm run lint` — all actually
   run, not assumed.
   - This exact discipline is what caught a **critical Next.js RCE**
     that sat in `package.json` for three build sessions before anyone
     ran `npm audit` for real. It's what caught a missing `eslint.config.js`
     that made every prior "lint passed" claim meaningless. It's what
     caught several genuine React cascading-render bugs. It's what
     caught a dependency version-skew that silently broke every build
     since step 2. None of those would have been caught by reading code.
2. **Resolve architecture decisions explicitly before dispatching build
   work.** If a build session would have to guess at a real fork (data
   shape, permission model, storage backend), stop and get an explicit
   decision from Sepiso Toni first. Don't let a build session's convenience
   silently decide something with long-term consequences.
3. **Carry handoff state between sessions via structured zip packages** —
   diff+manifest for incremental changes, or full source + handback docs
   for larger jumps. Always leak-check before packaging (`.env` files
   with real secrets have leaked into intermediate working copies
   multiple times in this project's history — always `find . -iname
   ".env" -o -iname "*.db"` before zipping anything).
4. **Check for gaps the design docs assumed were already built.** Twice
   in Phase 10 alone, a scoping doc referenced infrastructure ("the
   plugin's own kv storage," "the existing Settings page") that turned
   out to not actually exist anywhere in the codebase. Check before
   building on top of an assumption.

---

## 3. Phase history (0–9: closed and verified)

- **Phases 0–6:** Capability registry, RBAC, hosting control plane,
  moderation core, verification system, mute enforcement, permission
  system with per-user overrides.
- **Phases 7–8 (closed):** Public REST API, durable outbox-table webhook
  event bus, plugin SDK with process-sandbox isolation (adversarially
  tested, two escape attempts held), marketplace with zip-slip
  protection hand-tested, Discord slash command wiring from installed
  plugins. **The old `umbrella-dashboard` was discovered to be
  byte-identical to the abandoned `UmbrellaMC` prototype** — this is why
  Phase 10 is a full rewrite, not an extension. Old dashboard/daemon
  source kept in `historical-reference/` for reference only — never
  build forward from it.
- **Phase 9 (closed):** Observability layer — Prometheus metrics, real
  OpenTelemetry SDK tracing (replaced a hand-rolled W3C traceparent
  shim), threat detection hooks, CVE dependency scanner. A live scan
  found real vulnerabilities across five packages; all five bumped plus
  the OTel swap, independently verified at 783/783 tests.

**Open infrastructure issue from Phase 7, still not fixed as of this
doc:** none currently known — the wheels mismatch issue from that era
was fixed during Phase 10 packaging (fresh wheels regenerated to match
current pins, confirmed offline-installable).

**Minecraft plugin:** fully scoped in `minecraft-plugin/
MINECRAFT-PLUGIN-SCOPING-AND-HANDOFF.md`, built against real GrimAC
2.3.73 source (bundled in that same folder) — confirmed `FlagEvent`,
`Check.getViolations()` returns `double` not `int`, `EventBus` API
preferred over deprecated `@EventHandler`. **One open decision:** how
the plugin authenticates ban-check calls (the existing punishment
endpoint uses RBAC, not the plugin-key auth every other plugin call
uses) — needs a decision before this can start, smaller in scope than
Phase 10's Decision 2 was.

**Known housekeeping, low priority, not urgent:** `anticheat_service.py`
has dead code (`_ai_confidence_review`, never wired in) and zero test
coverage.

---

## 4. Phase 10 — current, detailed state

Phase 10 is "Unified Experience Layer": a full dashboard rewrite plus
three tiers of plugin-contributed UI (Tier 1 dashboard widgets, Tier 2
config toggles, Tier 3 plugin-owned pages), command palette/search,
topology map, and custom per-page dashboards.

**Full detail — architecture, every locked decision, sequencing — is in
`phase10/PHASE10-BUILD-KICKOFF-HANDOFF.md`. Read that before touching
Phase 10 code.** Every individual step's handback doc is in
`phase10/handback/`, in order. The two most important to read, in this
order:

1. **`phase10/handback/STEP8-TIER2-CONFIG-TOGGLES-BACKEND.md`** — the
   most recent, has the current real state and the concrete "what's
   left" list.
2. **`phase10/handback/STEP6-VERIFICATION-ADDENDUM.md`** and
   **`STEP7-VERIFICATION-ADDENDUM.md`** — document exactly what real
   bugs were found by actually running the verification loop, and how
   they were fixed. Read these to understand *why* the discipline in
   section 2 above matters, concretely.

### What's done (steps 0 through 8's backend half)

- Step 0: live marketplace API response-shape verification.
- Step 1: core schema extension (`render_as` field).
- Step 2: dashboard scaffold (Next.js 16, server-components-by-default).
- Step 3: Tier 1 dashboard widgets (schema-driven rendering only — no
  plugin-supplied JSX ever runs in the browser, this is a hard
  constraint, not a preference).
- Step 4: command palette + federated live search (no pre-built index,
  by design).
- Step 5: topology map (two toggleable layers — infra, capability
  dependency).
- Step 6: custom per-page dashboards (`(user_id, page_id, layout_json)`
  persistence).
- Step 7: Tier 3 plugin-owned pages (`app/marketplace/[pluginId]`).
- Step 8 (partial): **Tier 2 config toggles — backend only.** Decision 2
  (config-write capability shape) is resolved: **Option A**, per-plugin
  auto-generated capability (`plugin.<id>.config.set`/`.get`), Sepiso Toni's
  explicit call, made for long-term customizability. Along the way, a
  real gap was found and fixed: the design assumed a plugin key-value
  storage backend already existed; it didn't, so that was built first
  (`models/plugin_kv.py`, `services/plugin_kv/`).

**Backend verified state: `umbrella-core-CURRENT/` — 838/838 tests,
fresh venv, offline install from `wheels/`. `pip check` and the
dependency scanner both clean.**

**Frontend verified state: `umbrella-dashboard-CURRENT/` — last fully
verified at the end of step 7 (0 `npm audit` vulnerabilities, clean
build across 12 routes, clean `tsc --noEmit`, 0 lint errors). Tier 2's
frontend (a Settings page) has NOT been built yet — see below.**

### What's left in Phase 10

1. **Tier 2 frontend (Settings page) — the immediate next task.**
   Fully scoped in `phase10/handback/STEP8-TIER2-CONFIG-TOGGLES-BACKEND.md`'s
   "Frontend — not started" section: which route to build, which
   existing files in this repo to copy the pattern from
   (`lib/marketplace-pages.ts` for the server-only fetch helper,
   `app/api/dashboard-layout/route.ts` for the same-origin API route
   pattern, `dashboard-customizer.tsx` for the client toggle leaf
   pattern). **Read that section before writing any code** — it also
   explains why the scoping doc's original assumption (toggles render
   into "the existing Settings page") doesn't hold, because that page
   was never built in any prior step.
2. **Marketplace listing/install UI** (`app/marketplace/page.tsx` — still
   the step-2 placeholder). Browse/publish/install/uninstall currently
   only works via CLI/API, not from the dashboard itself. Never assigned
   to any step — worth an explicit ask to Sepiso Toni about whether it's in
   scope for "done."
3. **No manual/browser runtime testing has happened anywhere in Phase
   10.** Every check across every step has been static (tests, build,
   lint, audit). Worth doing before calling the whole phase finished.

---

## 5. What a new chat picking this up should actually do

1. Read this file completely (you just did, if you're reading this
   line).
2. Read `phase10/PHASE10-BUILD-KICKOFF-HANDOFF.md` for full Phase 10
   architecture.
3. Read `phase10/handback/STEP8-TIER2-CONFIG-TOGGLES-BACKEND.md` for the
   current state and immediate next task.
4. Before writing any code: independently verify the claims in this doc
   are still true. Fresh venv, `pip install --no-index --find-links=wheels/
   -r umbrella-core-CURRENT/requirements.txt -r
   umbrella-core-CURRENT/requirements-dev.txt`, run `pytest -q` — should
   be 838 passed. Fresh `npm install` in `umbrella-dashboard-CURRENT/`,
   run `npm audit`/`npm run build`/`npm run lint` — should all be clean.
   **Don't skip this just because this doc says it's true — that's
   exactly the "trust a self-report" mistake section 2 warns against.**
5. Build the Tier 2 Settings page frontend (the concrete next task).
6. Run the same verification loop on the result before packaging
   anything back to Sepiso Toni. Write a handback doc following the pattern
   every prior step used (in `phase10/handback/`) — what was built, what
   was verified and how, what's still open, any real gaps found along
   the way stated honestly rather than glossed over.
7. If a request requires guessing at an architecture decision with
   long-term consequences (data shape, permission model, anything a
   future plugin author or Sepiso Toni would have to live with) — stop and
   ask, don't guess. This has happened twice already in this project
   (Phase 10 Decision 2, the Minecraft plugin's ban-check auth question)
   and both times stopping to ask was the right call.

---

## 6. Git history — real as of 2026-08-15, none before that

**Before 2026-08-15, this project had no git repository carried between
chats** — every handoff, in every phase, was a zip-based snapshot, no
`.git` folder anywhere. **That changed with D4 in
`PROJECT-PRINCIPLES-AND-WORKING-RULES.md`**: the repo now lives at
`github.com/sepisotoni/UmbrellaOS` with real, hosted, commit-by-commit
history from that date forward. For anything before the seam commit, the
closest equivalent is still the chain of handback/handoff docs in
`historical-reference/` and `phase10/handback/` — that pre-git narrative
isn't being reconstructed retroactively into git log. For anything from
2026-08-15 onward, use `git log` — see `PROJECT-PRINCIPLES-AND-WORKING-RULES.md`
sections 3 and 6 for the actual rules (session-labeled commits, D5's
two-tier PAT access).

## 7. Full project narrative history — every complication, not just a summary

Section 3 above is a compressed summary. For the real, detailed
narrative — including complications, false starts, and things that
were tried and superseded — read, in this order:

1. **`historical-reference/ORIGINAL-MASTER-STATUS-AND-HANDOFF-pre-phase10.md`**
   — the actual master doc this project was running on immediately
   before Phase 10 started, verbatim, not summarized. Has detail this
   doc's section 3 compressed away: the exact byte-identical-diff
   discovery that the old dashboard came from the abandoned `UmbrellaMC`
   prototype, the specific `_ai_confidence_review()` dead-code finding
   in `anticheat_service.py`, two deliberately-unassigned future ideas
   (Minecraft direct server push/pull, plugin-authored gameplay add-ons)
   that shouldn't be treated as already-decided, and exactly why the old
   `UmbrellaMC` codebase (a *separate, earlier, abandoned* attempt at
   this same idea — different name, different phase structure, not part
   of this project's lineage) was deliberately excluded from every
   handoff package rather than carried forward.
2. **`historical-reference/phase7-build-narrative/`** — five documents,
   in filename order (`handoff-to-new-session-phase7.md` →
   `-START.md` → `-PART2.md` → `-PART3.md` → `-PART4.md`), each marked
   at its own top with what it superseded and why. This is the most
   detailed "what actually happened, including dead ends" record in the
   whole project — Phase 7 alone went through this many handoff
   documents before landing. Useful less for Phase 7's specifics (long
   done) and more as a concrete example of how this project's handoff
   discipline actually works in practice across a phase that took
   several sessions to land.
3. **`historical-reference/umbrella-core-bug-report.md`** — a standalone
   code-review pass from partway through the project (Phase 5-era),
   found via manual review plus an actual test/linter run, not
   assumption. Historical, but shows the same "verify by running it"
   standard applied to a different kind of check (static analysis, not
   just tests).
4. **`historical-reference/PHASE7-COMPLETE-AND-PHASE8-HANDOFF.md`** and
   **`PHASE9-COMPLETE-FOLLOWUP-HANDOFF.md`** — the completion/handoff
   docs for those phases, narrating what was built and how it was
   verified at the time.
5. **`phase10/handback/`** — every Phase 10 step's handback doc, in
   order, is this same kind of narrative record for the current phase.
   `STEP6-VERIFICATION-ADDENDUM.md` and `STEP7-VERIFICATION-ADDENDUM.md`
   specifically narrate real complications found (a critical Next.js
   CVE, missing lint config, genuine React bugs) and how each was
   actually resolved — not a clean success story, the real messy one.

---

## 9. Unverified leak report — needs your attention before anything else in this section

`UNVERIFIED-leak-investigation/` contains a report Sepiso Toni uploaded
claiming a separate `new_attempt/UmbrellaOS` codebase is nearly
byte-identical to this project's own `umbrella-core`. **The head chat
that assembled this package could not verify this** — no access to the
files being compared. Read
`UNVERIFIED-leak-investigation/README-READ-FIRST.md` first; it explains
exactly what's confirmed, what isn't, and one thing that's urgent
regardless (a claim of real, live `SECRET_KEY`/`ADMIN_KEY` values sitting
in a zip — worth asking Sepiso Toni whether those need rotating before
anything else in this package gets touched).

---

## 10. Package contents

- `umbrella-core-CURRENT/` — backend, current verified state (838/838)
- `UNVERIFIED-leak-investigation/` — an unverified report about a
  possibly-related codebase; read section 9 above and the folder's own
  README before acting on anything in it.
- `umbrella-dashboard-CURRENT/` — frontend, current verified state
  (verified through step 7; Tier 2 frontend not yet built)
- `wheels/` — matching Python wheels for offline backend install
- `phase10/` — kickoff doc, every step's handback doc, the original
  scoping/roadmap docs Phase 10 was planned from
- `other-services/umbrella-discord-PHASE8-COMPLETE.zip` — the Discord
  bot, untouched throughout all of Phase 10, still current
- `minecraft-plugin/` — scoping doc + bundled GrimAC 2.3.73 reference
  source, for whenever that track starts
- `historical-reference/` — the ORIGINAL master status doc (verbatim,
  pre-Phase-10), the full Phase 7 build narrative (5 docs, every
  superseded step kept), a standalone bug-report/code-review pass, phase
  completion docs, old dashboard/daemon source (byte-identical to the
  abandoned `UmbrellaMC` prototype — reference only, never build forward
  from it), and the original moon-assistant monolithic-bot source
  UmbrellaOS was migrated from. **No git history exists for anything
  before 2026-08-15** — see section 6 above for what changed since.
