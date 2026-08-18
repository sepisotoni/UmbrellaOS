# Phase 13, Step 3 of 3 — GrimAC Bridge

Read `CLAUDE.md` then `PROJECT-PRINCIPLES-AND-WORKING-RULES.md` first.
Read-only access — hand back a zip, don't push.

Steps 1 and 2 are done and on `main`. Read the merged source directly
before writing anything — don't restructure what's there.

## Required reading

`minecraft-plugin/MINECRAFT-PLUGIN-SCOPING-AND-HANDOFF.md` on the
`archive` branch — the GrimAC section has the real, source-verified API
details. Use it, don't re-derive from GrimAC docs. Don't touch or
reference any old `minecraft-plugin/` Java source you find — abandoned,
reflection-based, dead on arrival.

## Build exactly this

One new class: `GrimBridge.java`

- `provided`-scope Maven dep on GrimAC — **not reflection**. Wrong
  class/method name must fail the build, not silently no-op.
- Runtime guard: `Bukkit.getPluginManager().isPluginEnabled("GrimAC")`
- `plugin.yml`: `softdepend: [GrimAC]` (not `depend`)
- EventBus: `GrimAPI.INSTANCE.getEventBus().get(FlagEvent.class).onFlag(...)`
- Report to existing `POST /api/v1/anticheat/flag` via `CoreApiClient`
- VL conversion: `Math.round(check.getViolations())` — round, not truncate

No core-side changes. No `connection_mode` work.

## Testing

JUnit/Mockito for the VL conversion and `CoreApiClient` extension.
More importantly: actually trigger a real GrimAC flag on a real Paper
server and confirm it reaches core. State this explicitly in your
handback — don't just say the code compiles.

## Handback zip

1. Diff + changed-file manifest
2. Handback doc with:
   - "Step 3 complete" declaration at the top
   - What was built, any deviations
   - What was verified live vs unit-tested only
   - Anything needing a decision before Phase 13 is marked done
