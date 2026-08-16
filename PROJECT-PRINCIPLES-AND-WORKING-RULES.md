# UmbrellaOS — Project Principles & Working Rules

**Every chat session working on this project reads this file before doing
anything else.** This is the "how we work" doc — separate on purpose from
`MASTER-PROJECT-STATUS-AND-HANDOFF.md` (the "where we are" doc) and
`phase10/UMBRELLAOS_MASTER_ROADMAP_v3_CONSOLIDATED.md` (the "what's
planned" doc). Read all three; this one first, because it tells you how
to treat the claims in the other two.

Consolidated from rules that previously existed only scattered across
the master doc's section 2 and individual sub-chat instructions. If a
future session finds a rule missing here that it had to rediscover the
hard way, add it here — don't let it stay tribal knowledge in one
session's memory.

---

## 1. Who's who

- **Sepiso Toni** is the sole developer and project owner. Use this name
  consistently. (An earlier package used "Johson" in one doc — confirmed
  a one-off naming inconsistency, not a different person or project. If
  you see "Johson" anywhere, it means Sepiso Toni.)
- The community server this project administers has been referred to as
  **"MOON"** in `MASTER-PROJECT-STATUS-AND-HANDOFF.md`. This has not been
  independently re-confirmed by Sepiso Toni as of this doc — if it's
  wrong or outdated, correct it here and in the master doc rather than
  letting it silently propagate.
- **There are two, historically separate codebases.** Don't conflate
  them:
  - The **current project** — everything this doc, the master doc, and
    the roadmap describe. Backend is `umbrella-core`, frontend is
    `umbrella-dashboard` (Phase 10 rewrite), Discord bot is
    `umbrella-discord`, Minecraft plugin not yet started.
  - **`UmbrellaOS.zip`** — Sepiso Toni's first, abandoned attempt at this
    same idea. ~40% of the current backend's Phase 0–6 files are
    byte-identical or line-identical carryovers from it (confirmed by
    direct file diff, not assumed) — **this carryover is being
    deliberately undone, see decision D2 below.** A real, populated
    `.env` (`SECRET_KEY`, `ADMIN_KEY`, `DATABASE_URL`) was found inside
    it and should be treated as compromised if it hasn't already been
    rotated — this zip has been uploaded to more than one AI chat
    session. Never carry files from this zip into a handoff package for
    the current project going forward.

## 2. The core discipline — non-negotiable, every session

1. **Never trust a self-report. Verify independently, every time.**
   Applies to claims from a prior session in *this* project's own
   history, and equally to claims arriving from a different sub-chat in
   a multi-chat workflow (see section 4). A document describing a diff,
   a test run, or a build result is not the diff/run/result itself.
   Concretely: fresh venv, install from `wheels/` (or real network),
   real `pytest` run, `pip check`, `pip-audit`. Fresh `npm install`,
   `npm audit`, `npm run build`, `npx tsc --noEmit`, `npm run lint` — all
   actually run, not assumed.
2. **Resolve real architecture decisions explicitly before building on
   top of them.** If a build session would have to guess at a real fork
   (data shape, permission model, storage backend, which of two
   competing docs to trust) — stop and get an explicit decision from
   Sepiso Toni first. Don't let convenience silently decide something
   with long-term consequences.
3. **Leak-check before packaging, every time, no exceptions:**
   `find . -iname ".env" -o -iname "*.db" -o -iname "*.sqlite*"` on
   whatever you're about to zip. This has caught real leaked secrets
   multiple times in this project's history (most recently: a stray
   `.env` with a placeholder-looking `DISCORD_BOT_TOKEN` in a handoff
   package assembled 2026-08-15) — treat every hit as worth inspecting,
   not assuming it's a fixture.
4. **Check for gaps a design doc assumed were already built**, rather
   than building on top of an assumption. This has happened multiple
   times (a plugin kv-storage backend, a Settings page, a Terraform
   provider) — always referenced in a scoping doc as if it existed,
   never actually checked against the real codebase until someone did.
5. **Scope discipline.** A dispatch package states exactly what's in
   scope. Don't expand it because something adjacent looks worth doing —
   flag it and ask, the way this rule itself asks you to.

## 3. Standing decisions — locked, don't re-litigate without asking

Numbered so future docs can reference them (`D1`, `D2`, ...) instead of
re-explaining the reasoning each time.

- **D1 — Phase numbering: v3 only.**
  `phase10/UMBRELLAOS_MASTER_ROADMAP_v3_CONSOLIDATED.md` is the canonical
  numbering (0–12). Two other schemes exist in this project's history —
  an older v2 scheme (used in most of `MASTER-PROJECT-STATUS-AND-HANDOFF.md`'s
  prose, e.g. its "Phase 9 (closed)" / "Phase 10" language, which is v2
  numbering) and the alembic migration filenames (`006_phase10_...`,
  `009_phase13_...`), which match neither. **Do not use v2 or
  migration-filename numbers in anything you write from now on.** Where
  you see v2 numbers in older docs, mentally (or explicitly, if editing)
  translate: v2 Phase 7 (public API + plugin SDK combined) split into v3
  Phase 7 (public API/SDKs/webhooks/Terraform) + Phase 8 (plugin
  SDK/sandbox/marketplace); v2 Phase 8 (observability) → v3 Phase 9; v2
  Phase 9 (clustering) → v3 Phase 11; v2 Phase 10 (platform maturity) →
  v3 Phase 12. v2's Phase 10 (dashboard rewrite) and v3's Phase 10
  (Unified Experience Layer) are the same phase under the same number —
  no translation needed there.
- **D2 — Backend independence.** The backend's Phase 0–6 foundation
  (currently ~40% carried over byte-for-byte from `UmbrellaOS.zip`) will
  be independently re-derived, not kept as a carryover. This is a real,
  large dispatch of its own — comparable in size to the Phase 10
  dashboard rewrite — not a drive-by cleanup. **Not started as of this
  doc.** Whoever scopes it should follow the same discipline Phase 10's
  kickoff doc did: a dedicated scoping doc, explicit sequencing, each
  step independently verified before the next starts. Until that
  dispatch happens, the carried-over code stays as-is (it's genuinely
  solid — see `cross-chat-findings/phase0-6_quality_verdict.md` for the
  quality read, though even that verdict is itself a sub-chat claim, not
  yet independently re-verified by a head chat against the current
  files).
- **D3 — Courier-workflow verification boundary.** In a multi-chat
  workflow (one head chat, multiple sub-chats each working a scoped
  package), the head chat's job is to scope dispatches and independently
  re-verify what comes back — not to write the code itself in parallel
  with a sub-chat that's already doing it. If a head chat starts
  duplicate work before checking whether a sub-chat's output already
  exists and is verified, stop and check first.
- **D4 — Real git, from this commit forward.** As of the repo's first
  commit ("Baseline: first commit this project has ever had", 2026-08-15
  — check `git log` for its current hash rather than hardcoding one here,
  since amending this file changes that commit's own hash), this project
  has a real git repository. Before this
  commit, every handoff in this project's entire history was a zip-based
  snapshot with no version-control lineage — that history is not being
  reconstructed retroactively (there's nothing to reconstruct it from),
  this commit is the seam where real history starts, not a claim that
  everything before it is now tracked. **Going forward, every session
  that changes anything commits it**, following section 6 below — no
  more "handback doc describes the diff" as the only record.
- **D5 — Two-tier PAT access: read-only for sub-chats, write only for
  the head chat.** As of 2026-08-15, the repo lives at
  `github.com/sepisotoni/UmbrellaOS`. Sub-chats get a **read-only**
  fine-grained PAT (scope: `Contents: Read-only`, this repo only) in
  their starter prompt, and clone directly instead of receiving a
  manually-assembled zip — always-current state, no staleness, and no
  more head-chat time spent filtering files into a package for the input
  side. **Only the head chat holds a read-write PAT, and only the head
  chat pushes** — a sub-chat physically cannot push straight to `main`
  even if it wanted to, which makes D3's "head chat re-verifies before
  trusting" boundary a property of the token scope, not just a rule
  someone has to remember to follow. Handback still flows back as a zip
  through Sepiso Toni to the head chat (see section 4) — that's the
  actual verification gate, and it stays. Consequence: `wheels/` being
  `.gitignore`'d (see `.gitignore`'s own comment) means a cloned sub-chat
  won't have it — default to a live `pip install -r requirements.txt`
  against the real PyPI (already network-reachable from every sandbox)
  rather than assuming bundled wheels; only reintroduce tracked wheels if
  pinned-artifact reproducibility becomes a real requirement someone
  states explicitly.

## 4. Multi-chat workflow — how packages move

This project is worked across separate chat sessions, courier-style —
this predates and is separate from the "head chat / sub-chat" pattern,
which is a further refinement of it for splitting concurrent work:

- **Handoff into a session (as of D5, 2026-08-15):** a starter prompt
  with the repo URL, a **read-only** PAT, and a pointer to which doc to
  start from — the sub-chat clones the repo itself rather than receiving
  a manually-assembled zip. Before D5, this was always a zip package;
  zips are still fine for one-off or pre-repo situations, but cloning is
  the default now — always-current, no staleness, no head-chat time
  spent filtering files for the input side. Either way, always point at
  `MASTER-PROJECT-STATUS-AND-HANDOFF.md` and
  `PROJECT-PRINCIPLES-AND-WORKING-RULES.md` for context, plus a narrower
  handoff doc for a scoped dispatch that states exactly which tasks are
  in scope and explicitly says what's *not* in scope, so a sub-chat
  doesn't wander into Phase 0–6 re-derivation while it's supposed to be
  fixing three bugs.
- **Handback out of a session:** still a zip, always — a sub-chat's
  read-only token means it can't push its own work even if it wanted to
  (D5), so this is also the actual verification checkpoint, not just a
  packaging convention. Follows the pattern every `phase10/handback/`
  doc already uses (what was built, what was verified and how, what's
  still open, gaps found stated honestly) plus the actual diff or
  modified files, and a real git commit under the sub-chat's own session
  label (section 6) if it had write access to a scratch clone — leak-
  checked before every commit and before zipping (rule 2.3 above).
- **A head chat receiving sub-chat output does not skip rule 2.1.**
  Independently re-verify — same fresh-venv/fresh-npm-install loop — and
  spot-check factual claims in any accompanying findings doc against the
  actual code before treating them as settled. Cross-chat findings docs
  get filed as reference material (e.g. this project's
  `cross-chat-findings/` folder), not silently merged into the master
  doc as fact.

## 5. Documentation map — what lives where

- **`MASTER-PROJECT-STATUS-AND-HANDOFF.md`** — the "where we are" doc.
  Full narrative history, phase-by-phase closed/open status (currently
  in v2 numbering in places — see D1 — worth a pass to normalize when
  someone's next touching it), what a new chat should do first.
- **`PROJECT-PRINCIPLES-AND-WORKING-RULES.md`** (this file) — the "how we
  work" doc. Rules, locked decisions, workflow.
- **`phase10/UMBRELLAOS_MASTER_ROADMAP_v3_CONSOLIDATED.md`** — the "what's
  planned" doc, v3 numbering, full phase-by-phase scope and definition of
  done for all 13 phases (0–12). Its own summary table is known to be
  stale in places (see `PHASE-STATUS-CORRECTED.md`, next) — treat the
  per-phase prose sections as more reliable than the summary table until
  someone reconciles them.
- **`PHASE-STATUS-CORRECTED.md`** (new, see below) — a corrected status
  read, v3 numbering, sourced only from what's been personally
  independently verified as of its own date, explicitly marking what's
  still an open/unverified claim rather than repeating the roadmap
  table's stale entries.
- **`phase10/handback/`** — per-step build narrative for the current
  phase, in order. `STEP6-VERIFICATION-ADDENDUM.md` and
  `STEP7-VERIFICATION-ADDENDUM.md` are worth reading regardless of
  whether you're touching Phase 10, as concrete examples of what the
  fresh-verify discipline actually catches.
- **`historical-reference/`** — narrative record of complications and
  false starts, kept for context, never a starting point to build from.

## 6. Version control — real git, session-labeled

The repo lives inside the handoff zip itself (`.git/` is a real,
trackable folder like any other — include it in every zip you produce
and receive, same as `wheels/` or any other package contents). There is
no hosted remote (no GitHub repo) as of D4 — this is local history that
travels with the zip, courier-style, matching how this project has
always moved state between sessions. If Sepiso Toni wants a hosted
remote later, that's its own explicit decision (rule 2.2), not something
a session should set up unprompted.

**Every session that changes anything must commit before handing back,**
using a **session label** as the git author so `git log` itself answers
"which chat produced this":

```
git config user.name "<session-label>"
git config user.email "<session-label>@umbrellaos.local"
git add -A
git commit -m "<short summary>

<body: what changed, what was verified and how, what task/decision
this is part of (cite D-numbers or a Task letter from the dispatch
doc that scoped it)>

Session: <session-label>, <date>"
```

**Session label convention:** `head-chat` for the coordinating session;
`subchat-<short-task-name>` for a dispatched sub-chat (e.g.
`subchat-bugfix-verify` for the a/b/c dispatch in
`SUBCHAT-HANDOFF-BUGFIX-AND-VERIFY.md`). Reuse the same label across a
sub-chat's own multiple commits if it makes more than one; don't invent
a new label per commit.

**What this replaces:** a handback doc is still required (section 4) —
git history doesn't replace the narrative "what was built and why," it
gives the narrative something to point at (`git show <hash>`, `git log
--oneline`) instead of the reader having to trust prose alone. Write
both.

**What this doesn't do:** this isn't a substitute for the leak-check
rule (2.3) — a leaked `.env` committed to git is *worse* than one in a
zip, since `git log` can resurface it even after a later commit removes
the file. Leak-check before every commit, not just before every zip.

