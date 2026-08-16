# Phase 2 — Hosting Control Plane: changes in this PR

Two components change in this phase: `umbrella-core` (the new hosting domain) and a small addition to
`umbrella-daemon` (the `Create`/`Remove` routes Phase 1 explicitly deferred, now built against a real
caller).

## umbrella-core: new files

```
models/hosting.py                      Node, ServerTemplate, Allocation, Server
alembic/versions/012_hosting_domain.py  Migration for the four new tables

services/node_auth_service.py          Signed node-token issuance (Python counterpart to the
                                        daemon's internal/auth) — verified cross-language compatible
services/daemon_client.py              HTTP client for a node's daemon (create/start/stop/restart/
                                        kill/state/stats/remove)
services/node_service.py               Node registration/lifecycle
services/server_template_service.py    Versioned server templates
services/allocation_service.py         Port allocation reservation/binding
services/server_service.py             Orchestrates Node + Template + Allocations + DaemonClient
                                        into full server lifecycle

capabilities/hosting.py                16 capabilities: node.{register,list,get},
                                        template.{create,list}, allocation.{create,list_free},
                                        server.{create,get,list,start,stop,restart,kill,stats,delete}

docs/adr/0003-hosting-domain.md        Architecture decision record for this phase

tests/test_node_auth_service.py            9 tests
tests/test_daemon_client.py                9 tests
tests/test_hosting_services.py             17 tests
tests/registry/test_capabilities_hosting.py 10 tests
```

## umbrella-core: modified files

- **`models/__init__.py`** — registers the four new hosting models for Alembic discovery.
- **`services/roles_service.py`** — adds 9 `hosting.*` permission keys to `DEFAULT_PERMISSIONS`
  (owner/admin get them automatically via `ALL_PERMISSION_KEYS`); kept namespaced distinctly from the
  pre-existing `server.control` key (see ADR-0003 on why these aren't unified).
- **`requirements.txt`** — added `pyjwt==2.7.0` (pinned to the version actually verified in this
  environment).

## umbrella-daemon: modified files (small addition to the Phase 1 deliverable)

- **`internal/transport/ws_server.go`** — added `POST /v1/servers/{id}` (create) and
  `DELETE /v1/servers/{id}` (remove) routes, built against this phase's actual `ContainerSpec` source
  (a template + node + allocations) rather than guessed at speculatively in Phase 1.
- **`internal/transport/ws_server_test.go`** — 5 new tests for the create/remove handlers
  (`fakeEnvironment` extended with configurable `createFn`/`removeFn` instead of hardcoded no-ops).

## Verification performed

- **45 new Python tests, all passing**: 9 node-auth, 9 daemon-client, 17 hosting-service, 10 hosting-
  capability REST integration. Full existing suite re-run: **269/270 passing** — the one failure is
  the same pre-existing, unrelated bug flagged in Phase 0 (confirmed against an untouched copy of the
  original code, still not fixed here as it's out of this phase's scope).
- **5 new Go tests, all passing** (91 total across the daemon now, up from 76), full daemon suite
  re-verified with `-race` after the change.
- **The migration was actually run**, not just written: applied and rolled back cleanly against SQLite
  in isolation (stamped to the prior revision first, since the full historical migration chain has a
  pre-existing Postgres-only incompatibility unrelated to this phase — confirmed by reproducing it
  against an untouched copy of the original migrations).
- **Cross-language token compatibility was verified for real, not assumed**: a token issued by
  `services/node_auth_service.py` was fed into an actual compiled build of the daemon's
  `internal/auth.Issuer.VerifyNodeToken` and confirmed to verify correctly, then the throwaway
  verification program was deleted — it's not part of the shipped deliverable, the fact that it was
  run once during development is recorded here and in ADR-0003.
- **The CLI's zero-extra-code promise from Phase 0 was checked against a second real domain**: all 16
  hosting capabilities appear in `python cli.py list` with correct destructive/irreversible flags, and
  `python cli.py platform system whoami` was actually run and returned a correct result — with no
  CLI-specific code written for the hosting domain at all.

## A real bug found and fixed during this phase, not glossed over

`NodeError`, `ServerTemplateError`, `AllocationError`, and `ServerError` were initially written as
plain `Exception` subclasses carrying their own `status_code` attribute — which does nothing on its
own, since only `AppException` subclasses are recognized by `api/middleware/errors.py`'s global
handler. Every one of these would have collapsed into a generic 500 "Internal server error," losing
the specific 404/409/502 status and message. Caught by reading `errors.py` before assuming the
attribute would be respected, not by a failing test (there wasn't one yet) — fixed by making all four
inherit from `AppException`, and then a regression test
(`test_register_duplicate_node_returns_409_not_500`, `test_get_missing_node_returns_404_not_500`) was
added specifically to guard against this exact mistake recurring.

## Known follow-ups (explicitly not built now)

- Event bus / WebSocket gateway wiring — deferred to land alongside Phase 3's dashboard, which is the
  first real consumer (see ADR-0003).
- Per-allocation container-port remapping — a real, flagged gap; the current convention is
  host-port-equals-container-port (see ADR-0003).
- Full REST-level integration tests for the daemon-calling server-lifecycle capabilities
  (create/start/stop/restart/kill/stats) — covered thoroughly at the service layer with an injected
  fake `DaemonClient` instead; the capability layer doesn't currently expose a seam for HTTP-mocking a
  node's daemon URL through the full REST stack, which would be a reasonable enhancement but wasn't
  built speculatively for this phase.
