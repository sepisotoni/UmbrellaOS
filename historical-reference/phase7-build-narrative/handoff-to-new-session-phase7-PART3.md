# UmbrellaOS — Phase 7 Handoff, Part 3: REST API Exposure + Marketplace

**Superseded — see `handoff-to-new-session-phase7-PART4.md`.** REST API exposure
and webhooks (this file's "what's left" items 1–2) are now done; use
`umbrella-core-PHASE7-REST-WEBHOOKS-COMPLETE.zip` referenced there instead of the
zip named below, which no longer exists in this package. Kept for its
still-accurate SDK/sandboxing detail and hand-verified security probing that
later files don't repeat.

Read in order: `handoff-to-new-session-phase7.md` → `-START.md` → `-PART2.md` →
this file → `-PART4.md`. Use `umbrella-core-PHASE7-SDK-SANDBOX-COMPLETE.zip`
source — the plugin SDK and sandboxing from PART2's items 3–4 are now **built**,
not just planned.

**Independently re-verified by a separate reviewing pass, not taken on the
building session's word:** merged/installed in a genuinely fresh venv, full
suite re-run — **648/648 passing**, matches the session's own report exactly.
Beyond just re-running tests, the sandbox was also adversarially probed by hand
(not just its own test suite) — two escape attempts tried:
1. A raw dunder-attribute-chain payload (`().__class__.__bases__...`) — caught
   by the static guard as expected.
2. The classic format-string two-stage gadget
   (`"{0.__class__.__bases__[0].__subclasses__}".format(x)`, intended to dodge
   AST-level attribute checks since the chain lives inside a string literal) —
   this one *did* pass the static guard as predicted (string contents aren't
   AST-inspected, and the module's own docstring says this is expected/why the
   runtime layer exists independently). At runtime it failed for a genuinely
   interesting reason: `str.format()` always returns a string representation,
   not a live object reference, so the "leaked" subclasses method can't
   actually be called afterward — `'str' object is not callable`. This isn't a
   gap in the sandbox; it's a property of `str.format()` itself (unlike
   template engines that evaluate expressions and can return live objects).
   Also confirmed a legitimate, non-adversarial plugin runs correctly and
   returns real computed values — the sandbox isn't just "safe because
   everything errors."

This is targeted probing, not a professional security audit — take it as
"held up under two real attempts," not as a clearance. The module's own
documented residual risk (a sufficiently skilled attacker targeting CPython
internals directly, not just Python-level introspection gadgets) still stands
exactly as written in `sandbox.py`'s docstring.

## What's done (Items 3–4 from PART2, now complete)

**Plugin SDK — tool-registration contract:**
- `docs/design/plugin-sdk-manifest-and-registration.md` — design doc written
  before code, per convention. Read this before touching the marketplace install
  flow — it explains the namespacing rule (`plugin.<plugin_id>.<local_name>`)
  and the tiny declared-type vocabulary decision.
- `services/plugins/manifest.py` — `PluginManifest` schema: plugin_id, semver,
  `storage: kv|sqlite` (Decision 2 from START.md), capabilities /
  discord_commands / dashboard_ui_slots, cross-reference validated.
- `services/plugins/registration.py` — registers plugin capabilities into the
  *same* `CapabilityRegistry` core capabilities use (no shadow registry).
  `required_permission` validated against the real `Permission` table at
  registration time — plugins cannot mint new permission keys.
- 36 tests, all passing.

**Sandboxing execution boundary:**
- `services/plugins/sandbox_guard.py` — static AST pre-check (defense-in-depth
  layer, explicitly documented as insufficient alone).
- `services/plugins/sandbox.py` — `ProcessSandbox`: real OS-process isolation
  via `multiprocessing` (fork), resource limits applied before plugin code
  runs (CPU/memory/fd/fsize/nproc), restricted builtins (confirmed by hand:
  only `Exception, False, IndexError, KeyError, None, StopIteration, True,
  TypeError, ValueError, abs, all, any, bool, dict, enumerate, filter, float,
  int, isinstance, len, list, map, max, min, range, repr, reversed, round,
  set, sorted, str, sum, tuple, zip` — no `open`/`eval`/`exec`/`import`/
  `getattr`/`vars`/`globals`), wall-clock timeout independent of CPU limit,
  `SqliteSandboxConnection` enforcing the per-plugin disk quota via SQLite's
  own `PRAGMA max_page_count`.
- One real bug found and fixed during the building session (documented in the
  session handoff, not hidden): an `EOFError` from a killed child's closed
  pipe was uncaught — now treated as an expected outcome reporting the
  killing signal.
- One known, deliberately-not-fixed caveat, stated plainly in `sandbox.py`'s
  own comments: `fork()` from an already multi-threaded process (any live
  asyncio app with a thread-pool executor) can deadlock. `forkserver` is the
  named fix, tracked as follow-up needing its own focused testing pass — **do
  not silently attempt this migration as a side effect of unrelated work**,
  it needs deliberate attention because forkserver has different
  requirements around what module state is picklable in the child.
- 30 tests, all passing, including real (not simulated) `SIGXCPU`/timeout/
  `RLIMIT_AS`-driven `MemoryError` kills.

**Not yet consumed:** `discord_commands` / `dashboard_ui_slots` are declared
in the manifest and validated at registration time, but nothing renders them
yet — no Discord cog reads a registered plugin's commands, no dashboard slot
system exists. This is explicitly deferred, flagged in the design doc, not an
oversight. Whoever builds the marketplace install flow will likely need this
working end-to-end for a plugin to be genuinely usable post-install — worth
deciding whether that's in-scope for marketplace work or its own follow-up
before starting.

## What's left in Phase 7

1. **REST API exposure of the Capability Registry.** Not started. Read
   `registry/registry.py` and `registry/adapters/rest.py` first — every prior
   handoff in this chain has said the same thing: "no shadow API," this
   should mean exposing the existing registry with proper external scoping
   (auth, rate limits, versioning), not building a second surface. Decide
   concretely: what does "public" mean here — a separate API key/OAuth scope
   model from the internal dashboard session auth? Versioning scheme (URL
   path `/v1/`, header-based, something else)? These are real decisions, flag
   them before building.
2. **Webhook registration + delivery**, from PART2 item 1 — still not started.
   CRUD for subscriber URLs per event topic, plus a real delivery-worker
   subscriber (HTTP POST with retry/backoff) reusing the dispatcher's
   existing `attempts`/backoff shape. This is a natural pairing with item 1
   above since both are "external consumers of internal state," but they're
   separable — webhooks don't strictly require the public REST API to exist
   first.
3. **Marketplace** (listing, versioning, install flow). Now unblocked — SDK
   and sandboxing are both solid. Install-time logic needs to: read a
   manifest's `storage` field and provision KV namespace or SQLite file
   accordingly (Decision 2, still not consumed by any real install flow);
   decide how `discord_commands`/`dashboard_ui_slots` actually get wired up
   post-install (see "not yet consumed" above — this may be a prerequisite,
   not a nice-to-have); and decide where plugin zip files/source actually
   live on disk in production (the sandbox takes `sources` as a constructor
   dict today, by design, with no filesystem-layout opinion of its own —
   something needs to own that now).
4. **`forkserver` migration** for `ProcessSandbox` — tracked, not urgent,
   needs its own focused session per the caveat above. Don't let it block 1–3.

## Working conventions (unchanged, still binding)

Test after every change, stop at the first new failure, don't batch. Verify
claims against real code, including every previous session's self-reported
summary — including this one's. Flag real design decisions before building
past them (item 1's auth/versioning model and item 3's plugin-storage-location
question are the two most likely to need this next).
