# Code Review: Settings, Knowledge, Webhooks, Bridge, Verification, Feature Flags
**Reviewed:**
- `umbrella-core-CURRENT/api/routers/settings.py`
- `umbrella-core-CURRENT/api/routers/knowledge.py`
- `umbrella-core-CURRENT/api/routers/webhooks_rest.py`
- `umbrella-core-CURRENT/api/routers/bridge.py`
- `umbrella-core-CURRENT/api/routers/verification.py`
- `umbrella-core-CURRENT/api/routers/feature_flags.py`
- `umbrella-core-CURRENT/services/settings_service.py`
- `umbrella-core-CURRENT/services/webhooks/service.py`
- `umbrella-core-CURRENT/services/knowledge/service.py`
- `umbrella-core-CURRENT/services/knowledge/repository.py`

**Also read for endpoint-vs-backend comparison (not edited):**
`models/setting.py`, `models/knowledge.py`, `models/webhook.py`, `models/discord.py`, `models/verification.py`, `models/player.py`, `models/feature_flag.py`, `services/feature_flag_service.py`, `capabilities/webhooks.py`, `api/middleware/auth.py`, `api/dependencies/permissions.py`, `database/engine.py` (`get_db`), dashboard `src/lib/api.ts` (settings/knowledge/bridge callers), plugin `VerificationCommand.java`, bot `verification_cog.py`.

**Date:** 2026-08-29

**Method:** Static review of routers against models/services/auth. Tests and live servers were not executed (reviewer skill constraint). Claims about runtime 500s are from column widths and FK/unique constraints in the models, not from a live insert.

## Summary

These surfaces are real, mounted in `main.py`, and mostly talk to real tables. The highest-risk problems are not missing routes — they are **routers that disagree with their own comments, models, or callers**. Settings GET treats every successful auth result as a string, so the “mask secrets for dashboard sessions” branch never runs. Knowledge create and plugin verification both write IDs longer than the VARCHAR columns they target. Dashboard broadcasts use `source: "DASHBOARD"`, which the bridge stores but never marks as forwarded. In-game `/verify` and Discord confirm are two incompatible flows sharing one `VerificationCode` table that has no Discord identity column.

Overall risk: **High** (secrets exposure + several 100%-fail write paths under Postgres VARCHAR limits).

## Findings

### [FINDING-001] Settings GET never masks secrets for dashboard sessions
- **Severity:** Critical
- **File:** `api/routers/settings.py`, lines ~21–46; `api/middleware/auth.py` `require_admin_hmac_or_session` / `require_admin_key`
- **Issue:** Both `GET /api/v1/settings` and `GET /api/v1/settings/{key}` set `unmasked = isinstance(auth, str)`. `require_admin_hmac_or_session` always returns a **string** (`"hmac"`, `"plugin"`, the raw admin key, or `"session"`). It never returns a `User`. The comments claim dashboard session callers get `***`; that condition is unreachable.
- **Edge-case:** Any valid Bearer session (not only owner) can list settings and receive `discord.bot_token`, RCON password, and AI provider keys in plaintext. Writes are still `require_owner`; reads are not even `settings.view`.
- **Recommendation:** Drive masking from the actual auth kind (session vs admin-key/HMAC/plugin), and gate list/get on `settings.view` (or owner-only if that is the intended policy). Reconcile with `tests/test_settings.py::test_sensitive_settings_are_masked`, which asserts the comment’s behavior.

### [FINDING-002] Settings GET is not owner- or `settings.view`-gated
- **Severity:** High
- **File:** `api/routers/settings.py`, lines ~20–37; contrast PATCH/POST using `require_owner`
- **Issue:** Read endpoints only require `require_admin_hmac_or_session` (any logged-in dashboard user, plus plugin key). `settings.view` exists in `services/roles_service.py` and is used by `GET /api/v1/bridge/settings`, but not here.
- **Edge-case:** A helper/moderator session that can call Core at all can dump the full settings registry (and, given FINDING-001, unmasked secrets).
- **Recommendation:** Align GET auth with the permission model already used for other settings surfaces.

### [FINDING-003] POST `/{key}` upsert create bypasses `SettingsService` rules
- **Severity:** High
- **File:** `api/routers/settings.py`, lines ~49–86 vs `services/settings_service.py` `update` / `DEFAULT_SETTINGS` / `write_env_value`
- **Issue:** If the key does not exist, the router inserts a `Setting` with `sensitive=False`, `requires_restart=False`, a synthetic description, commits itself, and returns `_to_dict(..., unmasked=False)`. It does not copy sensitivity/restart flags from `DEFAULT_SETTINGS`, does not write an audit log, and does not call `write_env_value` (so keys in `ENV_KEY_MAP` never sync to `.env` on first create).
- **Edge-case:** Creating `discord.bot_token` or `rcon.password` through POST (tests, seeding tools, dashboard POST) stores a live secret as non-sensitive; subsequent GETs return it even if masking were fixed. PATCH of an already-seeded row still audits and syncs `.env`.
- **Recommendation:** Create-or-update should go through one service path that applies the same sensitivity, audit, and env-sync rules as update.

### [FINDING-004] Knowledge create writes `discord_message_id` longer than the column
- **Severity:** High
- **File:** `api/routers/knowledge.py`, lines ~158–171; `models/knowledge.py` `discord_message_id` `String(32)`; migration `018_knowledge_base.py`
- **Issue:** Dashboard create sets `discord_message_id=f"dashboard-{uuid.uuid4()}"` (`dashboard-` + 36-char UUID = **46 characters**). The column and migration are VARCHAR(32). This path does not use `KnowledgeService.index_entry` (commented as intentional), so the service-layer tests never catch it.
- **Edge-case:** Staff “Add entry” from the dashboard against Postgres: insert fails (string-data-right-truncation / 500). SQLite test DBs may not enforce the same length, so the suite can stay green.
- **Recommendation:** Generate an ID that fits the column (or widen the column in model + migration) and cover REST create in tests against the real type.

### [FINDING-005] Knowledge REST ignores the knowledge permission keys
- **Severity:** High
- **File:** `api/routers/knowledge.py` (all endpoints); contrast `capabilities/knowledge.py` (`knowledge.entry.manage` / search / review)
- **Issue:** Every REST handler uses `require_admin_hmac_or_session` only. Helper is seeded with `knowledge.entry.search` but not manage/review; REST still allows that session to create, patch, delete, approve, and reject.
- **Edge-case:** Any authenticated dashboard user who can reach `/api/v1/knowledge` can hard-delete the knowledge base. Capability invoke remains permissioned; the dashboard client calls REST (`src/lib/api.ts`).
- **Recommendation:** Use the same permission keys as the capabilities (search vs manage vs correction review).

### [FINDING-006] Knowledge list/`status` and approve/reject do not match retrieval rules
- **Severity:** Medium
- **File:** `api/routers/knowledge.py` list handler ~112–127; `services/knowledge/repository.py` `search` / `approve` / `reject`
- **Issue:** Default list uses `KnowledgeRepository.search` (approved + non-superseded). `?status=` filters only `review_status` and still returns superseded rows. `approve`/`reject` do not require `PENDING`; approving an already-approved correction re-points `superseded_by_id`; rejecting a live approved entry removes it from search without restoring a predecessor.
- **Edge-case:** Dashboard filter “approved” shows obsolete superseded copies as current. Double-click approve/reject on the wrong row silently mutates live retrieval.
- **Recommendation:** Status-filtered list should apply the same superseded rule as search; approve/reject should only accept `PENDING` (or define an explicit re-open workflow).

### [FINDING-007] Knowledge mutations have no audit trail
- **Severity:** Medium
- **File:** `api/routers/knowledge.py` create/patch/delete/approve/reject
- **Issue:** State-changing operations flush only. Unlike `SettingsService.update` and verification confirm/revoke, they never write `AuditLog`. Actor attribution is also wrong for sessions: `_actor_id` / `_actor_name` only see a `User` if auth is a `User`, but HMAC/session auth is a string, so every dashboard edit is stored as author `"admin"`.
- **Edge-case:** Cannot tell which staff member deleted or edited an entry.
- **Recommendation:** Record actor from the real session user and audit create/update/delete/review.

### [FINDING-008] REST webhooks are an incomplete shadow of `WebhookService` / capabilities
- **Severity:** Medium
- **File:** `api/routers/webhooks_rest.py`; `services/webhooks/service.py` `update`; `capabilities/webhooks.py`
- **Issue:** REST exposes list/create/delete/test. The service and capabilities also support **update** (URL / `active`). REST create always passes `created_by=None` (capabilities resolve a user id). Module docstring says the dashboard calls these paths; the current dashboard tree has **no** `/api/v1/webhooks` client. Design docs say capabilities are the public surface (“no shadow APIs”).
- **Edge-case:** A caller can create a hook via REST but cannot pause it without the capability invoke API. Attribution on REST-created rows is always null.
- **Recommendation:** Either drop REST and point the dashboard at capabilities, or implement the same update/audit/`created_by` behavior on REST.

### [FINDING-009] Webhook delete maps every exception to HTTP 404
- **Severity:** Medium
- **File:** `api/routers/webhooks_rest.py`, lines ~81–93
- **Issue:** `except Exception` around `WebhookService.delete` is re-raised as 404. Missing rows raise `ResourceNotFoundException` (already 404). Database errors, programming errors, and unexpected `WebhookError` become “not found”.
- **Edge-case:** A failed DELETE due to a DB outage looks like a missing subscription; the client may stop retrying.
- **Recommendation:** Translate only not-found; let other errors surface as 5xx / AppException.

### [FINDING-010] Webhook URLs are not constrained beyond `http://` / `https://`
- **Severity:** Medium
- **File:** `services/webhooks/service.py` `create` / `update`; REST create and `POST .../test` call into delivery
- **Issue:** Any http(s) URL is stored and POSTed to (5s timeout), including loopback, link-local, and cloud metadata addresses. `WebhookDeliveryService.deliver` has no allowlist. Test delivery hits the URL immediately as the authenticated operator.
- **Edge-case:** An operator (or stolen `webhooks.subscription.manage` key) registers `http://127.0.0.1:...` or an internal admin port and uses test/delivery as SSRF.
- **Recommendation:** Restrict destinations (block private/link-local/metadata; prefer HTTPS) before persist and before test delivery.

### [FINDING-011] Dashboard bridge broadcasts are never forwarded
- **Severity:** High
- **File:** `api/routers/bridge.py` `receive_bridge_message` ~83–157; dashboard `src/lib/api.ts` `broadcastMessage` (`source: 'DASHBOARD'`)
- **Issue:** `DASHBOARD` is accepted and persisted. Forwarding only sets `forwarded=True` for `minecraft` or `discord` when mode is `full`/`partial`. `DASHBOARD` always returns `forwarded: false`, `targets: []`. `body.scope` is accepted on the request model and never read.
- **Edge-case:** Staff global broadcast from the dashboard stores a chat row but plugin/bot consumers that honor `forwarded` will not send it to Minecraft or Discord. `GET /messages?source=DASHBOARD` is also rejected (filter only allows `minecraft`/`discord`).
- **Recommendation:** Define where dashboard broadcasts should go (both directions vs a dedicated channel) and set `forwarded`/`targets` accordingly; allow listing `DASHBOARD` if those rows are meant to be visible.

### [FINDING-012] Bridge settings writes skip `SettingsService` (no audit, no env sync)
- **Severity:** Low
- **File:** `api/routers/bridge.py` `update_bridge_settings`; `services/settings_service.py` `update`
- **Issue:** PATCH upserts `bridge.*` rows directly. Core settings PATCH audits `settings.update`. Bridge toggles leave no audit row. Boolean compare is exact `"true"` (other casings read as false).
- **Edge-case:** Cannot reconstruct who turned the bridge on. A value `"True"` from a hand edit silently disables forwarding.
- **Recommendation:** Route bridge setting changes through the settings service (or equivalent audit) and parse booleans consistently.

### [FINDING-013] Plugin `/verify-code` cannot store a real Discord link
- **Severity:** High
- **File:** `api/routers/verification.py` `plugin_verify_code` ~583–710; `models/verification.py` (no `discord_id` on `VerificationCode`); `models/discord.py` `discord_id` `String(32)`
- **Issue:** In-game `/verify` (plugin) POSTs `{code, minecraft_uuid, ...}`. The handler looks up a code, then either updates a `DiscordAccount` keyed by **the code’s player_uuid** or **creates** `discord_id=f"pending_mc:{player_uuid}"` (`pending_mc:` + 36-char UUID = **47 characters** vs VARCHAR(32)). `VerificationCode` has no Discord identity. Discord’s live path is `verification.confirm` with `discord_id` after the player DMs a **Minecraft-issued** code (`verification_cog.py`). Nothing in this repo’s Discord client calls `POST /verification/request`. Templates still tell players to type a Discord-issued code in-game.
- **Edge-case:** First-time `/verify` with no pre-existing `DiscordAccount` fails on Postgres length. If a row existed, the code is consumed and the Minecraft UUID may be overwritten **without checking that `vc.player_uuid` matches the caller**, so player B can burn player A’s code. Success responses can report `discord_username=None` and a fake Discord snowflake.
- **Recommendation:** One flow: either MC issues codes and Discord confirms (current `confirm` / capability), or Discord issues codes bound to `discord_id` and `/verify-code` consumes that binding. Enforce code ownership; never invent `pending_mc:` IDs that do not fit the column.

### [FINDING-014] `POST /manual-link` placeholder UUID does not fit `players.uuid`
- **Severity:** High
- **File:** `api/routers/verification.py` `manual_link` ~367–380; `models/player.py` `uuid` `String(36)`
- **Issue:** Missing players get `uuid = f"manual-{uuid4()}"` (7 + 36 = **43 characters**). Primary key is VARCHAR(36).
- **Edge-case:** Dashboard manual link for a username with no `Player` row fails on insert (Postgres). The success message claims “UUID resolves on next join.”
- **Recommendation:** Use a 36-character UUID (or another legal PK) and a separate pending marker that `resolve-pending` actually understands.

### [FINDING-015] `POST /resolve-pending` looks for a marker nothing writes
- **Severity:** High
- **File:** `api/routers/verification.py` `resolve_pending` ~449–479 vs `manual_link`
- **Issue:** Docstring and query look up `DiscordAccount.player_uuid == "pending:<username>"`. `manual-link` writes `manual-{uuid}` on **Player.uuid**, not `pending:` on DiscordAccount. No other file in this repo writes `pending:`. Plugin join calling this endpoint always gets `{resolved: false}` for staff manual links.
- **Edge-case:** Manual links never attach to the real UUID on join via this endpoint. Stale placeholder player rows remain.
- **Recommendation:** Use one pending-token scheme in both write and resolve paths (and in the plugin).

### [FINDING-016] `GET /links` does not match its own contract
- **Severity:** Medium
- **File:** `api/routers/verification.py` `list_verification_links` ~496–547
- **Issue:** Docstring says “all verified” links. Query loads **all** `DiscordAccount` rows. `verified=False` is labeled `PENDING_CODE` even after revoke/unlink. `verified_by` is hardcoded `"BOT_CODE"` including manual-link rows.
- **Edge-case:** Dashboard verification table mixes revoked/unlinked accounts into the verified list and attributes them to the bot.
- **Recommendation:** Filter (or paginate) by `verified`, and persist/return a real `verified_by` when the link was manual.

### [FINDING-017] Verification codes are globally unique including used/expired rows
- **Severity:** Medium
- **File:** `models/verification.py` `code` unique; `api/routers/verification.py` `request_verification` ~140–151
- **Issue:** New codes are six digits (`100000`–`999999`) with a table-wide unique constraint. Old used codes still occupy the namespace. `request` does not invalidate prior unused codes for the same player (multiple live codes possible until they expire).
- **Edge-case:** After enough historical verifications, `flush` hits unique violation (500) on a random collision. Two unused codes for one player can both confirm depending on which is submitted first (`scalar_one_or_none` on code).
- **Recommendation:** Unique among unused/unexpired only (or recycle used codes); invalidate older unused codes for the same player on request.

### [FINDING-018] Revoke reports success when nothing was revoked
- **Severity:** Low
- **File:** `api/routers/verification.py` `revoke_verification` ~323–349
- **Issue:** Missing `DiscordAccount` still returns `{"success": true}` with no audit row. Callers cannot distinguish “revoked” from “never linked.”
- **Edge-case:** Staff revoke on a typo UUID looks successful.
- **Recommendation:** Return 404 (or `success: false`) when no account exists.

### [FINDING-019] Feature-flag upsert cannot clear description; no audit
- **Severity:** Low
- **File:** `services/feature_flag_service.py` `set_flag` (`if description:` skips empty string); `api/routers/feature_flags.py` POST/DELETE
- **Issue:** Updating a flag with `description=""` leaves the old description. Create/update/delete do not write `AuditLog`. Router GET-by-name queries the model directly instead of the service (behavior is equivalent for found rows).
- **Edge-case:** Dashboard “clear description” appears to save but the old text remains. No trail of who toggled a flag.
- **Recommendation:** Treat empty description as an explicit clear; audit manage operations.

### [FINDING-020] SettingsService documents Redis caching that is not implemented
- **Severity:** Low
- **File:** `services/settings_service.py` module docstring vs body
- **Issue:** Docstring claims 60s Redis cache invalidated on write. There is no Redis read/write/invalidate in this service. Callers that assumed cache-after-write semantics are actually always hitting the DB (not a functional outage, but the documented contract is false).
- **Edge-case:** None for correctness today; a later “add cache” change could be duplicated or skip invalidation because the comment already claims it exists.
- **Recommendation:** Remove the claim or implement cache + invalidation as described.

## Already-Documented Issues (Skipped)

- **Bug #8** (`CRITICAL-FINDINGS-2026-08-17.md`, `cross-chat-findings/review-4-moderation-verification-appeals-2026-08-17.md`): `verification.confirm` FK failure because `request` never created a `players` row. Current `request_verification` upserts a `Player` before inserting the code. Not re-reported. Residual risk: `confirm` / `services/verification/service.py` still mark `used=True` before 409 conflict checks; persistence depends on `get_db` rolling back `HTTPException`.
- **Webhook capability `id` vs `subscription_id`:** `cross-chat-findings/review-6-untested-surfaces-2026-08-17.md`. Capabilities now accept both field names. REST uses a path parameter. Not re-reported as a functional bug.
- **Bridge live CRUD** in review-6: exercised `minecraft`/`discord` sources, not dashboard `DASHBOARD` broadcasts (FINDING-011 is new).
- **Rate limiter / migration bootstrap / appeals / kick-ipban check constraints:** out of scope for this file set; already in `CRITICAL-FINDINGS-2026-08-17.md`.
