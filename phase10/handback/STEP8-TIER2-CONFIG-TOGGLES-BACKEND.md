# Step 8 — Tier 2 config toggles: backend done, frontend not started

Decision 2 is resolved: **Option A** (per-plugin auto-generated capability),
Sepiso Toni's explicit call, made for long-term customizability — per-plugin
permission grants matter more as the marketplace grows, and it's
consistent with every other `plugin.<id>.*` pattern already built
(`dashboard_ui_slots`, `discord_commands`, Tier 3's page capabilities).
See `umbrella-core/docs/design/phase10-decision2-config-write-capability-shape.md`
(now marked DECIDED at the top) for the full tradeoff writeup.

## Backend — done, independently verified, 838/838

### A real gap found and fixed along the way
The design docs (`DASHBOARD-PLUGIN-UI-SCOPING.md`'s Tier 2 section, and
the manifest's own `storage: "kv"` default) assumed a plugin key-value
storage backend already existed to write config values into. **It
didn't** — checked the whole codebase before starting, no such table,
model, or service existed anywhere, despite being referenced since
Phase 7/8. Built it as prerequisite infrastructure, not scope creep:

- `models/plugin_kv.py` — `PluginKvEntry` (plugin_id, key, value_json),
  unique on (plugin_id, key). Global per plugin, not per-user (contrast
  `DashboardLayout`, which is per-user by design).
- `services/plugin_kv/service.py` — plain CRUD, upsert-on-set, mirrors
  `services/dashboard_layout/service.py`'s split exactly.
- `alembic/versions/027_plugin_kv_entries.py` — the migration.

### Tier 2 itself
- `services/plugins/manifest.py` — `ConfigFieldDecl` (boolean-only for
  now, `_ALLOWED_CONFIG_FIELD_TYPES = {"boolean"}`, per the scoping doc's
  explicit "don't build speculatively" instruction) and `config_fields`
  on `PluginManifest`, strictly opt-in.
- `services/plugins/registration.py` —
  `register_plugin_config_capabilities()`. Auto-creates the per-plugin
  `plugin.<id>.config.write` permission (idempotent get-or-create,
  mirrors `roles_service.py`'s own dynamic-Permission-row pattern — the
  only other place in this codebase does this). Registers
  `plugin.<id>.config.set`/`.config.get` as **pure platform-owned
  handlers — no sandbox involved at all**, unlike every other
  `plugin.<id>.*` capability in this codebase. That boundary is the
  actual point of Option A: a plugin can't write an arbitrary key or
  value shape through this, only a key it declared, type-checked.
- `services/plugins/marketplace_service.py` — `configurable_plugins()` +
  `ConfigurablePluginEntry`, mirroring `pages()`'s exact shape. Needed
  because there's no Settings page yet for the frontend to already know
  which installed plugins have anything to show (see below).
- `capabilities/marketplace.py` —
  `marketplace.install.configurable_plugins`, gated by the existing
  `marketplace.install.view` permission, same discovery-capability
  pattern as `.pages`/`.dashboard_slots`.
- Wired into `MarketplaceService.install()`, into the same
  `dry_run_registry` as `register_plugin_capabilities` so a manifest
  error in either half aborts the whole install atomically.
  `uninstall()` needed zero changes — already fully generic over
  `registered_capability_names`.

### Tests — 19 new (838 total, was 819 before this session)
Manifest validation (6): opt-in default, boolean accepted, unsupported
type rejected, bad key shape rejected, duplicate keys rejected, no
capability cross-reference required (unlike `dashboard_ui_slots`).

Service layer (10): both capabilities registered together, permission
row actually created, no-config-fields is a true no-op, real
set→get round trip through the actual handlers (not mocked), default
value fallback when never set, undeclared-key rejected, reinstall
doesn't duplicate the permission row, uninstall removes both
capabilities, `configurable_plugins()` empty/non-empty cases.

REST-level (3): full round trip through real HTTP invoke calls, a
`member`-role rejection for `.set` (proving the specific per-plugin
permission gates it, not just "not an admin"), and — the concrete
behavioral difference Option A promised over Option B — a role granted
*only* `marketplace.install.view` can read config but still can't write
it, checked with a real permission grant via the DB, not asserted from
the CapabilitySpec alone.

**Verification: fresh venv, fresh install, real `pytest -q` run —
838/838. `pip check` and the dependency scanner both clean. No new
dependencies required — `requirements.txt` diffed against the last
verified state and is unchanged.**

## Frontend — not started

This is the real gap in this package. While scoping the Settings page I
found the same "assumed infrastructure doesn't exist" pattern as the
backend kv gap: **`DASHBOARD-PLUGIN-UI-SCOPING.md` says Tier 2 toggles
"render inline in the existing Settings page,"** but this dashboard
rewrite has no Settings page at all — never built in any prior step.
The existing `/marketplace/[pluginId]` route (Tier 3) also isn't the
right home: it strictly 404s for any plugin that didn't declare a Tier 3
`page`, and most config-only plugins won't have one.

**What the next session needs to build:**
1. A new route — `app/(dashboard)/settings/page.tsx` (or similar; not
   yet decided which nav slot it belongs in — check `sidebar.tsx`'s
   current nav structure before picking).
2. A server-only fetch helper (`lib/plugin-config.ts`, following
   `lib/marketplace-pages.ts`'s exact pattern already in this repo) that
   calls `marketplace.install.configurable_plugins` to list which
   plugins to render, then `plugin.<id>.config.get` per plugin for
   current values.
3. A same-origin API route (`app/api/plugin-config/route.ts`, following
   `app/api/dashboard-layout/route.ts`'s exact pattern) so the toggle's
   write goes through `plugin.<id>.config.set` without the bearer token
   ever touching client JS — same invariant every other write path in
   this app already holds.
4. A small `'use client'` toggle leaf component, following
   `dashboard-customizer.tsx`'s pattern from step 6 — the only prior
   client-side interactive settings UI in this codebase.
5. Nav wiring so the Settings page is actually reachable.
6. The full verification loop this project's discipline requires before
   calling it done: `npm audit`, `npm run build`, `npx tsc --noEmit`,
   `npm run lint` — all run for real, not self-reported. Every prior
   step that skipped this found real bugs when it was finally run (see
   `STEP6-VERIFICATION-ADDENDUM.md` and `STEP7-VERIFICATION-ADDENDUM.md`
   for exactly what that loop has caught so far: a critical Next.js RCE,
   several genuine React bugs, a missing lint config, a dependency
   version-skew build break). Don't skip it here either.

## What's left for the whole project after this

1. **This Settings page frontend** — the one concrete remaining build
   item, fully scoped above.
2. **Marketplace listing/install UI** (`app/marketplace/page.tsx` itself
   — browse/publish/install/uninstall from the dashboard) — still the
   step-2 placeholder, never assigned to any step. Worth deciding if
   it's in scope for "done."
3. **Minecraft plugin** — separate track, fully scoped in the original
   project handoff, not started. One small open decision of its own
   (how the plugin authenticates ban-checks against the RBAC-gated
   punishment endpoint).
4. **Housekeeping, low priority:** `anticheat_service.py` dead code +
   zero test coverage; `middleware.ts` → `proxy` naming convention
   deprecation warning (non-blocking, Next 16.3 still supports the old
   convention).
5. **No manual/browser runtime testing has happened anywhere in Phase
   10.** Every check across every step has been static — tests, build,
   lint, audit. Nobody has clicked through the actual dashboard in a
   browser yet. Worth doing before calling the whole phase done.
