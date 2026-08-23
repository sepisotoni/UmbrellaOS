# BACKEND_REQUIREMENTS.md
# UmbrellaOS Dashboard — Backend Endpoint Reference
# Generated from reading umbrella-core-CURRENT/api/routers/* directly.

---

## Health

| Method | Path | Notes |
|--------|------|-------|
| GET | `/health` | No auth. Used for DISCONNECTED banner (polled every 30s). Returns `{status, version, database, redis, service}`. |

---

## Auth

| Method | Path | Body / Params | Notes |
|--------|------|---------------|-------|
| POST | `/api/v1/auth/discord/authorize` | `{redirect_uri}` | Returns `{authorize_url, state}`. No auth required. |
| POST | `/api/v1/auth/discord/callback` | `{state, code, redirect_uri}` | Returns `{token, user, expires_in}`. No auth required. |
| GET | `/api/v1/auth/me` | Bearer token | Returns `UserSchema`. |
| POST | `/api/v1/auth/logout` | Query: `?session_token=` | Returns `{success}`. Sets `session.revoked = True`. |

---

## Dashboard / Fleet

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/dashboard/servers` | Lists servers from `PluginHeartbeat` rows seen in last 3 minutes. Returns `list[dict]` with `id, name, status, tps, players, maxPlayers, version, pluginsConnected, pluginsTotal`. `ramUsedMb`/`ramTotalMb`/`cpu` always 0 — not tracked. |
| GET | `/api/v1/dashboard/plugins` | Lists UmbrellaOS + GrimAC entries per active server. |

---

## Players

| Method | Path | Params | Notes |
|--------|------|--------|-------|
| GET | `/api/v1/players` | `username` (ilike), `skip`, `limit` (max 100) | |
| GET | `/api/v1/players/{uuid}` | — | Includes `ip_addresses`. |
| GET | `/api/v1/players/{uuid}/full-profile` | — | **Ordered before `/{uuid}`** in router. Returns all sub-data in one call. Queries `AnticheatViolation` with graceful fallback if model not migrated yet. |

---

## Punishments

| Method | Path | Body / Params | Notes |
|--------|------|---------------|-------|
| GET | `/api/v1/punishments` | `player_uuid`, `active_only` (default **True**), `skip`, `limit` | Pass `active_only=false` to see all. |
| POST | `/api/v1/punishments` | `{player_uuid, type, reason, expires_at?, staff_id?}` | Returns 404 if player not found. |
| POST | `/api/v1/punishments/{id}/revoke` | No body | Sets `active=False`. **Use POST, not PATCH.** |

---

## Appeals

| Method | Path | Body / Params | Notes |
|--------|------|---------------|-------|
| GET | `/api/v1/appeals` | `status`, `player_uuid`, `skip`, `limit` | Status values seen in DB: `pending`, `ACCEPTED`, `REJECTED`, `ESCALATED`, `REVIEW_SCHEDULED`, `REDUCED`. |
| POST | `/api/v1/appeals/{id}/close` | `{action, staff_note?, new_expiry?}` | Valid actions: `ACCEPT`, `REDUCE_SENTENCE`, `REJECT`, `ESCALATE`, `SCHEDULE_REVIEW`. `new_expiry` required when action=`REDUCE_SENTENCE`. Returns `AppealSchema` with `action_taken`, `handled_by`, `case_summary`, `closed_at` populated. |

---

## Anticheat

| Method | Path | Params | Notes |
|--------|------|--------|-------|
| GET | `/api/v1/anticheat/violations` | `player_uuid`, `server_id`, `check_name` (ilike), `limit` (max 200, default 50) | Reads `AnticheatViolation` table. `created_at` is mapped from `timestamp` column. |

---

## Staff

| Method | Path | Body | Notes |
|--------|------|------|-------|
| GET | `/api/v1/staff` | — | Returns users with `role_id IS NOT NULL` and `is_active=True`, excluding `player` role. Includes `linked_minecraft_uuid`. |
| POST | `/api/v1/staff/manage` | `{user_id, action: "promote"\|"demote"}` | Walks `ROLE_LADDER` in `staff_service.py`. |
| POST | `/api/v1/staff/add` | `{discord_id, role, username?}` | Returns 403 if role=`owner`. |

---

## Verification

| Method | Path | Params / Body | Notes |
|--------|------|---------------|-------|
| GET | `/api/v1/verification/links` | `limit` (max 200), `offset` | Lists `DiscordAccount` rows enriched with player usernames. `verified_by` always `"BOT_CODE"`. |
| GET | `/api/v1/verification/pending` | — | Active, unexpired `VerificationCode` rows. |
| DELETE | `/api/v1/verification/unlink/{discord_id}` | — | Sets `verified=False, player_uuid=None, linked_at=None`. Returns `{success}`. |

---

## Alt Detection

| Method | Path | Body / Params | Notes |
|--------|------|---------------|-------|
| GET | `/api/v1/alts/flagged` | `skip`, `limit` | Players with `suspicion_score >= 80`. |
| GET | `/api/v1/alts/groups` | — | **Only returns `confirmed=True` groups.** |
| POST | `/api/v1/alts/false-positive` | `{event_id?, player_uuid?, reviewed_by}` | One of `event_id` or `player_uuid` required (422 otherwise). Marks most recent event for player as false positive and reduces their score. |

---

## AI Tasks

| Method | Path | Body / Params | Notes |
|--------|------|---------------|-------|
| GET | `/api/v1/ai/tasks` | `status`, `task_type`, `skip`, `limit` (max 200) | |
| GET | `/api/v1/ai/tasks/{task_id}` | — | Returns with `evidence` blob. |
| POST | `/api/v1/ai/tasks/{task_id}/approve` | `{action_taken, reviewed_by}` | **Both fields required** — omitting either returns 422. Returns 400 if task not `pending`. |
| POST | `/api/v1/ai/tasks/{task_id}/deny` | `{reviewed_by, reason?}` | Returns 400 if task not `pending`. |
| POST | `/api/v1/ai/review/player/{uuid}` | No body | Returns 503 (not 400) on AI failure — dashboard shows Re-review button. |
| POST | `/api/v1/ai/review/appeal/{appeal_id}` | No body | Returns 503 on AI failure. Response also includes `ai_review_status` and `ai_result`. |

---

## AI Copilot & Crash Risk

| Method | Path | Body | Notes |
|--------|------|------|-------|
| POST | `/api/v1/ai/copilot` | `{message, context?}` | Returns `{response, model_used, latency_ms}`. Returns 503 if no provider available — never fakes a response. |
| GET | `/api/v1/ai/crash-risk/{server_id}` | — | Real enum values: `INSUFFICIENT_DATA`, `NONE`, `WATCH`, `CRITICAL`. `mspt_avg` always null (not tracked). |

---

## AI Config (per-task model assignments)

| Method | Path | Body | Notes |
|--------|------|------|-------|
| GET | `/api/v1/ai/config/tasks` | — | Returns `{player_review, appeal_review, copilot, crash_risk, chat_responder}` each with `{primary, failover}`. Falls back to defaults if not yet configured in DB. |
| POST | `/api/v1/ai/config/tasks` | `{task, primary, failover?}` | Valid providers: `gemini`, `anthropic`, `openai`, `deepseek`, `openrouter`. Returns full updated config. |
| POST | `/api/v1/ai/providers/test` | `{provider, api_key?}` | Live key test. `api_key` overrides DB setting for this test only. Returns `{success, latency_ms, message, model}`. |

---

## Audit Log

| Method | Path | Params | Notes |
|--------|------|--------|-------|
| GET | `/api/v1/audit` | `limit` (max 200), `offset`, `actor_type` | Delegates to `platform.audit.search` capability. Returns `{items: [...], total: N}`. |

---

## Feature Flags

| Method | Path | Body | Notes |
|--------|------|------|-------|
| GET | `/api/v1/feature-flags` | — | |
| POST | `/api/v1/feature-flags` | `{name, enabled, description}` | Upsert by name. Returns **200** (not 201). |

---

## Settings

| Method | Path | Body | Notes |
|--------|------|------|-------|
| GET | `/api/v1/settings` | — | Sensitive values masked for session-auth users; unmasked for admin-key. Requires owner role or admin key. |
| GET | `/api/v1/settings/{key}` | — | 404 if key not found. |
| POST | `/api/v1/settings/{key}` | `{value}` | **Preferred** — upsert, creates key if not exists. Derives `category` from key prefix. Returns 400 if value is `"***"`. |
| PATCH | `/api/v1/settings/{key}` | `{value}` | Update only — returns 404 if key not found. |

---

## WebSocket — Console

| Protocol | Path | Auth | Notes |
|----------|------|------|-------|
| WS | `/api/v1/hosting/servers/{server_id}/console` | `?token=` query param | Browser WebSockets cannot set headers — token travels as query param, validated identically to Bearer. Proxied through Core to the node daemon. Connects **only** when staff opens the Console page; disconnects on page leave. Requires `hosting.server.view` permission. |

---

## Auth Headers Summary

- **Session auth**: `Authorization: Bearer <token>` on all dashboard requests
- **Admin key**: `X-Admin-Key` — used only for plugin/bot integration; dashboard always uses session tokens

## Key Gotchas (verified from source)

1. `GET /api/v1/players/{uuid}/full-profile` is declared **before** `GET /api/v1/players/{uuid}` in the router — FastAPI matches it correctly without path conflict.
2. `POST /api/v1/punishments/{id}/revoke` takes **no body**. Using PATCH returns 405.
3. `POST /api/v1/ai/tasks/{id}/approve` requires **both** `action_taken` and `reviewed_by` — the backend 422s if either is missing.
4. `GET /api/v1/anticheat/violations` returns `created_at` mapped from the model's `timestamp` column, not a column literally named `created_at`.
5. Crash risk levels are `INSUFFICIENT_DATA`, `NONE`, `WATCH`, `CRITICAL` — not LOW/MEDIUM/HIGH.
6. The audit endpoint returns `{items: [...], total: N}`, not a bare list.
7. `POST /api/v1/feature-flags` returns HTTP **200**, not 201.
8. `ramUsedMb`, `ramTotalMb`, `cpu` in server records are always 0 — the plugin heartbeat does not send these.
9. AI review endpoints return **503** (not 400) on AI failure so the dashboard can show a Re-review button without treating it as a client error.
10. The dashboard never connects to Supabase/Postgres directly — all data flows through Core's REST/WS APIs.
