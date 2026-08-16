# Head-chat verification addendum — steps 0–6

This doc records what the head chat (the one you're courier-ing between)
independently checked and fixed on top of the step 0–6 build sessions'
own handback docs. Read alongside `handback/STEP0` through `STEP6` —
this doesn't replace them, it corrects/extends them.

## Backend — confirmed clean, nothing to fix

- Step 0's live-shape verification script re-run against my own
  independently-verified `umbrella-core` (790/790 baseline): output
  matched the handback doc byte-for-byte, including the `plugin_id`
  presence and `capability`→`capability_name` field-name flag.
- Step 6's backend additions (`dashboard.layout.get/set/reset`) applied to
  the same verified baseline, fresh venv, fresh install, real `pytest`
  run: **798/798**, matching the handback exactly. Spot-checked the
  admin-key-rejection and self-scoped-user claims directly against
  `capabilities/identity.py`'s real `_current_staff_user` — genuinely
  identical pattern, not just a docstring claim. Migration 026's columns
  cross-checked against the model 1:1. `pip check` and the dependency
  scanner both clean.

## Frontend — real, serious issues found and fixed

Every step 2–5 handback flagged "no npm registry access, build/lint
unverified" as an open risk. Step 6's session got registry access and
ran a real build for the first time — and caught two real bugs (see its
own handback). Running `npm audit`, which no session had done yet,
turned up a third, more serious problem this doc fixes:

### 1. Critical: `next@16.0.1` has a disclosed critical RCE

`npm install` itself warns on this version (GHSA-9qr9-h5gf-34mp, plus
~30 other advisories — XSS, cache poisoning, SSRF, DoS). This was the
pin in every step's `package.json` from step 2 onward, never audited
until now. **Fixed: bumped to `16.3.0`** (the version already proven
compatible by step 6's own tailwindcss investigation). `npm audit`:
5 vulnerabilities (1 critical, 2 high, 2 low) → 0, after this and the
next two fixes.

### 2. Low: ReDoS in `eslint`'s `@eslint/plugin-kit` dependency

`eslint@9.18.0` pulled in a vulnerable `@eslint/plugin-kit`. Confirmed
`eslint-config-next` has no upper bound on `eslint` before bumping.
**Fixed: `eslint` → `9.39.5`, `eslint-config-next` → `16.3.0`** (tracking
`next`'s version, its own convention).

### 3. Missing `eslint.config.js` entirely — every step's lint was silently never runnable

Confirmed no `.eslintrc*` or `eslint.config.*` existed anywhere in the
tree, despite `lint` being a wired `package.json` script since step 2.
**Fixed: added `eslint.config.mjs`.** First attempt used the legacy
`FlatCompat` shim (the commonly-documented approach) — that produced a
real circular-JSON crash against this `eslint`/`eslint-plugin-react`
combination. Checked `eslint-config-next@16.3.0`'s own package exports
first this time: it ships a native flat config directly
(`eslint-config-next`'s default export is already flat-config shaped,
confirmed by reading `node_modules/eslint-config-next/dist/index.js`,
not assumed) — so the fix is a two-line file spreading that export
directly, no compat shim needed.

### 4. Real bugs `eslint` caught once it could actually run: `command-palette.tsx`

Three genuine `react-hooks/set-state-in-effect` violations — synchronous
`setState` calls in an effect's non-callback body, which the rule exists
to catch because they cause a real extra cascading render each time:

1. The close-triggered state reset (`setQuery("")`/`setResults([])`/
   `setActiveIndex(0)` when `open` becomes `false`) — moved out of a
   `useEffect` entirely, into React's documented "adjusting state when a
   prop changes" render-time pattern (a `wasOpen` ref-like state variable
   compares against the current `open` value during render).
2. The too-short-query early return's `setResults([])`/`setLoading(false)`
   — removed; the empty/not-loading state is now derived at render time
   (`visibleResults`, `isSearching`) from `query` directly, rather than
   stored and reset.
3. `setLoading(true)` at the top of the debounced-fetch effect — moved
   inside the `setTimeout` callback, right before the actual `fetch`
   starts. This is also a small real UX improvement, not just a lint fix:
   no loading-indicator flash for a query that gets replaced before the
   debounce window elapses.

All three fixes verified by actually re-running `npx next build` and
`npm run lint` after each change, not just inspecting the diff.

## Final verified state (this session, fresh install every time)

```
npm audit          → found 0 vulnerabilities
npm run build       → ✓ Compiled successfully, all 12 routes, TypeScript clean
npx tsc --noEmit     → clean, exit 0
npm run lint        → clean, 0 errors
```

This is the first point in Phase 10's history where the frontend has
been build-clean, lint-clean, and vulnerability-clean simultaneously,
confirmed independently rather than self-reported by the session that
wrote the code.

## Not yet done (unchanged from step 6's own handback)

- Step 7 (Tier 2 config toggles) still blocked on your Decision 2
  sign-off — nothing implemented, per your explicit instruction.
- Tier 3 plugin-owned pages (`app/marketplace/[pluginId]`) don't depend
  on Decision 2 and could start independently — not built yet.
- No manual/browser runtime check of any of this — everything verified
  here is static (audit, build, lint, tests), not "does it actually
  behave correctly when a person clicks around it."
- The `middleware.ts` → `proxy` naming convention deprecation warning
  from `next build` is real but non-blocking — Next.js 16.3 still
  supports the old convention, just recommends migrating. Left as-is;
  worth a follow-up, not urgent.
