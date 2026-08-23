# Sub-chat handback — 3 backend bugfixes, Settings-toggle permission UX, phase-status verification

All three scoped tasks done. Nothing built beyond them.

## Independent verification, before touching any code (as instructed — not skipped)
- Backend: fresh venv, offline install from `wheels/` (clean), `pytest -q` → **838 passed**, `pip check` → clean, `pip-audit` → 6 CVEs, all against `pip` itself (the venv bootstrap tool, not a project dependency).
- Frontend: fresh `npm install` (0 vulnerabilities on install), `npx tsc --noEmit` → clean, `eslint` → clean, `next build` → succeeds, 13 routes.

Both matched what the package claimed, before any changes were made.

## Task A — 3 backend bugs, `umbrella-core-CURRENT/`

1. **`services/alt_detection_service.py` — dead `player_punishments` query, ~line 139.** Checked `Punishment`'s model (`models/player.py`) — it has no `ip_address` column, only `player_uuid`. That means the working `same_ip_player` loop right below the dead query is already the *only* correct way to answer "has anyone on this IP been punished" — there was no second, missing use for the dead fetch to fill. What it *was* fetching (the current player's own punishment history) is a different signal entirely — repeat-offender, not alt-detection — and folding it into this rule would have conflated the two rather than fixed anything. **Removed the dead query, with the reasoning left as a comment in place of it** rather than silently dropped. Behavior of `previously_punished_ip` is unchanged (the loop was already doing the real work) — confirmed via `tests/test_alt_detection.py`, all still pass, no assertions needed updating.
2. **`api/routers/auth.py` — unused `client_secret` in `discord_authorize`, ~line 250.** Compared against `discord_callback`'s use of the same pattern. Per OAuth2 spec, the authorization-request URL genuinely never needs `client_secret` — `discord_callback` is correctly the only place it's sent (in the code-for-token exchange). But the *fetch itself* wasn't pointless: a server missing `client_secret` would currently let a user go through the entire Discord redirect only to fail later at the callback exchange. **Added `client_secret` to the existing `if not client_id` check**, so a misconfigured server fails fast with a clear 503 instead of failing confusingly two steps later. No existing test asserted the old behavior (`tests/test_auth.py` has no `discord_authorize` coverage at all — worth a note, not in scope to add here).
3. **`services/alt_detection_service.py` — `datetime.utcnow()`, ~line 94.** Replaced with `datetime.now(timezone.utc)`, matching the convention already used everywhere else in the codebase (`services/ai/model_router.py`, `services/server_service.py`, etc. — grepped to confirm before picking, didn't invent a new style). Only this file's instance touched — `api/routers/verification.py` still has 3 `utcnow()` calls, confirmed still firing in the fresh pytest run's warnings, left alone as explicitly out of scope.

**Verification after Task A:** fresh full `pytest -q` rerun → **838 passed** (unchanged), `pip check` clean. The two `utcnow()` warnings from this file are gone from the output; `verification.py`'s three remain, as expected.

## Task B — Settings toggle read/write UX, `umbrella-dashboard-CURRENT/`

- `app/(dashboard)/settings/page.tsx` — computes `canWrite` per plugin via the existing `hasPermission(session.user, `plugin.${plugin.plugin_id}.config.write`)` helper (already used elsewhere in this app, per the task's own pointer), passed down as a prop.
- `components/widgets/plugin-config-toggle.tsx` — when `canWrite` is false: toggle renders disabled, inline "Read-only — you lack permission to change this," and the `fetch` never fires on click. When `canWrite` is true but the save fails at runtime: kept the existing optimistic-flip-and-revert, but the error message now distinguishes a 403 ("Permission denied — reverted") from a network/5xx failure ("Save failed — reverted"), by checking `res.status` rather than just `res.ok`.
- `app/api/plugin-config/route.ts` — catches `ApiError` specifically (from `lib/api.ts`, same pattern already used in `lib/marketplace-pages.ts`) and returns a real `403` when the underlying `plugin.<id>.config.set` capability call was rejected for permissions, instead of folding every failure into one generic `502`.
- `lib/plugin-config.ts` needed **no changes** — `setPluginConfigValue` already correctly throws rather than swallowing the error, which is exactly what the route needed to inspect.

**Note on the security boundary:** `canWrite` is explicitly a UX signal only, computed once at page load — it is not, and was never meant to be, the actual enforcement. The backend re-checks the real permission on every write regardless of what the client believes; if a permission is revoked mid-session, the toggle's stale `canWrite=true` just means the user sees the (still-real) 403-branch error message instead of the disabled state, not that anything unsafe happens.

**Verification after Task B, all four run fresh:** `npm audit` → 0 vulnerabilities, `npx tsc --noEmit` → clean, `eslint` → clean, `next build` → succeeds, **same 13 routes** as before the change.

## Task C — phase-status table verification
Written up as its own doc: `task_c_phase_status_verdict.md`. Short version: **the table held up completely** — every cell checked against this package's actual code, not trusted from either source doc. Confirmed v3's own roadmap status table is genuinely stale for Phases 9 and 10 (both say "not started," both are substantially built) — this is now independently confirmed by two separate chat sessions checking the same claim against the same code, which is worth actually fixing in `UMBRELLAOS_MASTER_ROADMAP_v3_CONSOLIDATED.md` itself rather than re-verifying a third time later.

## What's still open (not done here, not in scope for this dispatch)
- The two standing locked decisions noted at the top of the dispatch doc (Phase 0–6 re-derivation; v3-only numbering going forward) — untouched, as instructed.
- `tests/test_auth.py` has no coverage of `discord_authorize` at all — noticed while fixing bug 2, not added since it wasn't in scope.
- The Phase 10 gaps Task C reconfirmed (marketplace listing/install UI still a placeholder; no manual browser testing has happened anywhere in Phase 10) — unchanged, still open.
- `pip-audit`'s 6 CVEs against `pip` itself — not a project dependency, but worth someone deciding whether to bump the venv bootstrap tooling anyway.

## Leak-check
```
find . -iname ".env" -o -iname "*.db" -o -iname "*.sqlite*"
```
Run against the full output package below — returned nothing.
