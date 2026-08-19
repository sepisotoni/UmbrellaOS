# UmbrellaOS — Phase 12 Step 1B: Feature Flags

Read `CLAUDE.md` then `PROJECT-PRINCIPLES-AND-WORKING-RULES.md` first.
Read-only repo access — hand back a zip, don't push.

Repo: `https://github.com/sepisotoni/UmbrellaOS`
Read-only PAT: [READ-ONLY-PAT — provided by Sepiso Toni in starter prompt]
Clone: `git clone https://x-access-token:<PAT>@github.com/sepisotoni/UmbrellaOS.git`
Current tip: `085688c`

This is a backend-only dispatch. Don't touch `umbrella-dashboard-CURRENT/`,
`minecraft-plugin/`, or anything Phase 11/13 related.

Parallel dispatch running: `DISPATCH-P12-S1A-CI-HEALTH.md` — that
sub-chat is building CI/CD workflows and extending `/health`. No file
overlap with this dispatch.

---

## Context — read before writing anything

- `umbrella-core-CURRENT/models/setting.py` — the existing `Setting`
  model and `__tablename__ = "settings"`. Feature flags are **not**
  settings — don't piggyback on this table. They need their own model.
- `umbrella-core-CURRENT/capabilities/` — read 2-3 existing capability
  files (e.g. `webhooks.py`, `automation.py`) to understand the
  `@capability` decorator pattern before writing your own. Every new
  capability must follow this pattern — CLI+API+AI-reachable from one
  declaration.
- `umbrella-core-CURRENT/alembic/versions/028_plugin_execution_records.py`
  — the current last migration. Your new migration is `029_feature_flags.py`.
  Check the `down_revision` chain before writing it.
- `umbrella-core-CURRENT/models/__init__.py` — export your new model here.
- `umbrella-core-CURRENT/api/routers/` — read `settings.py` as a style
  reference for a simple CRUD router.

---

## What to build

A feature flag system: named boolean flags, owner-managed, stored in
Postgres, readable by any service in umbrella-core that needs to gate
behavior.

### 1. Model — `models/feature_flag.py`

```
FeatureFlag:
  id: str (UUID, PK)
  name: str (unique, indexed) — machine-readable key, e.g. "anticheat.enabled"
  enabled: bool (default False)
  description: str (human-readable, what this flag gates)
  created_at: datetime (timezone=True)
  updated_at: datetime (timezone=True)
```

Use `datetime.now(timezone.utc)` for defaults — not `datetime.utcnow()`
(that's a known bug pattern in this codebase, see `CRITICAL-FINDINGS-2026-08-17.md`
item #7's timezone notes).

Export from `models/__init__.py`.

### 2. Migration — `alembic/versions/029_feature_flags.py`

`create_table('feature_flags', ...)` with all columns above. Check
`down_revision` against `028_plugin_execution_records.py` before writing.
Include a `downgrade()` that drops the table.

### 3. Service — `services/feature_flag_service.py`

```python
async def get_flag(db, name: str) -> bool:
    """Returns the flag's enabled state, or False if the flag doesn't exist."""

async def set_flag(db, name: str, enabled: bool, description: str = "") -> FeatureFlag:
    """Create or update a flag by name. Upsert semantics."""

async def list_flags(db) -> list[FeatureFlag]:
    """Return all flags."""

async def delete_flag(db, name: str) -> bool:
    """Delete a flag by name. Returns True if it existed, False if not."""
```

Keep it simple — no caching layer, no Redis, just Postgres. Caching is
a future optimization if flag reads become a bottleneck.

### 4. Capability — `capabilities/feature_flags.py`

Register these capabilities through the capability registry (follow the
`@capability` pattern from existing files):

- `feature_flags.get` — get a single flag's state by name
- `feature_flags.set` — create or update a flag (requires `feature_flags.manage` permission)
- `feature_flags.list` — list all flags (requires `feature_flags.view` permission)
- `feature_flags.delete` — delete a flag (requires `feature_flags.manage` permission, mark `destructive=True`)

### 5. Router — `api/routers/feature_flags.py`

REST endpoints (all require admin key auth):
```
GET  /api/v1/feature-flags          — list all flags
GET  /api/v1/feature-flags/{name}   — get one flag by name
POST /api/v1/feature-flags          — create/update a flag
DELETE /api/v1/feature-flags/{name} — delete a flag
```

Register the router in `main.py` (follow the existing pattern — import
and `app.include_router(...)`).

### 6. Wire into existing anticheat toggle (if clean to do so)

`GrimBridge.java` in the plugin currently ignores an `anticheat.enabled`
toggle — that's flagged as an open item in the Phase 13 dispatch. On the
**backend side only**: seed a `feature_flags` row for `"anticheat.enabled"`
with `enabled=True` as a default in the migration's `upgrade()` (an
`op.execute(INSERT ...)` after `create_table`). The plugin-side wiring
is out of scope here — just get the flag into the DB so it exists when
the plugin eventually checks it.

---

## Testing

Write tests in `tests/test_feature_flags.py`. Cover:
- CRUD via the router (create, read, list, update, delete)
- `get_flag` returns `False` for a nonexistent flag (not a 404, not an
  exception — just False, that's the contract)
- Permission enforcement (flags.view vs flags.manage)
- The `anticheat.enabled` seed row exists after migration runs

Run `pytest tests/test_feature_flags.py -v` and include output in handback.

---

## Explicitly out of scope

- Dashboard UI for feature flags — separate dispatch later
- Redis caching of flag values
- Per-user or per-tenant flags — this is global flags only
- Anything touching `minecraft-plugin/` (plugin-side anticheat toggle
  wiring is Phase 13's job)

---

## Deliverable for handback

Zip containing:
1. All new/modified files in full.
2. File manifest.
3. Handback doc:
   - Status of each item (done / partial / blocked).
   - `pytest tests/test_feature_flags.py -v` output.
   - Full test count before/after (e.g. "869 → 884 passing").
   - Anything noticed outside scope, flagged not acted on.
4. Leak check: `find . -iname ".env" -o -iname "*.db" -o -iname "*.sqlite*"`

Session label for any scratch clone commits: `subchat-p12-s1b`.
