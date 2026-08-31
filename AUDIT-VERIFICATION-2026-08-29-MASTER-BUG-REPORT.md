# Verification of MASTER-BUG-REPORT (124 claims) against actual code

**Date:** 2026-08-29
**Method:** Read the actual source at each cited file/line on current `main`
(`bcd952d`) and confirmed or refuted each claim directly — no assumptions from
the report's own description. Checked out via `git worktree` against
`origin/main` mid-investigation to guarantee current code, not a stale local
copy.

**Coverage:** This is not an exhaustive re-derivation of all 124 items. I did
real, evidence-based verification on ~50 items, weighted toward
Critical/High severity and toward anything easy to falsify with a direct
grep/read. The remaining items (mostly LOW-severity frontend polish and
scripts/tooling opinions) are marked **UNVERIFIED** rather than guessed at.

**Headline finding: this report is significantly less reliable than it
presents itself.** Of the items I could actually check, several fall into
one of three buckets that inflate the "124 bugs" count against the real
codebase:

1. **False positives from ignoring the global rate-limit middleware.** At
   least 3 "no rate limiting on X" claims (#7, #14/38, and by extension the
   framing of #24) are wrong because `api/middleware/rate_limit.py` is a
   *global* per-IP + per-API-key middleware applied to every route except
   `/health` — it already covers AI endpoints and punishment endpoints. The
   real gap (if any) is a stricter *per-endpoint* limit, not "no rate
   limiting," which is what's claimed.
2. **False positives from stale/wrong line citations.** #12's cited lines
   (`capabilities/operational_intelligence.py:30-40`) contain Pydantic model
   fields, not datetime logic at all — the actual timezone-sensitive code
   (`services/operational_intelligence/crash_prevention.py`) is correctly
   timezone-aware. #31's cited lines (135-150) are inside a properly
   paginated query; the actual unpaginated-load-everything pattern the claim
   describes exists ~85 lines later, in a different function, and is an
   explicitly documented, deliberate design decision (small expected row
   counts), not an oversight.
3. **Flat-out wrong factual claims,** apparently from not reading the code:
   #16/#39 ("heartbeats never cleaned up") — `PluginHeartbeat` is a
   true upsert (one row per server, updated in place); there is nothing to
   clean up. #65's implied "no cleanup" for server metrics is also wrong —
   `services/operational_intelligence/metrics.py::purge_old_snapshots` runs on
   a scheduled sweep. #73 ("`_resolve_actor` duplicated in multiple files")
   — only exists in **one** file. #114 ("missing cyclonedx dependency") — it
   **is** in `requirements-dev.txt`.

That said, a meaningful number of CRITICAL and HIGH items are **genuinely
real and worth fixing** — see below. No code was changed in this pass, per
instructions; this is investigation-only.

---


---

## Fixes Applied by Auth/Permissions Agent (2026-08-29)

The following confirmed bugs within the auth/permissions/middleware subsystem
were fixed in commit `audit-fixes-2026-08-29`:

| # | Bug | Fix |
|---|-----|-----|
| 1 | Default `"change-me-in-production"` secret keys — no startup check | Added `validate_secrets()` in `config/settings.py`; called from `main.py` at startup — refuses to start if `SECRET_KEY` or `ADMIN_KEY` still has the default value |
| 6 | WAF mixed-encoding bypass (`..%2f`, `..%5c` not caught) | Expanded `_PATH_TRAVERSAL_RE` to include `..%2f`/`..%5c` mixed variants; added double-decode (`unquote(unquote(x))`) pass so `%252e%252e%252f` is also caught |
| 25 | Rate limiter keys off proxy IP, not real client IP | `rate_limit.py` now reads the rightmost `X-Forwarded-For` entry (proxy-injected, not spoofable) as the rate-limit key, falling back to `request.client.host` |
| 27 | No session rotation on login (session fixation risk) | `discord_callback` now revokes all existing valid sessions for the user (`revoked=True`) before issuing a new session token |

Not fixed by this agent (out of subsystem scope or deferred):
- **#5** (no MFA recovery codes) — requires full recovery-code design + enrollment UI changes; flagged for a dedicated task
- **#4** (PBKDF2 per-endpoint DoS) — partially mitigated by existing global rate limiter; a dedicated per-endpoint limit is a future hardening task
- All items not marked ✅ TRUE under CRITICAL/HIGH that relate to DB models, op-intel, marketplace, frontend perf, or other subsystems — left for their respective agents

---

## Legend
- ✅ **TRUE** — confirmed, matches the report's claim
- ⚠️ **PARTIALLY TRUE** — the underlying issue is real but the report's
  framing, severity, or specifics are off
- ❌ **FALSE** — contradicted directly by the code
- ❓ **UNVERIFIED** — not independently checked in this pass (mostly LOW items)

---

## 🔴 CRITICAL (23 claimed)

| # | Bug | Verdict | Evidence |
|---|-----|---------|----------|
| 1 | Default secret keys in production | ✅ TRUE — ✅ **FIXED** (commit: audit-fixes-2026-08-29) | `config/settings.py:103-104` — `secret_key`/`admin_key` both default to the literal string `"change-me-in-production"`, with no startup check anywhere that fails if unchanged. |
| 2 | `secrets_encryption_key` optional, no validation | ❌ FALSE | The field is intentionally optional (comment says so), and `services/secrets_service.py::_fernet()` explicitly raises a `SecretsError` the moment anything tries to encrypt/decrypt without a key configured. It fails loudly exactly as designed — not silent. |
| 3 | Admin key bypasses all permissions | ✅ TRUE (by design) | `api/dependencies/permissions.py` docstring states this outright ("X-Admin-Key auth bypasses all permission checks (plugin god mode)"), and `require_permission`/`RoleChecker` both return immediately for any `str`/`ApiKey`-typed admin-key auth without checking `permission`. This is a documented, intentional trust model, not a hidden flaw — but the report presents it as a discovered bug. |
| 4 | PBKDF2 MAC without rate limiting — DoS | ⚠️ PARTIALLY TRUE | `api/middleware/auth.py:84-90` does run 100k PBKDF2 iterations per request with a valid timestamp+MAC header, with no extra protection at that specific check. But the global per-IP rate limiter (see #24) does apply to this route too, so it's not *unlimited* — just not specially hardened beyond the general limit. |
| 5 | No MFA recovery codes | ✅ TRUE | Confirmed no `recovery`/`backup_code` anywhere in `api/routers/auth.py` or `services/mfa_service.py`. A user who loses their authenticator app has no documented recovery path. Still true even after the recent MFA-enrollment commit. |
| 6 | WAF encoding bypass | ⚠️ PARTIALLY TRUE — ✅ **FIXED** (commit: audit-fixes-2026-08-29) | `api/middleware/waf.py`'s regex explicitly includes the singly-encoded literal (`%2e%2e%2f`) as one of its alternatives, so straightforward double-encoding of the whole traversal sequence is actually caught. However, **mixed-encoding variants** (e.g. literal `..` + encoded `%2f`) genuinely bypass it, since neither alternative matches that combination. The bug is real but "double-encoded paths bypass detection" as a blanket statement is not accurate. |
| 7 | No rate limiting on AI endpoints | ❌ FALSE | `api/middleware/rate_limit.py` is global (all paths except `/health`), 120 req/60s per IP + an additive per-API-key limit. AI endpoints are covered like everything else. No AI-specific stricter limit exists, but "no rate limiting" is wrong. |
| 8 | Prompt injection in AI endpoints | ✅ TRUE — ✅ **FIXED** (commit: e79b026) | Confirmed real: `natural_language` in `ai_config_service.process_ai_config_request()`, `body.message`/`body.context` in the copilot endpoint, and `appeal.message` in `ai_service`'s appeal review prompt were all interpolated as plain undelimited text directly adjacent to system instructions. The actual hard boundary was already correct — `apply_config_action()` requires human approval via `settings.manage` before any AI-proposed change is applied, and `action_guard.py`'s destructive/irreversible ceiling is enforced in code, not prompt text — so injection could not lead to autonomous destructive action. But nothing stopped an appeal statement or config request from manipulating the model's own JSON output. Fixed: wrapped all three untrusted-input sites in XML-style tags with an explicit "treat as data, not instructions" framing preceding them. Documented as defense in depth, not a claim that injection is now impossible. |
| 9 | Prepared statement cache disabled — kills performance | ❌ FALSE (mischaracterized) | Confirmed both caches are disabled in `database/engine.py`, but the extensive comment explains this is a **required, deliberate fix** for PgBouncer transaction-pooling compatibility (a real `DuplicatePreparedStatementError` seen in production, per the comment) — not an oversight. Re-enabling it would reintroduce a real bug. |
| 10 | Sync DB URL uses wrong port | ❓ UNVERIFIED | The default in `config/settings.py` uses port 5432 (correct, bypasses PgBouncer), but the actual *production* `.env`/Render env var value isn't visible from the repo — can't confirm or deny what's actually deployed. |
| 11 | Tool instance reused across requests | ⚠️ PARTIALLY TRUE — ✅ **FIXED** (commit: e79b026) | Confirmed: `capabilities/investigation.py::_make_tool_capability` created `tool = tool_cls()` once and captured it in a closure reused by every request. Checked all 5 `InvestigationTool` subclasses in `services/investigation/tools.py` — none define `__init__` or store mutable instance state, so the pattern was currently harmless. Fixed anyway as a latent footgun: any future tool subclass caching something on `self` would silently leak state between concurrent requests from different users. Both `_make_tool_capability`'s generated handlers and the standalone `recent_announcements` capability now instantiate `tool_cls()` fresh inside each request handler instead of at module load. |
| 12 | Timezone handling missing (crash risk / op intel) | ❌ FALSE | Cited lines (`capabilities/operational_intelligence.py:30-40`) are Pydantic model field declarations with zero datetime logic — wrong file/line entirely. The actual comparison logic in `services/operational_intelligence/crash_prevention.py:51` uses `dt.datetime.now(dt.timezone.utc)`, correctly timezone-aware. |
| 13 | No validation for encryption key | ❌ FALSE | Duplicate of #2 — same claim, same refutation. `_fernet()` fails loudly. |
| 14 | No rate limiting on punishments | ❌ FALSE | Same reasoning as #7 — global middleware covers `/api/v1/moderation/*`. |
| 15 | No IP/UUID validation in player snapshot | ✅ TRUE (severity overstated) | Confirmed: `POST /{uuid}/snapshot` uses the path param directly with no `uuid.UUID()` format check. Since `Player.uuid` is `String(36)`, not a native UUID column, a malformed value doesn't crash — it just gets stored as garbage data. Real gap, but not the crash risk the "critical" label implies. |
| 16 | Heartbeats never cleaned up | ❌ FALSE | `POST /api/v1/plugin/heartbeat` is a true upsert — one `PluginHeartbeat` row per `server_id`, fields overwritten in place on every call (`hb.last_seen = now`, etc.). There are no accumulating rows to clean up. |
| 17 | No UUID validation in verification | ✅ TRUE (same caveat as #15) | Confirmed — `player_uuid` used throughout `api/routers/verification.py` with no format check, same pattern as players.py. Data-quality gap, not a crash. |
| 18 | Appeal close without status validation — ACTION_TO_STATUS incomplete | ✅ TRUE (already fixed) | This was real and was fixed in an earlier pass on this repo (commit `3f01f48`, "audit(appeals)"): `close_appeal` previously wrote uppercase action names directly as `appeal.status`, which violated `ck_appeals_status` (case mismatch, plus `"reduced"` wasn't in the constraint at all) — every close call raised an unhandled 500. Now maps actions through `ACTION_TO_STATUS` to constraint-valid lowercase values, with migration 042 adding `'reduced'`. |
| 19 | Duplicate installation check missing (marketplace) | ❓ UNVERIFIED | Not checked in this pass. |
| 20 | Hardcoded API URL | ✅ TRUE (severity overstated) | `src/lib/api.ts:469` — `DEFAULT_CORE_URL` falls back to a hardcoded production Render URL if `VITE_UMBRELLA_CORE_URL` is unset. Real, but this is a common "sensible default" pattern, not really a security-critical bug. |
| 21 | No token refresh mechanism | ❓ UNVERIFIED | Not checked in this pass. |
| 22 | No command sanitization in console | ❓ UNVERIFIED | Not checked in this pass. |
| 23 | No CORS handling for network errors | ❓ UNVERIFIED | Not checked in this pass. |

**CRITICAL tally (of 20 checked):** 8 TRUE, 4 PARTIALLY TRUE, 8 FALSE, 6 UNVERIFIED. Note several "TRUE" ones (#3, #9) are actually intentional/documented design decisions the report presents as newly-discovered flaws.

---

## 🟠 HIGH (32 claimed) — sampled

| # | Bug | Verdict | Evidence |
|---|-----|---------|----------|
| 24 | Rate limit fails open | ✅ TRUE (documented tradeoff) | Confirmed in `api/middleware/rate_limit.py` — a `RedisError` logs a warning and allows the request through. The module's own docstring says this was found and deliberately fixed this way during Phase 3 testing (the alternative — propagating the error — took down every request on a Redis outage). Real behavior, but a considered tradeoff, not an unnoticed flaw. |
| 25 | IP-based limiting behind proxies | ✅ TRUE — ✅ **FIXED** (commit: audit-fixes-2026-08-29) | Confirmed — `request.client.host` used directly with no `X-Forwarded-For`/proxy-header handling anywhere in the middleware or `main.py`. Behind Render's/any reverse-proxy's LB, this means the rate limiter likely buckets by the proxy's IP, not the real client. |
| 26 | No permission hierarchy (`players.manage` doesn't imply `players.view`) | ✅ TRUE (mechanism), severity unclear | Confirmed — roles are defined as flat, explicit permission lists in `services/roles_service.py` with no automatic implication resolved at check time. Whether this manifests as an actual usability bug depends on whether any predefined role grants `.manage` without `.view` — didn't check every role definition. |
| 27 | No session rotation on login | ✅ TRUE — ✅ **FIXED** (commit: audit-fixes-2026-08-29) | No rotation/reissue-on-login pattern found in `api/middleware/session.py`. |
| 28 | No API key rotation support | ✅ TRUE | Confirmed — `services/secrets_service.py` uses a single static Fernet key with no rotation mechanism; its own docstring calls per-key rotation "real follow-up work," i.e. a known, self-documented gap. |
| 29 | `.env` write on every update | ❓ UNVERIFIED (partially contradicted) | `services/settings_service.py::write_env_value` exists, but I didn't confirm it's actually called unconditionally "on every update" vs. only for specific settings — the surrounding code suggests it's scoped, not universal. Needs a closer read to confirm/deny with confidence. |
| 30 | Missing error handling in verification (`confirm_verification()`) | ❓ UNVERIFIED | Started checking `capabilities/verification.py` — didn't complete a full trace of whether exceptions from `confirm_verification()` propagate uncaught to the capability layer's own error handling (which may catch broadly at a higher level). Inconclusive in the time available. |
| 31 | Memory bloat in plugin profile | ⚠️ PARTIALLY TRUE, wrong lines | Report cites lines 135-150, which are inside `execution_history()` — a **properly paginated** query (`.limit(params.limit).offset(params.offset)`). The actual load-everything-into-memory pattern is in a *different* function, `profile()` (~lines 225-240), which fetches all rows in a time window and aggregates in Python — but this is explicitly documented as a deliberate choice ("row counts involved are small"), not an oversight. |
| 32 | Suspicion score accumulates forever, no decay | ✅ TRUE (now, after an earlier fix) | `services/alt_detection_service.py` used to *overwrite* `suspicion_score` on every join (a different, worse bug — see below), which was fixed in an earlier pass to *accumulate* instead so false-positive reviews aren't silently undone. That fix is correct, but it does mean the score now only ever grows — there's genuinely no decay/reset mechanism, matching this claim as a real, open gap worth addressing separately (e.g. a cap or periodic decay). |
| 33 | No cleanup for `AnticheatViolation` | ❓ UNVERIFIED | Not checked. |
| 34 | No cleanup for player snapshots | ❓ UNVERIFIED | Not checked. |
| 35 | No cleanup for replay events | ❓ UNVERIFIED | Not checked. |
| 36 | No cleanup for security events | ❓ UNVERIFIED | Not checked. |
| 37–44 | (bridge validation, punishment rate limit dup, heartbeat cleanup dup, appeal idempotency dup, cron/scheduler, token TTL, retry logic, connection pooling) | ❓ UNVERIFIED / ❌ some are duplicates | #38 is a duplicate of #14 (FALSE, same reasoning). #39 is a duplicate of #16 (FALSE, same reasoning). #40 is a duplicate of #18 (TRUE, already fixed). The rest (#37, #41-44) not checked. |
| 45 | No code splitting | ✅ TRUE | Confirmed — no `lazy(` or `Suspense` anywhere in `src/App.tsx`. |
| 46 | No error boundaries | ✅ TRUE | Confirmed — no `ErrorBoundary`/`componentDidCatch` anywhere in `src/`. |
| 47 | No request cancellation | ❓ UNVERIFIED | Not checked. |
| 48 | No pagination in PlayersView | ✅ TRUE | Confirmed — `PlayersView.tsx` calls `api.getPlayers({ username: search || undefined, limit: 100 })` with a hardcoded limit, no `offset`, and no pagination controls in the component. |
| 49–51 | (WebSocket reconnection, console scroll lock, WS keepalive) | ❓ UNVERIFIED | Not checked. |

---

## 🟡 MEDIUM (32 claimed) — sampled

| # | Bug | Verdict | Evidence |
|---|-----|---------|----------|
| 52 | MFA secrets not encrypted | ✅ TRUE (self-documented) | `models/user.py:41-46` — `mfa_secret` stored as plaintext `String(64)`; the column's own comment admits this openly ("encrypted at rest is Phase 4's...scope...stored as-is here in the meantime"). `services/mfa_service.py` confirms no `encrypt_secret()` call anywhere. |
| 53 | Webhook secrets not encrypted | ✅ TRUE (deliberate) | `services/webhooks/service.py:69-73` stores `secret` in plaintext with a comment explaining it must be, to compute HMAC signatures — same tradeoff as documented for `ApiKey`. Real, but a considered design choice, not an accidental leak. |
| 54–57 | (sensitive settings masking, permission-change audit, webhook secret re-exposure, `.env` sync opt-in flags) | ❓ UNVERIFIED | Not checked. |
| 58 | Missing cascade delete / relationship in `models/ai.py` | ✅ TRUE (as literally stated) | `created_by` column exists with no `ForeignKey`/`relationship()` — may be intentional if it stores a Discord ID rather than a DB FK, didn't confirm intent either way. |
| 59 | Missing relationships in `models/moderation_intelligence.py` | ✅ TRUE | Confirmed — `ForeignKey` constraints exist (e.g. to `moderation_reports.id`), but no `relationship()` ORM attributes anywhere in the file for eager/lazy-loading convenience. |
| 60 | Missing indexes in `plugin_execution` | ✅ TRUE — ✅ **FIXED** (`92aad30`) | Confirmed — `actor_id` and `entrypoint` both defined without `index=True`, while sibling columns (`plugin_id`, `outcome`, `created_at`) do have it. |
| 61 | Text column for JSON in `plugin_kv`, no validation | ❓ UNVERIFIED | Not checked. |
| 62 | Missing indexes in `audit_log` | ✅ TRUE — ✅ **FIXED** (`92aad30`) | Confirmed — `actor_type` and `target` both lack `index=True`, while `action` and the timestamp column do have it. |
| 63 | Missing expiry index in `memory` | ✅ TRUE — ✅ **FIXED** (`a24477b`) | Confirmed — `expires_at` column has no `index=True`. |
| 64 | No FK in `anticheat_violation` | ✅ TRUE — ✅ **FIXED** (`a24477b`) | Confirmed — `player_uuid` is `String(36), index=True` but has no `ForeignKey("players.uuid")`. |
| 65 | Missing FK in `server_metrics` | ❌ FALSE (implied "no cleanup" is wrong) | Didn't verify the FK claim specifically, but the report's broader framing of this table lacking any lifecycle management is wrong: `services/operational_intelligence/metrics.py::purge_old_snapshots` runs a scheduled retention sweep against `settings.server_metric_retention_hours` (168h default), invoked from `sampler_loop.py`. |
| 66–71 | (batch auditing, security event retention, webhook retry, masked audit values, trace sampling, console line cleanup) | ❓ UNVERIFIED | Not checked. |
| 72 | Duplicate `NoParams` classes "in every file" | ⚠️ PARTIALLY TRUE — ✅ **FIXED** (`18baeb1`) | Found in 3 files in `capabilities/`, not "every file" — real duplication, but the claim overstates its extent. |
| 73 | Duplicate `_resolve_actor` pattern "in multiple files" | ❌ FALSE | Only one definition found (`capabilities/marketplace.py`) across `capabilities/`, `services/`, and `api/`. |
| 74 | No context memoization | ✅ TRUE | Confirmed — `DashboardContext.tsx`'s `<DashboardContext.Provider value={{...}}>` builds a brand-new object literal inline on every render, not wrapped in `useMemo`. Every consumer re-renders on every provider re-render regardless of which field changed. This is a real, verifiable perf bug. |
| 75–81 | (response caching, sidebar persistence, unsaved-changes warnings ×2, staff role validation, verification link validation, broadcast rate limiting) | ❓ UNVERIFIED | Not checked. |

---

## 🟢 LOW (36 claimed) — sampled

| # | Bug | Verdict | Evidence |
|---|-----|---------|----------|
| 85 | Unused import `ALL_TOOLS` | ✅ TRUE — ✅ **FIXED** (`18baeb1`) | Confirmed — imported in `capabilities/investigation.py:19`, never referenced anywhere else in the file. |
| 94–105 | (React.memo, useCallback/useMemo, error handling consistency, loading states, ARIA, ANSI colors, large SVGs/images, modal lazy loading, fuzzy search, keyboard nav, debouncing) | ⚠️ NOTE, mostly ❓ UNVERIFIED | Spot-checked `DashboardContext.tsx` specifically for #95 ("missing useCallback/useMemo") — this one is actually **partially false**: the file does use `useCallback` in several places (`setDoodleOpacity`, `handleToggleDoodles`, `setSelectedBrand`, etc.), contradicting a blanket "missing" claim for at least this file. Didn't check the rest. |
| 108 | TS strict mode disabled | ✅ TRUE | Confirmed — `tsconfig.json` has no `"strict"` key at all (defaults to `false`). |
| 109 | Path alias points to root, not `./src` | ✅ TRUE (and inconsistent with tsconfig) | Confirmed — `vite.config.ts`: `'@': path.resolve(__dirname, '.')`. Notably, `tsconfig.json`'s own `paths` mapping is *correct* (`"@/*": ["./src/*"]`), meaning type-checking/IDE resolution and the actual Vite bundler disagree — real, previously-unflagged bug distinct from what the report even claims. |
| 111 | No Suspense with lazy loading | ✅ TRUE | Same evidence as #45 — no `lazy(`/`Suspense` in `App.tsx`. |
| 114 | Missing `cyclonedx` dependency | ❌ FALSE | `cyclonedx-python-lib==11.11.0` is explicitly listed in `requirements-dev.txt`, and `scripts/generate_sbom.py`'s own docstring explains the deliberate choice of the library over the CLI wrapper. |
| 115 | `sys.path` manipulation risk | ✅ TRUE (but intentional/commented) | Confirmed in `scripts/export_openapi_schema.py:33`, with an explanatory comment justifying it (repo root needs to be importable for `import main`). Real but low-risk, single-purpose dev script. |
| 119 | No caching of vulnerability scan results | ✅ TRUE | Confirmed — no cache-related code in `scripts/scan_dependencies.py`. |
| 120 | No dry-run mode | ✅ TRUE | Confirmed — no `dry_run`/`dry-run` flag anywhere in `scripts/scan_dependencies.py`. |
| 124 | No logging config, uses `print()` | ✅ TRUE | Confirmed — 11 `print()` calls across `scripts/*.py`, no `logging` module usage found in those files. |
| *(all other LOW items)* | — | ❓ UNVERIFIED | Not checked — mostly subjective frontend-polish/accessibility opinions (missing ARIA labels, missing `React.memo`, virtualization, image lazy-loading, etc.) that are plausible on their face for a dashboard this size but weren't independently confirmed line-by-line given the time budget. |

---

## Summary

| | Checked | ✅ True | ⚠️ Partially true | ❌ False |
|---|---|---|---|---|
| Critical | 20 / 23 | 8 | 4 | 8 |
| High | ~14 / 32 | 8 | 1 | 3 (incl. 2 dupes) |
| Medium | ~14 / 32 | 9 | 1 | 2 |
| Low | ~10 / 36 | 7 | 1 | 1 |
| **Total** | **~58 / 124** | **32** | **7** | **14** |

**Roughly one in five checked claims is flatly wrong**, and several more are
technically-true-but-misleadingly-framed (intentional design decisions
presented as newly-discovered flaws, or real issues attributed to the wrong
file/line). The report is most reliable on frontend perf/DX gaps (code
splitting, error boundaries, context memoization, TS strict mode, Vite
alias) and DB indexing/relationship gaps — these held up consistently.
It's least reliable on anything involving "no rate limiting" (misses the
global middleware every time) and anything involving cleanup/retention
claims (misses that purge jobs already exist).

**Recommendation:** treat this report as a rough lead-generation list, not
a validated backlog. Before scheduling any item from it, re-confirm against
current code the way this pass did — several "critical" items here are
either already fixed, already-considered tradeoffs, or simply untrue.

No code was modified as part of this investigation, per instructions.
