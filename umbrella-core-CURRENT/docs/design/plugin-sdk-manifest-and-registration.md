# Plugin SDK — manifest schema + tool-registration contract

Status: proposed, implementing against this doc in the same session.
Scope: Phase 7 item 3 (`services/investigation/tools.py` +
`capabilities/investigation.py` read first, per the handoff). Sandboxing
(item 4) is a separate doc/module — this one only covers *what a plugin
declares* and *how that becomes a capability*, not *how the plugin's code
is executed safely*. The registration contract below is written so it does
not care which sandbox implementation sits behind it.

## Why this needs a real decision, not boilerplate

Core capabilities (`@capability` in `registry/decorator.py`) bind a
`CapabilitySpec.handler` to a real, already-imported, trusted Python
function at process-startup import time. A plugin's handler is untrusted
code inside a zip that hasn't executed yet when the manifest is read (at
install time, and again at every process startup when installed plugins
are re-registered). That one difference forces three departures from the
core pattern, all captured below:

1. **Params/result schemas can't be Python `BaseModel` subclasses** declared
   in the manifest — the manifest is static JSON/TOML data, not importable
   code, until the plugin's own module is loaded inside the sandbox. The
   manifest instead declares a small JSON-Schema-like shape (see
   "Param schema vocabulary") that we compile into a real Pydantic model
   *before* registering, using `pydantic.create_model`. This still gives
   `CapabilityRegistry.call()` a real `params_model` to validate against —
   nothing downstream (REST, CLI, AI) needs to know the model was
   generated rather than hand-written.
2. **`CapabilitySpec.handler` can't be the plugin's function directly** —
   it must be a thin wrapper, built at registration time, that calls into
   the sandbox executor with `(entrypoint, ctx-safe-params)` and adapts the
   result back into `result_model`. This is the one new piece of glue code;
   everything else about `CapabilityRegistry.call()` (permission check,
   audit row, validation) is reused completely unmodified — same "no
   shadow API" principle Phase 7's REST work is supposed to honor for the
   registry itself.
3. **Namespacing must be structural, not a naming convention staff members
   remember to follow**, because plugin authors are untrusted third
   parties, unlike every capability module written so far. `CapabilityRegistry.register()`
   already raises `CapabilityAlreadyRegisteredError` on name collision, so
   the fix is one rule enforced by the registration function itself:
   every plugin capability name is generated as
   `f"plugin.{plugin_id}.{local_name}"` and a plugin's manifest is
   rejected outright if `local_name` isn't a bare, dot-free identifier
   (i.e. a plugin cannot declare `name="plugin.other_plugin.foo"` or any
   name containing a `.` itself, which would otherwise let one plugin spoof
   another's namespace or collide with a core `platform.*` name).

## Manifest schema (v1)

File: `plugin.json` at the root of the plugin's zip. One manifest can
declare a capability, a Discord command, and a dashboard UI slot together
(Decision from `docs/adr/phase-7-notes-from-phase-5.md`, "multi-surface
plugins" — confirmed intended shape, built here for the first time).

```jsonc
{
  "schema_version": 1,
  "plugin_id": "queue-tools",              // slug: ^[a-z][a-z0-9_-]{2,63}$
  "name": "Queue Tools",
  "version": "1.0.0",                       // semver, enforced
  "author": "example-author",
  "description": "One-line summary shown in the marketplace listing.",
  "storage": "kv",                          // "kv" (default) | "sqlite" — Decision 2

  "capabilities": [
    {
      "local_name": "queue_status",         // becomes plugin.queue-tools.queue_status
      "summary": "Report current queue depth.",
      "entrypoint": "handlers:queue_status",// module:function inside the plugin zip
      "params": {
        "target_user_id": {"type": "string", "required": false}
      },
      "result": {
        "queue_depth": {"type": "integer"},
        "oldest_wait_seconds": {"type": "number"}
      },
      "required_permission": "queue.read",  // must be an existing core permission key;
                                             // plugins do not get to invent new ones (see below)
      "destructive": false,
      "reversible": true,
      "audited": true
    }
  ],

  "discord_commands": [
    {
      "name": "queue-status",
      "description": "Show current queue depth.",
      "capability": "queue_status"          // local_name, resolved against this manifest only
    }
  ],

  "dashboard_ui_slots": [
    {
      "slot": "sidebar.tools",              // one of a fixed, host-defined slot vocabulary
      "label": "Queue Tools",
      "capability": "queue_status"
    }
  ]
}
```

### Param/result schema vocabulary

Deliberately tiny — this is not a general JSON Schema implementation,
because every extra type is more surface area `pydantic.create_model` has
to translate correctly and more surface area for a malicious manifest to
try to smuggle something unexpected through. Supported `type` values:
`string`, `integer`, `number`, `boolean`. `required` defaults to `true`.
No nested objects, no arrays, no `$ref`, no free-form `additionalProperties`
— a plugin needing a richer shape passes a JSON-encoded string field and
parses it itself inside the sandbox. Revisit only if a real plugin author
hits this limit in practice (same "revisit if insufficient" posture the
zip-vs-container decision already used).

### `required_permission` must reference an existing core permission

A plugin manifest cannot mint new permission keys — `required_permission`
is validated at registration time against the same permission set core
capabilities already draw from (`services/permission_resolution.py`'s
known keys). This is what keeps "no more access than it was granted" true:
the *ceiling* a plugin can ask for is bounded by permissions that already
exist and that an admin already understands, not an arbitrary string the
plugin invents and that only the plugin's own code enforces the meaning
of. Installing a plugin whose manifest requests a permission is a distinct,
explicit admin approval step in the marketplace install flow (not built
in this session — flagged so it isn't silently assumed later).

## Tool-registration contract

Mirrors `capabilities/investigation.py`'s `_make_tool_capability` shape —
generate the `@capability`-equivalent registration once, per declared
capability, rather than per plugin:

```python
def register_plugin_capabilities(
    manifest: PluginManifest,
    sandbox: SandboxExecutor,  # see sandboxing doc; anything satisfying this Protocol works
    registry: CapabilityRegistry = default_registry,
) -> list[str]:
    """Registers every capability in `manifest.capabilities` into `registry`,
    returning the list of fully-qualified names registered. Called once at
    plugin install time and once per capability module at every process
    startup for already-installed plugins (mirrors capabilities/__init__.py's
    "import everything at startup" pattern, just data-driven instead of
    import-driven)."""
```

For each declared capability:
1. Validate `local_name` is dot-free; compute `full_name = f"plugin.{manifest.plugin_id}.{local_name}"`.
2. Compile `params` / `result` schema dicts into real `BaseModel` subclasses
   via `pydantic.create_model` (cached per plugin+capability so repeated
   calls don't rebuild the model every invocation).
3. Validate `required_permission` against the known core permission set;
   reject registration (not just the call) if it doesn't resolve — a bad
   permission reference is caught at install time, not silently allowed
   through to become a runtime 403 surprise for whoever installed it.
4. Build the handler wrapper:
   ```python
   async def _handler(ctx: CallContext, params: BaseModel) -> BaseModel:
       raw_result = await sandbox.run(
           plugin_id=manifest.plugin_id,
           entrypoint=cap.entrypoint,
           params=params.model_dump(),
           actor_id=ctx.actor_id,   # sandbox never receives ctx.db or ctx.permissions —
       )                            # see sandboxing doc for exactly what crosses the boundary
       return result_model.model_validate(raw_result)
   ```
5. Call `registry.register(CapabilitySpec(name=full_name, ...))` — same
   object, same registry, same `CapabilityRegistry.call()` path every other
   adapter already uses. This is the concrete mechanism behind "no shadow
   API": a plugin capability is indistinguishable to REST/CLI/Discord/AI
   from a core one once registered, except for the `plugin.` name prefix.

### What crosses the sandbox boundary, and what deliberately doesn't

The wrapper hands the sandbox `params` (already validated, plain dict) and
`actor_id` (a string) — never `ctx.db` (a live DB session) and never
`ctx.permissions` (the actor's full permission set). A plugin capability
that needs core data must go back through the Capability Registry itself
(the same REST-shaped call any external API consumer would make), which is
the concrete enforcement of Decision 2's "no cross-plugin or cross-core
joins, ever, by design" rule — the plugin's sandboxed process has no
direct handle to the core database at all, so there's no boundary to
accidentally get wrong later.

## Discord commands / dashboard UI slots

Both are declared as thin references (`capability: <local_name>`) rather
than duplicating a description — this is what "one manifest declares three
things" actually buys: the summary, params schema, and permission all live
in exactly one place (the capability declaration), and the Discord/
dashboard declarations only add surface-specific presentation (a
slash-command name, a sidebar slot). Building the actual Discord
cog-registration and dashboard-slot-rendering code that reads these is
follow-on work once the capability registration path is verified solid —
not done in this increment.

## Open item deliberately not resolved here

Result-schema validation failures (sandbox returns a value that doesn't
match `result.*`) are treated as capability call failures (same as any
other handler exception `CapabilityRegistry.call()` already handles and
audits) — no special-cased plugin error type. Flagging this explicitly
since it's a real behavioral choice, not an oversight: a plugin returning
a malformed result looks the same, to every adapter, as a plugin that
raised.
