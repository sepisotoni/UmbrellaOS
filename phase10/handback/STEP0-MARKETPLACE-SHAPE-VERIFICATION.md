# Step 0 — Live marketplace response-shape verification

Per kickoff doc Decision 8: the scoping doc's assumptions about
`marketplace.install.list` / `marketplace.install.dashboard_slots`'s real
response shape were never independently checked. Verified live against the
patched `umbrella-core` (790/790 baseline, `render_as` already landed) using
the same in-memory-SQLite/ASGI harness `tests/conftest.py` uses — publish →
install a real plugin declaring a `dashboard.widgets` slot with
`render_as: "stat_pair"` → call both capabilities → record the raw JSON.
Script: `handback/step0_verify_script.py` (one-off, not part of the test
suite — reproducible, not committed into `umbrella-core/`).

## `marketplace.install.list` — live shape

```json
[
  {
    "plugin_id": "step0-verify-plugin",
    "installed_version": "1.0.0",
    "registered_capability_names": ["plugin.step0-verify-plugin.status"]
  }
]
```

The scoping doc never stated an explicit assumed shape for this one — no
mismatch to flag. One thing worth calling out for dashboard-side code,
since it wasn't spelled out anywhere: `registered_capability_names` entries
are the **fully-qualified** registry names (`plugin.<plugin_id>.<local_name>`),
not the bare `local_name` a plugin author writes in its manifest. Anything
in the dashboard that needs to invoke a plugin capability (Tier 1 widget
data fetch, Tier 3 page data fetch) must use the fully-qualified name — the
same one `dashboard_slots`'s `capability_name` field below already returns,
so in practice this falls out naturally, but worth stating since it's easy
to assume the bare local name works.

## `marketplace.install.dashboard_slots` — live shape

```json
[
  {
    "plugin_id": "step0-verify-plugin",
    "slot": "dashboard.widgets",
    "label": "Step0 Status",
    "capability_name": "plugin.step0-verify-plugin.status",
    "render_as": "stat_pair"
  }
]
```

### Mismatches vs. `DASHBOARD-PLUGIN-UI-SCOPING.md`

The scoping doc's "Confirmed gap" section describes this shape as carrying
only `slot`/`label`/`capability`. Two real mismatches against the live
response:

1. **`plugin_id` is present and the doc didn't mention it.** Not a
   regression — it's necessary. A dashboard rendering `dashboard.widgets`
   slots from multiple installed plugins needs `plugin_id` to key/scope
   widgets per plugin (e.g. as a React list key, or to group by plugin in a
   settings-style view). Dashboard scaffold work should assume it's there,
   not treat it as optional.
2. **Field name is `capability_name`, not `capability`.** The doc's prose
   used `capability`; the actual Pydantic field (and the manifest's own
   `dashboard_ui_slots[].capability` input field, confusingly, uses the
   *short* name on the way in — see `_manifest()` in the verify script) is
   `capability_name` on the way out. Any dashboard-side TS type generated
   from or hand-written against this response must use `capability_name`.

`render_as` itself matches Decision 7 exactly: present, typed as the
declared literal (`"stat_pair"` in this run), `null` when a plugin's slot
declaration omits it (not exercised in this run, but confirmed by the
existing 7 core-side tests from Step 1's `render_as` schema extension).

### Net effect on Tier 1 widget-rendering work (step 3, not started yet)

No blocking issues — the live shape is a strict superset of what the
scoping doc assumed, plus the one field-name correction above. Dashboard
TypeScript types for `DashboardSlot` should be:

```ts
type DashboardSlot = {
  plugin_id: string;
  slot: "sidebar.tools" | "sidebar.moderation" | "dashboard.widgets";
  label: string;
  capability_name: string;
  render_as: "stat_pair" | "status_badge" | "simple_list" | "table" | null;
};
```
