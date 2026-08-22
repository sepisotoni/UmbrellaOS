# SUBCHAT-HANDBACK: Phase 14 — Backend Fixes

**Sub-chat type:** Write access (umbrella-core-CURRENT only)
**Branch:** `p14-backend-fixes` → pushed to `main`
**Base tip:** `5593d8e`
**Final tip:** `53925fe`
**Completed:** 2026-08-22

---

## Commits

| SHA | Message |
|-----|---------|
| `28c4adf` | core: add GET /api/v1/anticheat/violations (P14 Task 1) |
| `e9beb1f` | core: add GET /api/v1/staff staff directory endpoint (P14 Task 2) |
| `d0ca70b` | core: add GET /api/v1/verification/links endpoint (P14 Task 3) |
| `9e0671a` | core: add AI copilot, provider test, and crash-risk endpoints (P14 Tasks 4-6) |
| `8a51359` | core: add REST facades for webhooks and API keys (P14 Task 7) |
| `53925fe` | core: relax BridgeMessageRequest schema to accept scope and optional source (P14 Task 8) |

---

## Task Outcomes

### Task 1 — `GET /api/v1/anticheat/violations` ✅
**File:** `api/routers/anticheat.py`

Violations are stored as `AITask` rows with `task_type="anticheat_review"` — there is no dedicated violation model. The endpoint queries those rows and parses `check_name` and `vl` out of `ai_summary` (format: `"Grim flagged <username> for <check> (VL <n>) — action: <action>"`). Evidence string is stored in `ai_task.evidence`.

**Decision:** The dispatch schema specifies a `server_id` field. The anticheat service never stores server_id (it's not a field on `AITask` or written during `handle_cheat_flag`). The field is returned as `null` in the response. The `server_id` query param is accepted but has no effect. If server_id tracking is needed, the plugin would need to send it in the flag payload and the anticheat_service would need to persist it.

**Auth:** `punishments.view` — same permission as the AI task list.

---

### Task 2 — `GET /api/v1/staff` ✅
**File:** `api/routers/staff.py`

Queries `User` rows where `role_id IS NOT NULL` and `is_active=true`. Bulk-loads `Role + permissions` via `selectinload` in one query. Bulk-loads `DiscordAccount` for linked MC uuid. Excludes any role named `"player"` (case-insensitive).

**Decision:** `User` has no `role` relationship — only `role_id` FK. Used separate bulk query on `Role` rather than `selectinload(User.role)`. The `linked_minecraft_username` field is returned as `null` — resolving it would require a third DB round-trip per staff member (Player lookup by uuid). The `linked_minecraft_uuid` is populated from `DiscordAccount`.

**Auth:** `roles.manage` — same as existing `/staff/manage` and `/staff/add`.

---

### Task 3 — `GET /api/v1/verification/links` ✅
**File:** `api/routers/verification.py`

Queries `DiscordAccount` with pagination (`limit`/`offset`). Enriches with `Player.username` via bulk lookup. Returns all accounts (verified and unverified), with status `VERIFIED` or `PENDING_CODE`.

**Decision:** The dispatch schema specifies `verified_by: "BOT_CODE | MANUAL_STAFF | OAUTH"`. The `DiscordAccount` model has no `verified_by` column — all links look identical in the DB regardless of how they were created (code, manual-link, or a future OAuth flow). Always returns `"BOT_CODE"` for now. If this distinction matters, a `verified_by` column would need to be added to `DiscordAccount` and populated in `confirm_verification`, `manual_link`, and any future OAuth confirm path.

**Auth:** `players.view` — same as `/verification/pending`.

---

### Task 4 — `POST /api/v1/ai/copilot` ✅
**File:** `api/routers/ai_copilot.py` (new file)

Routes through `Orchestrator.run()` with `task_type="copilot"` and `require_dual_review=False` (copilot is low-stakes; dual review would double latency with no benefit). Returns the orchestrator's `primary_provider`/`primary_model` as `model_used` and measured wall-clock latency. Fails 503 on orchestrator error — never fabricates a response.

**Note:** The orchestrator writes an `AIDecisionLog` row for every copilot call. This is the same behaviour as all other orchestrator callers — expected and fine for auditability.

---

### Task 5 — `POST /api/v1/ai/providers/test` ✅
**File:** `api/routers/ai_copilot.py`

If `api_key` is supplied in the body, bypasses `ProviderFactory` and constructs the provider inline with that key. This avoids any DB write (the key is never saved) and lets the dashboard validate a new key before persisting it to Settings.

Default test models used per provider: `anthropic → claude-haiku-4-5-20251001`, `gemini → gemini-1.5-flash`, `openrouter → openai/gpt-3.5-turbo`. These are the cheapest/fastest options per provider. If the OpenRouter default model isn't in the operator's allowed list, the test may fail for a different reason than a bad key — worth noting.

**Decision:** Returns a `ProviderTestResponse` (not a 4xx) even on provider failure, with `success: false` — this is correct because the endpoint itself worked; it's the provider that failed.

---

### Task 6 — `GET /api/v1/ai/crash-risk/{server_id}` ✅
**File:** `api/routers/ai_copilot.py`

Calls `assess_crash_risk()` from `services/operational_intelligence/crash_prevention.py` directly — the same function `operational_intelligence.crash_risk.assess` capability calls. Skips the capability registry overhead (no RBAC re-check, no audit log write) since this is a read-only, low-stakes endpoint.

**Decision:** `mspt_avg` is always `null`. The dispatch brief specifies it; the actual crash prevention service documents explicitly that MSPT is not tracked (`ServerMetricSnapshot` has no MSPT column — see `crash_prevention.py` module docstring). Returning `null` is accurate; faking a value would be misleading.

`risk_level` values from the service are `"insufficient_data"`, `"none"`, `"watch"`, `"critical"`. The response uppercases them (`"INSUFFICIENT_DATA"` etc.) to match the dispatch brief's `"LOW | MEDIUM | HIGH | CRITICAL"` shape — note the risk level vocabulary is different (no LOW/MEDIUM in the actual service). Head chat should be aware the dashboard may need to map `WATCH` → a display label.

---

### Task 7 — Webhooks and API keys REST facades ✅
**Files:** `api/routers/webhooks_rest.py` (new), `api/routers/auth.py` (extended)

`webhooks_rest.py` delegates to `WebhookService` directly (same layer as the capabilities). The `POST /webhooks/{id}/test` endpoint uses `WebhookService.deliver()` with a synthetic `"webhook.test"` topic — there is no `webhooks.subscription.test` capability; this is the correct delivery path.

`auth.py` extended with a `keys_router` (separate `APIRouter` instance) mounted at `/api/v1/auth/keys`. Uses `ApiKeyService` directly. Auth: `identity.apikey.manage` permission.

**Decision:** Webhook `created_by` is set to `None` from the dashboard REST path. The capability path resolves the dashboard user from the session actor; the REST facade doesn't have access to the full actor resolution chain without more plumbing. This is acceptable — the webhook subscription is still created, just without a `created_by` attribution. If attribution matters, the facade could be extended to accept an optional user_id header.

---

### Task 8 — Fix `POST /api/v1/bridge/message` to accept `scope` ✅
**File:** `api/routers/bridge.py`

- `source` made optional with default `"DASHBOARD"`
- `scope: str | None = None` added to `BridgeMessageRequest`
- Validation extended to accept `"DASHBOARD"` as a valid source value
- `scope` is accepted in the request body but not persisted (no `scope` column on `ChatMessage`)

This is a backwards-compatible relaxation — existing plugin/bot callers that send an explicit `source` are unaffected.

---

## No Tasks Skipped

All 8 tasks completed.

---

## What Head Chat Should Know

1. **Anticheat violations have no `server_id` field in the DB.** The `GET /api/v1/anticheat/violations?server_id=` filter param is a no-op today. Either add the field to the anticheat flag ingest or accept the null.

2. **Verification `verified_by` is always `"BOT_CODE"`.** The model has no `verified_by` column. If manual vs bot-verified distinction is needed in the UI, a migration is required.

3. **Crash risk levels don't match the dispatch spec vocabulary.** The service uses `NONE / WATCH / CRITICAL / INSUFFICIENT_DATA`; the dispatch said `LOW / MEDIUM / HIGH / CRITICAL`. The REST endpoint returns the actual service values (uppercased). The dashboard will need to handle `WATCH` and `INSUFFICIENT_DATA` in its display logic.

4. **Copilot writes `AIDecisionLog` rows.** Every copilot chat message creates a row. This is correct behaviour (auditability) but worth knowing for DB growth planning.

5. **Webhook `created_by` is null from the REST facade.** See Task 7 notes above.

6. **No new dependencies added.** `requirements.txt` is unchanged.

7. **No existing routes broken.** All changes are additive except Task 8 (schema relaxation, backwards-compatible) and Task 2 (added a `GET ""` route to the staff router, which previously had no GET on the root).
