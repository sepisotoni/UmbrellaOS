# Phase 0 — Capability Registry: changes in this PR

## New files

```
registry/__init__.py             Public exports: capability, CallContext, registry, CapabilitySpec
registry/spec.py                 CapabilitySpec — declared metadata for one capability
registry/context.py              CallContext — actor identity/permissions for one call
registry/audit.py                Audit-row writer, reuses the existing AuditLog model
registry/registry.py             CapabilityRegistry — the single call path (auth, validate, invoke, audit)
registry/decorator.py            @capability decorator
registry/adapters/__init__.py
registry/adapters/rest.py        Generic REST adapter: GET/POST /api/v1/capabilities...
registry/adapters/cli.py         Typer-based CLI adapter, builds command tree from the registry
registry/README.md               Developer guide for declaring/calling capabilities

capabilities/__init__.py         Imports every capability module (mirrors models/__init__.py)
capabilities/system.py           platform.system.whoami, platform.audit.search

services/permission_resolution.py   Extracted, shared permission-resolution logic

cli.py                           CLI entry point (`python cli.py <command>`)

docs/adr/0001-capability-registry.md   Architecture decision record for this phase

tests/registry/__init__.py
tests/registry/conftest.py                 Shared test helper: session_headers_for_role
tests/registry/test_registry_core.py       12 unit tests — registration, RBAC, validation, audit
tests/registry/test_capabilities_system.py  8 integration tests — real REST calls, real DB
tests/registry/test_cli_adapter.py          5 tests — Typer CliRunner against a throwaway registry
```

## Modified files

- **`main.py`** — imports `capabilities` (registers everything) and mounts
  `registry.adapters.rest.router`.
- **`api/dependencies/permissions.py`** — `_load_role_permissions` now delegates to
  `services.permission_resolution.resolve_user_permissions` instead of duplicating the role/permission
  query inline; keeps its existing request-scoped caching behavior unchanged.
- **`api/routers/audit.py`** — both routes now delegate to the `platform.audit.search` capability via
  `registry.call()` instead of implementing the query themselves. Response shape is unchanged — the
  full pre-existing `tests/test_audit.py` suite (10 tests) passes against this file with zero
  modifications to that test file.
- **`requirements.txt`** — added `typer==0.16.0` (pinned specifically to avoid a
  `typer==0.15.1` + `click>=8.2` incompatibility hit and confirmed during this phase's testing, not a
  hypothetical concern).

## Verification performed

- Full existing test suite run before and after: **224/225 passing**, unchanged from before this PR.
  The one failure (`tests/test_settings.py::test_sensitive_settings_are_masked`) is confirmed
  pre-existing — reproduced identically against an untouched copy of the prior codebase — and is
  unrelated to this phase's scope (settings-value masking, not the registry).
- New tests added by this phase: **25**, all passing (12 registry-core unit tests, 8 REST integration
  tests, 5 CLI adapter tests).
- `python cli.py list`, `python cli.py platform system whoami --help`, and a live invocation were run
  manually against the built app to confirm the CLI adapter works end-to-end, not just under test
  mocks.
- `main.py` imports cleanly and mounts 98 routes including the two new capability routes, confirmed by
  direct import rather than assumed.

## Known follow-ups (explicitly not built now — see ADR-0001 and registry/README.md)

- AI Tool Registry adapter — Phase 5.
- Discord adapter — Phase 5/6.
- Resource-styled REST path aliases — deferred, layered on top later without a contract change.
- Per-user CLI authentication — Phase 3 dependency (needs a login/session capability that doesn't
  exist yet).
- Pre-existing settings-masking bug (`test_sensitive_settings_are_masked`) — flagged, not fixed; out
  of this phase's scope.
