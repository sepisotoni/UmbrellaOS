# Read this first — every session, no exceptions

You're joining an existing, long-running project. It has survived
dozens of chat-session handoffs because of a specific discipline. Skim
this file, then follow its pointers in order — don't start writing
code or trusting a status claim before you have.

## The one rule that matters most

**Never trust a self-report. Verify independently, every time.** Not
this file's claims, not the master doc's claims, not a prior sub-chat's
"X passed." A document describing a test run is not the test run. Run
it yourself. Full detail: `PROJECT-PRINCIPLES-AND-WORKING-RULES.md`
section 2 — read that file in full before doing anything else.

## Read in this order

1. **`PROJECT-PRINCIPLES-AND-WORKING-RULES.md`** — the rules. Read in
   full. Tells you how to treat every other claim in this repo.
2. **`MASTER-PROJECT-STATUS-AND-HANDOFF.md`** — the narrative status.
   Some of it is dated; where it conflicts with `PHASE-STATUS-CORRECTED.md`,
   the latter wins (it's sourced — every line says whether it was
   personally checked or is still an unverified claim).
3. **`PHASE-STATUS-CORRECTED.md`** — actual current phase-by-phase
   status.
4. **`CRITICAL-FINDINGS-2026-08-17.md`** — open, unresolved bugs that
   are more urgent than any new feature work. Read before starting
   Phase 11/12 or anything else.

## Known open items as of this file's writing

- **Phase 8 status is disputed** — one doc says the debugger/profiler/
  visualizer is done, `PHASE-STATUS-CORRECTED.md` says it searched and
  found nothing. Not resolved. Check the actual code before trusting
  either claim.
- **Test suite has never run with Redis genuinely reachable** in most
  of this project's history — a "passed" claim from before this was
  discovered needs re-checking under real Redis, not assumed valid.
- **Migration chain can't bootstrap a fresh database** — several real
  models are never created by any migration. See the critical-findings
  doc.
- **Minecraft plugin phase numbering** — undecided whether it's Phase
  13 or stays unnumbered. Ask Sepiso Toni, don't guess.
- **Codespace sub-chat write access** — a codespace-based sub-chat has
  pushed directly to `main` twice, bypassing the normal read-only-PAT
  boundary. Open process question, not yet resolved with Sepiso Toni.

## Who you're working with

Sepiso Toni is the sole developer and owner. Casual, heavily
abbreviated typing — don't mirror it, don't be thrown by it. Wants
directness, will push back on rounding up or hiding a gap. Runs a
multi-chat courier workflow: one head chat with write access,
scoped sub-chat dispatches, independent re-verification of everything
that comes back.

## Don't

- Don't guess at a real architecture decision (data shape, permission
  model, storage backend) — stop and ask.
- Don't expand a dispatch's scope because something adjacent looks
  worth fixing — flag it, ask, stay scoped.
- Don't carry anything forward from `UmbrellaOS.zip` or the
  `UmbrellaMC` prototype — abandoned lineage, explicitly being
  independently re-derived (D2), not extended.
- Don't treat a stale doc's summary table over its own prose sections,
  or an old doc over a newer, more-sourced one — check `git log` and
  file dates when two docs disagree.
