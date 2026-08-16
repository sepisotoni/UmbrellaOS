# Phase 4 — Files, Backups, DR, Scheduler, Self-Healing, Secrets: changes in this PR

Two components change: `umbrella-daemon` (file manager, backup create/restore, both wired into the
HTTP API) and `umbrella-core` (backup/schedule metadata, scheduler loop, self-healing reconciliation,
secrets encryption).

## umbrella-daemon: new files

```
internal/files/manager.go     Sandboxed file manager (path-traversal + symlink-escape tested)
internal/files/manager_test.go

internal/backup/backup.go     tar.gz create/restore (tar-slip attack tested and rejected)
internal/backup/backup_test.go
```

## umbrella-daemon: modified files

- **`internal/environment/environment.go`** — added `WorkingDir(ctx, serverID) (string, error)` to the
  `Environment` interface, so file/backup operations always operate against the container's *actual*
  current mount, never a value the daemon tracks separately and could drift from reality.
- **`internal/environment/docker.go`** — implements `WorkingDir` by inspecting the container's mounts
  for the `/data` destination.
- **`internal/transport/ws_server.go`** — new routes: `GET/PUT/DELETE /v1/servers/{id}/files/*`,
  `POST /v1/servers/{id}/backups`, `POST .../backups/{id}/restore`, `DELETE .../backups/{id}`.
- **`cmd/daemon/config.go`** — added `BackupDir` (env: `UMBRELLA_BACKUP_DIR`).

## umbrella-core: new files

```
models/automation.py                Schedule model
services/secrets_service.py         Fernet encryption for secrets at rest
services/backup_service.py          Backup metadata/orchestration
services/scheduler_service.py       Cron evaluation + capability-agnostic scheduled invocation
services/scheduler_loop.py          Background polling task, wired into main.py's lifespan
capabilities/automation.py          automation.schedule.{create,list,set_enabled,delete}

alembic/versions/014_phase4_automation.py   backups + schedules tables, servers.crash_count/last_crash_at

docs/adr/0005-backups-scheduling-self-healing.md

tests/test_secrets_service.py           6 tests
tests/test_backup_service.py            7 tests
tests/test_scheduler_service.py         14 tests
tests/test_scheduler_loop.py            2 tests
tests/test_self_healing.py              7 tests
tests/registry/test_capabilities_backup.py      5 tests
tests/registry/test_capabilities_automation.py  6 tests
```

## umbrella-core: modified files

- **`models/hosting.py`** — added `Backup` model; added `crash_count`/`last_crash_at` to `Server`.
- **`services/node_service.py`** — `register_node` now returns `(Node, plaintext_secret)` and encrypts
  before persisting; added `decrypted_signing_secret`. Breaking change to this method's signature,
  updated at every call site (capabilities/hosting.py, tests).
- **`services/server_service.py`** — `_client_for` promoted to public `client_for` (now used by
  `BackupService` too); `start_server`/`restart_server` reset `crash_count`; added
  `reconcile_server`/`reconcile_fleet` and `MAX_CONSECUTIVE_CRASHES_BEFORE_SUSPEND`.
- **`api/routers/hosting_console_ws.py`** — decrypts the node's signing secret before issuing a node
  token (previously would have issued a token from ciphertext, which the daemon would reject).
- **`capabilities/hosting.py`** — added `hosting.backup.*` (4) and `hosting.server.reconcile` /
  `hosting.fleet.reconcile`; `register_node` handler and `NodeResult` updated for the new return shape.
- **`services/roles_service.py`** — added `hosting.backup.view`, `hosting.backup.manage`,
  `automation.schedule.view`, `automation.schedule.manage`.
- **`config/settings.py`** — added `secrets_encryption_key` (no default — fails loudly if unset).
- **`main.py`** — starts/stops the scheduler background loop in the app lifespan.
- **`requirements.txt`** — added `croniter==6.2.3`; `pyotp`/`websockets`/`fakeredis` already present
  from Phase 3.
- **`tests/conftest.py`** — added a session-scoped autouse fixture generating a valid Fernet key, since
  plenty of tests exercise `NodeService` directly without going through the `client` fixture's
  per-test settings overrides.

## Verification performed

- **47 new Python tests, all passing.** Full suite re-run: **364/365** — same single pre-existing,
  unrelated failure flagged since Phase 0.
- **Daemon: 2 new packages, all tests passing with `-race`** (`internal/files`, `internal/backup`),
  full daemon suite re-verified unaffected.
- **Both Phase 4 migrations verified in isolation, both directions** (stamped to the prior revision,
  upgraded, schema inspected, downgraded, schema re-inspected) — the same technique used for every
  migration since Phase 2, since the full historical chain has a pre-existing Postgres-only
  incompatibility unrelated to any phase's own work.
- **Cross-language contract preserved**: the WS console proxy's use of `node.signing_secret` was
  updated to decrypt first — caught by grep-auditing every direct read of that field after changing
  what it stores, not assumed safe because the type didn't change.

## Three real bugs found and fixed during this phase, not glossed over

1. **`Backup.created_at` ordering was unreliable under SQLite's second-resolution timestamps** — two
   backups created in the same second (plausible for scheduler-fired jobs) couldn't be ordered by
   `created_at` or by the UUID primary key. Found by a failing test. Fixed with a Python-side
   microsecond-precision default (see ADR-0005).
2. **A hand-constructed "tar-slip via absolute path" security test asserted the wrong expectation** —
   Go's `filepath.Join` never lets an absolute-looking second argument discard the base path (unlike
   some other languages' path-join semantics), so the archive entry was already safely contained. The
   test's assumption was wrong, not the code — verified empirically with a standalone Go snippet before
   correcting the test to assert the actual (safe) behavior instead of a fabricated vulnerability.
3. **Changing `register_node`'s return type to include the plaintext secret required updating every
   direct read of `node.signing_secret`** — found and fixed the WS console proxy's now-broken usage
   (it would have issued node tokens from ciphertext, which the daemon correctly rejects) by grepping
   for every call site rather than assuming the encryption change was self-contained to
   `NodeService`/`ServerService`.

## Known follow-ups (explicitly not built now)

- Per-key secrets marking for `Server.env_overrides` — see ADR-0005.
- A dedicated `hosting.server.console_write` permission distinct from `hosting.server.view` — still
  flagged from Phase 3, unchanged this phase.
- Backup storage is local-disk-per-node only; off-node/object-storage backup destinations are a real,
  reasonable future capability, not built speculatively now.
