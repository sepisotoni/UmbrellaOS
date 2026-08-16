# UmbrellaOS — Sub-chat dispatch: Phase 10 completion (marketplace UI + manual testing)

Read this completely first, then `MASTER-PROJECT-STATUS-AND-HANDOFF.md`,
then `PROJECT-PRINCIPLES-AND-WORKING-RULES.md` — the second doc is now
the actual "how this project works" reference; read it before starting,
not as an afterthought. This dispatch follows its rules exactly
(session-labeled git commits, leak-check before every commit, verify
independently, don't expand scope).

**Session label for your git commits: `subchat-phase10-completion`.**

This closes out the last two open items in Phase 10 (v3 numbering — see
`PHASE-STATUS-CORRECTED.md` for the full current status of every phase).
Everything else in Phase 10 is done. Two tasks, both in scope; nothing
else.

---

## Task A — Marketplace listing/install UI

`umbrella-dashboard-CURRENT/app/(dashboard)/marketplace/page.tsx` is
currently a 5-line placeholder. The backend side is fully built and
tested — this is purely a frontend build against existing, real
capabilities:

- `marketplace.listing.list` — every plugin in the catalog
  (`PluginListingResult`: `plugin_id`, `name`, `author`, `description`,
  `latest_version`)
- `marketplace.listing.versions` — every published version of one plugin
  (`PluginVersionResult`: `plugin_id`, `version`, `sha256_hash`,
  `published_at`)
- `marketplace.install.list` — every plugin currently installed
  (`PluginInstallResult`: `plugin_id`, `installed_version`,
  `registered_capability_names`)
- `marketplace.install.install` — install or update
  (`{plugin_id, version}` → `PluginInstallResult`)
- `marketplace.install.uninstall` — uninstall (`{plugin_id}` →
  `{uninstalled: bool}`)

All five are real, in `umbrella-core-CURRENT/capabilities/marketplace.py`
— read the full file, not just the params/result models above, before
building against it.

**Build, following this app's own established conventions — same
patterns `lib/marketplace-pages.ts`, `lib/plugin-config.ts`,
`lib/dashboard-layout.ts` already use:**
1. A server-only fetch helper (`lib/marketplace-listings.ts` or extend
   an existing lib file — your call, match existing file-organization
   conventions rather than inventing a new one) wrapping
   `marketplace.listing.list` and `marketplace.install.list`, same
   catch-and-degrade-to-empty-array posture every other list fetch in
   this app already uses.
2. The page itself (`app/(dashboard)/marketplace/page.tsx`) — replace
   the placeholder. Show the catalog, mark which plugins are already
   installed (cross-reference the two lists), show install/uninstall
   actions.
3. Install/uninstall are `destructive: true` capabilities server-side —
   the write actions need a same-origin API route (same pattern as
   `app/api/plugin-config/route.ts` and `app/api/dashboard-layout/route.ts`:
   browser never holds the bearer token, route reads the session cookie
   server-side and forwards the call) plus a `'use client'` leaf
   component for the actual button/confirm interaction (same scoping
   rule section 6 in `PROJECT-PRINCIPLES-AND-WORKING-RULES.md`
   references — client components stay minimal, leaves only).
4. Gate the install/uninstall actions on `marketplace.install.manage`
   (via `hasPermission`, same pattern the Settings page's `canWrite`
   already established for `plugin.<id>.config.write` — read
   `app/(dashboard)/settings/page.tsx` before building this, it's the
   most recent example of this exact permission-gating shape in this
   codebase).
5. Install is a real, meaningful action (it runs plugin manifest
   validation and sandbox setup server-side, not instant) — show a
   pending/loading state, don't assume it resolves instantly the way a
   config toggle does.

**What's explicitly NOT in scope:** `marketplace.listing.publish` (a
plugin author uploading a new plugin zip) — that's a separate, larger
UI (file upload, zip validation feedback) and isn't part of "Phase 10 is
done." Confirm this is still correctly out of scope if you're unsure,
don't just build it because it's adjacent.

**Verification for Task A:** the standard frontend loop — fresh `npm
install`, `npm audit`, `npx tsc --noEmit`, `npm run lint`, `npm run
build` — all run for real, all clean, before handback.

---

## Task B — First real manual/browser testing pass

Every check on Phase 10 so far, across every step including this
package's own baseline verification, has been static: tests, build,
lint, tsc, audit. **Nobody has ever actually loaded this dashboard in a
browser and clicked through it.** Prior steps' own verification
addenda (`phase10/handback/STEP6-VERIFICATION-ADDENDUM.md`,
`STEP7-VERIFICATION-ADDENDUM.md`) found real bugs static checks missed —
there's no reason to assume this phase is different.

**The real blocker, solve this first:** the dashboard's session
(`lib/session.ts`) is established via real Discord OAuth
(`app/api/auth/start` → Discord's real authorize URL → `app/api/auth/callback`).
A sandboxed test run can't complete a real Discord redirect. You need a
way to get a valid session without one.

**Head chat's proposed approach, follow it unless you find a real
problem with it (and say so if you do, don't just build it anyway):**
add a `DEBUG`-gated dev-only capability,
`auth.dev.mint_test_session` or similar, that creates a `Session` row
for a specified role directly (no Discord round-trip), returning a token
the same shape `discord_callback` already produces. Gate it exactly the
way the existing `X-Admin-Key` bypass in `api/dependencies/permissions.py`
is gated and documented (that module's own docstring is your reference
for how this codebase already handles "explicit, off-by-default,
clearly-documented bypass for exactly this kind of need") — must be a
hard no-op unless a `DEBUG`/`ENVIRONMENT=development`-style setting is
explicitly true, and the module's docstring must say plainly why it
exists and that it must never be reachable in production. This is a new
capability, not modifying an existing one — add real tests for it
(including a test that it's unreachable when the gating flag is false),
same as anything else in this codebase.

**Then, the actual test pass:**
1. Bring up a real backend: fresh venv, offline wheels install, a real
   (sqlite is fine for this — check `database_url_sync`'s sqlite
   fallback in `config/settings.py`) migrated DB via `alembic upgrade
   head`, `uvicorn main:app` running.
2. Bring up the dashboard against it: `npm run build && npm run start`
   (test the production build, not `next dev` — that's what actually
   ships).
3. Use the dev-session-mint capability to get a valid session cookie for
   at least two roles: one with broad permissions (owner/admin-shaped)
   and one narrow one (e.g. `marketplace.install.view` but not `.manage`,
   to actually exercise the read/write UX distinction Task B of the
   *previous* dispatch built into the Settings toggles — this is a good
   chance to confirm that actually works end-to-end, not just in unit
   tests).
4. Click through (or drive via a headless browser tool if one's usable
   in your sandbox — try `npx playwright install` first and report
   whether it actually works; this project's network access has been
   restricted before, so don't assume it'll succeed) every route:
   `/dashboard`, `/marketplace` (the page you just built in Task A),
   `/marketplace/[pluginId]` for at least one installed plugin,
   `/settings`, `/topology`, `/login`, plus the logout flow.
5. **If headless browser tooling genuinely isn't reachable from your
   sandbox, don't silently skip this task** — fall back to `curl`-based
   smoke tests against every route (real HTTP status codes, checking
   the actual returned HTML for the expected content, not just "200 OK")
   and say explicitly in your handback that this is a reduced substitute
   for real click-through testing, not equivalent to it.

**Deliverable for Task B:** a written test-pass report — what you
clicked through (or curl'd), what worked, what didn't, any real bugs
found (fix small ones inline, same as the bugfix dispatch did; flag
anything bigger rather than silently expanding scope to fix it).

---

## What to hand back

Same structure as the last dispatch: a handback doc
(`SUBCHAT-HANDBACK.md`), diffs or modified files for both projects, and
Task B's test-pass report as its own doc. Commit your work with
`git config user.name/email` set to `subchat-phase10-completion` before
handing back (see `PROJECT-PRINCIPLES-AND-WORKING-RULES.md` section 6) —
**leak-check before every commit, not just before zipping**, same
section, same rule. This package's own backend previously had a test
that silently wrote a real `.env` to disk on every `pytest` run
(`tests/test_settings.py`, fixed 2026-08-15) — if your leak-check ever
turns up a `.env` unexpectedly, don't assume it's an upload leak before
checking whether something you're running wrote it, the way that one
did.
