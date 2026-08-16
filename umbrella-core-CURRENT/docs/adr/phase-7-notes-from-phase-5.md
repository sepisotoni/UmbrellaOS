# Phase 7 — Notes carried forward from Phase 5 conversation

Captured during Phase 5 work, for when Phase 7 (Developer Platform: Public API, Plugin SDK, Marketplace)
actually starts. Not decisions — open questions and one concrete safety flag.

## Plugin package format
**Decided:** zip format (manifest + files), not a container image. Rationale discussed: container images give
kernel-level isolation (strongest sandboxing, since it's enforced by the OS, not by the plugin's own code
behaving), but are heavier to author and further from "just upload a file." Zip was chosen for authoring
simplicity; means sandboxing has to be enforced by the runtime (resource limits, restricted builtins, no
default filesystem/network) rather than by physical isolation. Revisit if a real plugin author reports the
runtime-enforced sandbox isn't strong enough in practice.

## Multi-surface plugins
Confirmed as the intended shape: one plugin package/manifest declaring a capability should be able to also
declare a Discord command and a dashboard UI slot for that same capability — not three separate artifacts to
build per plugin. Matches the roadmap's existing Phase 7 wording ("hosting hooks, dashboard UI slots, AI tool
registration").

## Open gap: plugins bringing their own data/schema
Not solved anywhere in the current design. Every table today lives in umbrella-core's single Alembic migration
chain; there's no mechanism yet for a third-party add-on to bring its own persistent data (e.g., a non-Minecraft
pivot needing custom stats/leaderboard tables) without editing core migrations directly - which defeats the
"add-ons without touching core code" goal. Three options surfaced, not evaluated in depth, no decision made:

1. Generic key-value/document store, scoped per plugin. Simplest, most sandboxed, worst for anything needing
   real relational queries (sorting a leaderboard, joins against core data).
2. Plugins get their own schema/tables via their own scoped migrations at install time. More powerful, more
   surface area to get sandboxing wrong (a plugin's migration touching something it shouldn't).
3. Plugins get an entirely separate SQLite file, fully isolated from core's DB. Strongest isolation, but no
   easy joins against core data (e.g., "which Discord user has this race time" needs core's User table).

Needs an actual decision when Phase 7 starts, not before - flagged now only so it isn't assumed-solved by
then.

## Safety flag: CodeExecutionService's sandboxing claim doesn't match its implementation
`bot/services/code_execution_service.py` (Moo-assistant) is being ported into Phase 5 as-is, since it's your
own trusted first-party tool (gated to owner/founder role, same as it always was). But its docstring claims
more than the code does: it says "runs in a subprocess with a 30-second timeout" and "no filesystem writes
outside /tmp" - the actual implementation is a raw `exec()` **in-process**, with full unrestricted
`__builtins__` (meaning `open()`, `import os`, `import subprocess` are all available to whatever code runs).
The only real protection is a timeout and the owner-only permission gate.

This is a defensible risk for a single trusted owner triggering their own bot's code execution. **It must not
become the template for Phase 7's third-party plugin sandboxing** - that needs real process/container
isolation, a restricted builtins allowlist, and enforced filesystem/network limits, none of which this
pattern has despite its docstring's claims. Flagging now so a future session doesn't see "there's already a
sandboxed code execution pattern in the codebase" and reuse it uncritically for plugins.
