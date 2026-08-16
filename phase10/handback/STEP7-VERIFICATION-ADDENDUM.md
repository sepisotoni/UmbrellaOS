# Head-chat verification addendum — step 7 (Tier 3)

Read alongside `handback/STEP7-TIER3-PLUGIN-PAGES.md` and
`STEP6-VERIFICATION-ADDENDUM.md` — this corrects/extends the former,
using the fixes already established in the latter.

## Important: this deliverable branched from the pre-fix step 6 zip

The step 7 session's own tree still had `next@16.0.1`, the missing
`eslint.config.js`, and the unfixed `command-palette.tsx` — all three
correctly re-flagged in `STEP7-TIER3-PLUGIN-PAGES.md` as pre-existing,
not introduced by this step, which is accurate. But those are already
fixed in the consolidated package from the step 6 addendum. Rather than
apply Tier 3's changes on top of the broken tree, I diffed step 7's
delivered tree against the *unfixed* step 6 tree to isolate exactly
which files Tier 3 actually touched, then applied only those onto the
already-fixed baseline. Confirmed by diffing: `command-palette.tsx` and
`package.json`'s `next`/`eslint` version lines were the *only* files that
differed beyond Tier 3's real changes, and in both cases the difference
was purely "my fix is present vs. absent" — not competing edits. No
Tier 3 logic was lost or overwritten by doing it this way.

## Backend — confirmed clean, nothing to fix

Applied all 6 modified files
(`manifest.py`/`marketplace_service.py`/`capabilities/marketplace.py` +
3 test files) onto the step 6 addendum's verified core. Confirmed each
file is a genuine superset — still contains step 1's `render_as` and
step 6's `dashboard_layout` additions, not a stale rollback. Fresh venv,
fresh install, real `pytest -q`: **819/819**, matching the handback
exactly. `pip check` and the scanner both clean.

Spot-checked two of the design claims directly rather than trusting the
manifest doc:
- `_ALLOWED_PAGE_RENDER_AS = _ALLOWED_RENDER_AS | {"table"}` — confirmed
  it's a real set union against Tier 1's vocabulary, not a hand-copied
  list that could drift out of sync.
- `_ALLOWED_NAV_ICONS` — confirmed it's the same 9-icon set
  `lib/nav-icons.ts` hardcodes on the frontend side.

## Frontend — merged onto the fixed baseline, then re-verified in full

New files (`table-widget.tsx`, `lib/marketplace-pages.ts`,
`lib/nav-icons.ts`) and genuinely modified files
(`app/(dashboard)/marketplace/[pluginId]/page.tsx`,
`components/nav/sidebar.tsx`, `components/widgets/plugin-widget.tsx`,
`lib/types.ts`) applied onto the step 6 addendum's already-fixed
`umbrella-dashboard` (Next.js 16.3.0, working `eslint.config.mjs`,
fixed `command-palette.tsx`). `package.json` was **not** overwritten —
confirmed step 7's version differs only in the two CVE-relevant pins,
no new dependency was added for table/icon rendering.

Spot-checked two of the trust-boundary claims directly:
- `lib/nav-icons.ts` — genuinely a fixed lookup object
  (`Record<string, LucideIcon>`), not a dynamic import by name. A
  manifest `nav_icon` string can only ever resolve to one of 9
  pre-bundled icons or fall back to a default, never reach arbitrary
  `lucide-react` exports.
- `table-widget.tsx` — columns genuinely derived from `Object.keys(row)`
  across all rows, first-seen order, never a plugin-supplied header
  list. Cell values go through plain JSX text interpolation
  (`cellText()` returns a string, rendered as `{cellText(row[col])}`),
  same as every other trusted renderer — holds Decision 1.

### Full verification loop re-run on the merged tree

```
npm audit          → found 0 vulnerabilities
npm run build       → ✓ Compiled successfully, all 12 routes
                       (including /marketplace/[pluginId] as a real
                       dynamic route, not the step-2 placeholder)
npx tsc --noEmit     → clean, exit 0
npm run lint        → clean, 0 errors
```

Same five-way-clean state the step 6 addendum established, now holding
across Tier 3's additions too.

## What's left, unchanged from step 7's own handback

- **Tier 2 config toggles** — still blocked on your Decision 2 sign-off.
  Nothing implemented.
- **Marketplace listing/install UI** (`app/marketplace/page.tsx` itself —
  browse/publish/install/uninstall from the dashboard) — never assigned
  to any step 0–7. Still the step-2 placeholder. This is the one real
  gap left if you want the full plugin lifecycle usable from the
  dashboard instead of CLI/API only — worth its own explicit ask.
- No manual/browser runtime check of any of this — everything verified
  here is static (audit, build, typecheck, lint, backend tests).
