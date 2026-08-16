# Capability Registry — developer guide

The Capability Registry is how a domain in `umbrella-core` exposes business logic to every adapter
(REST, CLI, and — from Phase 5 onward — Discord and the AI Tool Registry) at once, with one
implementation underneath all of them. See `docs/adr/0001-capability-registry.md` for why this exists.

## Declaring a capability

```python
from pydantic import BaseModel
from registry import capability, CallContext


class RestartServerParams(BaseModel):
    server_id: str

    def audit_target(self) -> str:
        """Optional: what this action affected, for the audit log's `target` column."""
        return self.server_id


class ServerState(BaseModel):
    server_id: str
    status: str


@capability(
    name="hosting.server.restart",          # dot-separated, globally unique
    summary="Restart a server.",             # shown in GET /capabilities, umbrella --help
    params_model=RestartServerParams,
    result_model=ServerState,                # optional
    required_permission="server.control",    # None = any authenticated actor
    destructive=True,                        # read by the Phase 5 AI orchestrator
    reversible=False,                        # a restart can't be "undone"
    audited=True,                            # default; set False only for pure introspection
)
async def restart_server(ctx: CallContext, params: RestartServerParams) -> ServerState:
    ...
```

Rules that make this safe to build on:

- **Never call a `@capability`-decorated function directly.** Always go through
  `registry.call(name, ctx, params)`. Calling the handler directly skips permission enforcement and
  audit logging — the two things the registry exists to make automatic.
- **Register the module.** Add `from . import your_module` to `capabilities/__init__.py` (mirrors
  `models/__init__.py`'s existing pattern) so your capability is registered before the app or CLI
  starts. A capability that's never imported never registers.
- **Capability names must have at least one dot** (`domain.subject.action`) — this is what lets the
  CLI adapter build `umbrella domain subject action` and is enforced at declaration time
  (`CapabilitySpec.__post_init__`), not left as a convention.
- **Don't duplicate permission-resolution logic.** If you need "what can this user do" outside a
  capability handler, import `resolve_user_permissions` from `services/permission_resolution.py` —
  the same function `CallContext` itself uses.

## Calling a capability from an adapter

Every adapter follows the same two-step shape: build a `CallContext`, then call the registry.

```python
ctx = await CallContext.from_web_auth(auth, db, source="rest")  # or source="cli"
result = await registry.call("hosting.server.restart", ctx, {"server_id": "abc"})
```

`from_web_auth` accepts the exact return type of the existing `require_admin_key_or_session`
dependency (a `User` or the raw admin-key string) — there is no separate authentication concept to
learn for capability calls.

## What you get for free

- **REST**: `POST /api/v1/capabilities/{name}/invoke`, `GET /api/v1/capabilities` (self-describing
  listing with each capability's JSON schema) — no route to write.
- **CLI**: `umbrella <name-as-nested-groups>` — no command to write. Run `python cli.py list` to see
  everything currently registered.
- **Audit log**: one row per call, success or failure, in the existing `audit_log` table — no
  `AuditLog(...)` construction to write by hand.
- **Permission enforcement**: one check, in `registry.call()`, before your handler ever runs.

## What Phase 0 deliberately does not include

- An AI Tool Registry adapter — arrives in Phase 5, once there's a model-routing/orchestration layer
  to hand these schemas to. Building a stub now would be exactly the kind of placeholder
  implementation the project's engineering rules rule out.
- A Discord adapter — arrives alongside the Phase 5/6 bot restructuring.
- Resource-styled REST path aliases (`/servers/{id}/restart` instead of
  `/capabilities/hosting.server.restart/invoke`) — can be layered on top later without changing this
  contract; see ADR-0001's trade-offs section.
- Per-user CLI authentication — the CLI currently runs at the admin-key/superuser tier only, pending
  Phase 3's identity/session work.
