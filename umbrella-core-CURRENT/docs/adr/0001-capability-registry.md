# ADR-0001: The Capability Registry as UmbrellaOS's single business-logic call path

**Status:** Accepted, implemented (Phase 0).

## Context

UmbrellaOS is committed to every capability being reachable identically from the Dashboard, REST
API, CLI, Discord, and (Phase 5) an AI layer, with exactly one implementation underneath all of
them, and to a new subsystem becoming available everywhere automatically just by existing. Prior to
this phase, `umbrella-core` had one working adapter (REST) with hand-written routes, each responsible
for its own permission check and its own audit-log write (see the pre-Phase-0 `api/routers/audit.py`
for a representative example). Adding CLI, Discord, and AI adapters on top of that pattern would have
meant re-implementing permission checks and audit writes per adapter, per capability — four places to
keep in sync per feature, growing linearly with both feature count and adapter count.

## Decision

Every capability is declared once, via `@capability(...)` in `registry/decorator.py`, producing a
`CapabilitySpec` (`registry/spec.py`) that carries its parameter schema, required permission,
destructive/reversible flags, and audit category. `CapabilityRegistry.call()` (`registry/registry.py`)
is the *only* code path that may invoke a capability's handler — it performs permission enforcement,
parameter validation, handler invocation, and audit-log writing, in that order, regardless of which
adapter initiated the call. Adapters (`registry/adapters/rest.py`, `registry/adapters/cli.py`)
translate their transport's request shape into a `CallContext` (`registry/context.py`) and a raw
params dict, then call `registry.call()` — they contain no business logic and no permission/audit
logic of their own.

`CallContext` is built from the same `require_admin_key_or_session` dependency REST already used
before this phase — Phase 0 does not change *who* is allowed to authenticate, only how an
authenticated call is subsequently routed to business logic.

## Consequences

**What this buys:**
- A new capability is automatically reachable over REST (`POST /api/v1/capabilities/{name}/invoke`)
  and the CLI (`umbrella <group> <group> <leaf>`) the moment it's declared — no separate route or CLI
  command to write.
- Permission enforcement and audit logging happen exactly once per call, in the registry, not once
  per adapter per capability. A missing audit write or a forgotten permission check on a new feature
  is now a class of bug that can't occur for anything built on the registry, rather than something to
  remember per feature.
- Audit rows are written on both success and failure outcomes automatically (see
  `registry/registry.py`'s `call()`), which is a strict improvement over the pre-Phase-0 pattern of
  each service hand-writing a single success-path audit call.
- `api/routers/audit.py` was refactored to delegate to the new `platform.audit.search` capability
  instead of duplicating its own query — proving the migration pattern later phases will repeat for
  the rest of the hand-written routers, without breaking any existing consumer (see the pre-existing
  `tests/test_audit.py`, which passes unmodified against the refactored router).

**Trade-offs accepted, explicitly:**
- The REST adapter is RPC-style (`POST /api/v1/capabilities/{name}/invoke`), not resource-styled
  (`POST /servers/{id}/restart`). This is the same trade-off recorded in the ecosystem architecture
  discussion: resource-styled aliases can be layered on top later as thin routes calling the same
  `registry.call()`, without changing the underlying contract. Building that sugar now, before a
  second adapter (Phase 5's AI Tool Registry) exists to validate the schema-driven approach against,
  would be speculative.
- The CLI currently authenticates only at the admin-key/superuser tier (see `registry/adapters/cli.py`).
  Per-user CLI identity requires a login/session capability that doesn't exist yet — it's a Phase 3
  (Identity/RBAC/SSO) dependency, not something to fake with a placeholder auth path now.
- `CallContext.db` is a single shared `AsyncSession` for the duration of one call — a capability's own
  side effects and its audit row commit or roll back together. This is the correct behavior for
  Phase 0's scope; if a future capability needs to span multiple independent transactions, that's a
  capability-level design question for that phase, not something the registry needs to solve
  speculatively now.

## Alternatives considered

- **Per-adapter hand-written glue** (status quo, extended to CLI/Discord/AI as each phase needed it):
  rejected — this is exactly the "four implementations to keep in sync" problem the ecosystem
  architecture discussion identified as the reason a registry pattern was needed at all.
- **A second, event-sourced/CQRS-style command bus for all business logic**: rejected for the same
  reason recorded in the master roadmap — event sourcing is valuable for the audit log specifically
  (already an append-only model, unaffected by this decision) but not for state that's overwhelmingly
  read as "current value," which is what most capabilities' underlying data actually is.
