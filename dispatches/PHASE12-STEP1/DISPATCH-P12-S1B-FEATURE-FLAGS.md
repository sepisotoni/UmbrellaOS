# Phase 12 S1B — Feature Flags

Read-only repo access. Hand back a zip, don't push.
Repo: `https://github.com/sepisotoni/UmbrellaOS`
Read-only PAT: [READ-ONLY-PAT — provided by Sepiso Toni in starter prompt]

## Files to read before writing anything

- `umbrella-core-CURRENT/models/setting.py` — style reference for a simple model
- `umbrella-core-CURRENT/models/__init__.py` — add your export here
- `umbrella-core-CURRENT/capabilities/webhooks.py` — reference for the `@capability` decorator pattern
- `umbrella-core-CURRENT/api/routers/settings.py` — style reference for a CRUD router
- `umbrella-core-CURRENT/alembic/versions/028_plugin_execution_records.py` — get `revision` id for your `down_revision`
- `umbrella-core-CURRENT/main.py` — where to register your new router (follow existing pattern)

That's it. Don't read anything else unless you hit something unexpected.

---

## What to build

### `models/feature_flag.py`
```python
class FeatureFlag(Base):
    __tablename__ = "feature_flags"
    id: str (UUID PK)
    name: str (unique, indexed)      # e.g. "anticheat.enabled"
    enabled: bool (default False)
    description: str
    created_at / updated_at: DateTime(timezone=True)
```
Use `datetime.now(timezone.utc)` for defaults — not `datetime.utcnow()`.
Export from `models/__init__.py`.

### `alembic/versions/029_feature_flags.py`
`create_table('feature_flags', ...)`. Set `down_revision` from 028.
In `upgrade()`, after `create_table`, seed one row:
`op.execute("INSERT INTO feature_flags (id, name, enabled, description, created_at, updated_at) VALUES (..., 'anticheat.enabled', true, 'Enable GrimAC anticheat bridge reporting', now(), now())")`
Include `downgrade()` that drops the table.

### `services/feature_flag_service.py`
```python
async def get_flag(db, name: str) -> bool          # False if not found, never raises
async def set_flag(db, name: str, enabled: bool, description: str = "") -> FeatureFlag  # upsert
async def list_flags(db) -> list[FeatureFlag]
async def delete_flag(db, name: str) -> bool       # True if existed
```
No caching. Just Postgres.

### `capabilities/feature_flags.py`
Register via `@capability` pattern:
- `feature_flags.get` — get flag state by name
- `feature_flags.set` — create/update (permission: `feature_flags.manage`)
- `feature_flags.list` — list all (permission: `feature_flags.view`)
- `feature_flags.delete` — delete (permission: `feature_flags.manage`, `destructive=True`)

### `api/routers/feature_flags.py`
```
GET    /api/v1/feature-flags          # list all, admin auth
GET    /api/v1/feature-flags/{name}   # get one
POST   /api/v1/feature-flags          # create/update
DELETE /api/v1/feature-flags/{name}   # delete
```
Register in `main.py`.

---

## Tests — `tests/test_feature_flags.py`

Cover:
- CRUD via the router (create, read, list, update, delete)
- `get_flag` returns `False` for a nonexistent flag (not an exception)
- Permission enforcement (view vs manage)

Run `pytest tests/test_feature_flags.py -v` and include output in handback.
Don't run the full suite.

---

## Deliverable

Zip with:
1. All new/modified files in full
2. File manifest
3. Short handback doc: status of each item, `pytest tests/test_feature_flags.py -v` output, test count added, anything noticed outside scope
4. Leak check: `find . -iname ".env" -o -iname "*.db" -o -iname "*.sqlite*"`
