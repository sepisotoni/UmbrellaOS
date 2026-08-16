# Phase 10, Decision 2 — Tier 2 config-write capability shape

**STATUS: DECIDED — Option A.** Sepiso Toni's call, made explicitly for
long-term customizability: per-plugin permission scoping matters more
the more the plugin marketplace grows, and Option A is consistent with
every other pattern already built (`dashboard_ui_slots`,
`discord_commands` both already resolve to `plugin.<id>.*`). The
comparison below is kept for the record, not as an open question.

## The question

When a plugin declares a Tier 2 config toggle (`config_fields` — new
manifest field, not yet added; see `DASHBOARD-PLUGIN-UI-SCOPING.md` Tier
2), flipping it in the dashboard's Settings page needs to write the new
value into that plugin's own `kv` storage. What capability does that
write?

## Option A — per-plugin auto-generated

Every installed plugin that declares `config_fields` automatically gets
its own capability registered at install time:
`plugin.<plugin_id>.config.set`, alongside whatever capabilities the
plugin author declared themselves in `capabilities[]`. Mirrors how
`discord_commands` and `dashboard_ui_slots` already resolve to
`plugin.<plugin_id>.<local_name>` today — this would be the same pattern,
just auto-generated rather than declared.

**Permission model:** a distinct `required_permission` per plugin's config
write, e.g. `plugin.<plugin_id>.config.write`. An admin grants config-write
access to *this specific plugin's* settings, not to every installed
plugin's settings at once.

**What it costs:**
- N installed plugins with `config_fields` = N new capabilities registered
  and N new permission rows, growing with marketplace adoption. The
  capability registry and RBAC role ladder both already support this shape
  (every other plugin capability works this way), so it's not new
  mechanism — just more of the existing one.
- Slightly more registration-time work: `MarketplaceService.install()`
  needs to synthesize this capability the same way it already resolves
  `discord_commands`/`dashboard_ui_slots` — real but small, same shape as
  existing code in `marketplace_service.py`.

**What it buys:**
- An audit-log entry for a config write says exactly which plugin's
  capability was invoked (`plugin.queue-tools.config.set`) — no need to
  inspect the params to know which plugin was touched.
- A permission grant is inherently scoped. Granting a moderator "can
  configure `queue-tools`" doesn't imply "can configure every other
  installed plugin too" — no separate scoping check needed at call time,
  the registry's existing per-capability permission check does it for
  free.
- Consistent with the precedent already set by `discord_commands` and
  `dashboard_ui_slots`, which the review discipline flagged is worth
  weighing (a genuine fourth resolved-to-`plugin.<id>.*` mechanism, not a
  new shape to reason about).

## Option B — one generic capability

A single capability, `marketplace.install.config.set`, parameterized by
`plugin_id`, `key`, `value`. One registration, works for every installed
plugin without any per-install registry mutation.

**Permission model:** one `required_permission`, something like
`marketplace.config.write`. Granting it means "can write config for any
installed plugin," full stop — there is no narrower grant available
within this shape without inventing a second permission layer inside the
capability's own logic (i.e., re-implementing per-plugin scoping by hand
inside the handler, rather than getting it from the registry's existing
mechanism).

**What it costs:**
- Broader blast radius per grant. A role with `marketplace.config.write`
  can reconfigure *any* plugin's settings, including ones installed after
  the grant was made — a real difference from Option A if Sepiso Toni ever
  wants "this moderator can configure the anticheat plugin but nothing
  else."
- An audit-log entry for `marketplace.install.config.set` needs its
  `plugin_id` param inspected to know which plugin was actually touched —
  slightly less legible at a glance than Option A's fully-qualified
  capability name, though still fully recoverable from the params.
- Validating `key` against the plugin's own declared `config_fields` (so
  an arbitrary string can't be written into `kv` storage under a made-up
  key) has to happen inside the handler at call time, since the registry
  itself has no way to know Option B's `key` param is plugin-specific.
  Option A gets a version of this narrowing for free at the permission
  layer; Option B still needs the same field-existence check either way,
  just without the permission-level narrowing on top.

**What it buys:**
- Zero registration-time work — no per-install capability synthesis
  needed in `MarketplaceService.install()`. New plugins with config
  fields work immediately with no registry mutation.
- One permission to reason about platform-wide, not N growing with
  marketplace adoption — simpler mental model for an operator who trusts
  every plugin they've chosen to install roughly equally (true today,
  single-operator deployment; may not stay true if third-party plugins
  from the marketplace become a real trust boundary later).

## What doesn't change either way

- Both options still need the same manifest addition
  (`config_fields: list[ConfigFieldDecl]`) and the same write target (the
  plugin's `kv` storage, Decision 2 from the original Part 1 scoping
  conversation — unrelated numbering collision, not the same decision).
- Both still need the propagation-timing behavior already locked
  (Decision 3): "next poll cycle" by default, instant-reaction only as an
  explicit per-toggle manifest opt-in via `EventBus.publish()`.
- Both are equally compatible with the schema-driven-rendering constraint
  (Decision 1) — this decision is about the write path's permission
  shape, not about what renders in the browser.

## Recommendation, offered but not decided here

Option A is more consistent with the precedent every other Phase 7/8/9
plugin-facing capability already set, and gives a real permission-scoping
benefit for a single sentence of extra registration code. Option B trades
that away for less registration-time mechanism, which matters more if
config-capable plugins turn out to be common enough that N growing
unboundedly becomes a real registry-size concern — not yet evidenced at
this project's current scale (per the same single-operator reasoning
Decision 3 in the roadmap doc already used for the search-latency
tradeoff). Recommendation: **A**, unless Sepiso Toni weighs the registry-growth
concern differently — but this is a real fork, not a formality, so
flagging the recommendation rather than just picking it.
