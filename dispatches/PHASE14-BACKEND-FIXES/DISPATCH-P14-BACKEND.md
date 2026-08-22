# DISPATCH: Phase 14 — Backend Fixes & Missing Endpoints

**Type:** Sub-chat (write access)
**Scope:** `umbrella-core-CURRENT/` only — do NOT touch `umbrella-dashboard-CURRENT/`
**Write PAT:** [WRITE_PAT — see head chat]
**Read-only PAT:** [READ_ONLY_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip at dispatch time:** db986b8

---

## Context

Read these first before touching any code:
- `PHASE14-QUALITY-AUDIT.md` — the full audit. This is your spec.
- `umbrella-core-CURRENT/main.py` — all mounted routers and prefixes
- `umbrella-core-CURRENT/api/routers/` — all existing routers
- `umbrella-core-CURRENT/api/schemas/` — existing Pydantic schemas
- `umbrella-core-CURRENT/services/` — business logic layer

The backend is **FastAPI + Python**. Follow the exact same patterns as existing routers. Use existing service classes — do not duplicate business logic. All routes go under `/api/v1/`.

---

## Tasks

### Task 1 — Add `GET /api/v1/anticheat/violations`

**File:** `umbrella-core-CURRENT/api/routers/anticheat.py`

The plugin already writes cheat flags to the DB via `POST /api/v1/anticheat/flag`. There is no read endpoint. Add one.

```python
GET /api/v1/anticheat/violations
Query params: player_uuid (optional), server_id (optional), check_name (optional), limit (int, default 50, max 200)
Response: list of violation records
```

Response schema (add to schemas if needed):
```json
{
  "id": "string",
  "player_uuid": "string",
  "player_name": "string",
  "server_id": "string",
  "check_name": "string",
  "verbose": "string",
  "vl": 0,
  "created_at": "ISO8601"
}
```

Look at what the `handle_cheat_flag` handler stores in the DB and return those fields. Mount it in `main.py` if the router isn't already included (it should be — just add the route).

---

### Task 2 — Add `GET /api/v1/staff` (staff list)

**File:** `umbrella-core-CURRENT/api/routers/staff.py`

The staff router has `POST /manage`, `POST /add`, `GET /discord-members` but no list of existing staff users. The dashboard needs `GET /api/v1/staff` to populate the staff directory.

Add:
```python
GET /api/v1/staff
Response: list of User records where role != 'player' (i.e. staff members)
```

Response schema — same shape as `GET /api/v1/auth/me` but as a list:
```json
[{
  "id": "string",
  "discord_id": "string",
  "username": "string",
  "discriminator": "string",
  "avatar_url": "string",
  "role": "string",
  "permissions": [],
  "email": "string | null",
  "linked_minecraft_uuid": "string | null",
  "linked_minecraft_username": "string | null"
}]
```

Look at how `GET /api/v1/auth/users` works (it exists) and follow the same pattern. Filter to non-player roles.

---

### Task 3 — Add `GET /api/v1/verification/links`

**File:** `umbrella-core-CURRENT/api/routers/verification.py`

The verification router has pending, confirm, unlink, manual-link — but no endpoint to list all existing verified links. Add:

```python
GET /api/v1/verification/links
Query params: limit (default 50), offset (default 0)
Response: list of verified Discord↔MC links
```

Response schema:
```json
[{
  "id": "string",
  "discord_id": "string",
  "discord_username": "string",
  "minecraft_uuid": "string",
  "minecraft_username": "string",
  "linked_at": "ISO8601",
  "verified_by": "BOT_CODE | MANUAL_STAFF | OAUTH",
  "status": "VERIFIED | PENDING_CODE | EXPIRED"
}]
```

Query the existing verification/link table. Look at how existing verification routes query the DB and follow the same pattern.

---

### Task 4 — Add copilot chat endpoint

**File:** `umbrella-core-CURRENT/api/routers/ai_tasks.py` (or create `ai_copilot.py` if cleaner)

The dashboard's copilot chat is entirely a local simulation. The backend has a real AI orchestrator at `services/ai/orchestrator.py`. Add a thin REST endpoint that routes copilot prompts through it.

```python
POST /api/v1/ai/copilot
Body: { "message": "string", "context": "string | null" }
Response: { "response": "string", "model_used": "string", "latency_ms": int }
```

Implementation:
- Call `orchestrator.run()` (or whichever method generates a response) with the message and a system prompt like: "You are UmbrellaOS Copilot, an assistant for Minecraft server network administration."
- Return the result with the model name and latency
- If the orchestrator fails, return a 503 with a clear error message — don't fake a response

Mount the new route in `main.py` if you create a new router file.

---

### Task 5 — Add `POST /api/v1/ai/providers/test`

**File:** same router as Task 4

The dashboard's AI provider test button calls this. Add:

```python
POST /api/v1/ai/providers/test
Body: { "provider": "gemini | anthropic | openrouter", "api_key": "string | null" }
Response: { "success": bool, "latency_ms": int, "message": "string", "model": "string" }
```

Implementation:
- Get the provider via `ProviderFactory` (look at how `model_router.py` does it)
- Send a minimal test prompt ("Hello")
- Time it
- Return success/failure with latency
- If `api_key` is provided in the body, use it for the test (so the dashboard can test a new key before saving it)

---

### Task 6 — Add `GET /api/v1/ai/crash-risk/{server_id}`

**File:** same router as Task 4

The `operational_intelligence.crash_risk.assess` capability is built but not exposed via REST. Add:

```python
GET /api/v1/ai/crash-risk/{server_id}
Response: {
  "server_id": "string",
  "risk_level": "LOW | MEDIUM | HIGH | CRITICAL",
  "tps_trend": "float",
  "mspt_avg": "float",
  "recommendation": "string",
  "assessed_at": "ISO8601"
}
```

Call the capability via `capability_registry.invoke("operational_intelligence.crash_risk.assess", {"server_id": server_id})` — look at how other routes delegate to capabilities and follow the same pattern.

---

### Task 7 — Add thin REST facades for webhooks and API keys

The dashboard calls `/api/v1/webhooks` and `/api/v1/auth/keys` but these systems live behind the capabilities router. Add thin REST facades.

**Webhooks** — create `umbrella-core-CURRENT/api/routers/webhooks_rest.py`:
```python
GET /api/v1/webhooks → delegates to webhooks.subscription.list capability
POST /api/v1/webhooks → delegates to webhooks.subscription.create capability  
DELETE /api/v1/webhooks/{id} → delegates to webhooks.subscription.delete capability
POST /api/v1/webhooks/{id}/test → delegates to webhooks.subscription.test capability
```

**API Keys** — add to `umbrella-core-CURRENT/api/routers/auth.py` or create `auth_keys.py`:
```python
GET /api/v1/auth/keys → delegates to identity.api_key.list capability
POST /api/v1/auth/keys → delegates to identity.api_key.create capability
DELETE /api/v1/auth/keys/{id} → delegates to identity.api_key.revoke capability
```

Mount both in `main.py`.

---

### Task 8 — Fix `POST /api/v1/bridge/message` to accept `scope`

**File:** `umbrella-core-CURRENT/api/routers/bridge.py`

The dashboard's `broadcastGlobalMessage()` sends `{message, scope}` but the bridge router's request model doesn't have a `scope` field and requires `source`. 

- Add `scope: Optional[str] = None` to the bridge message request schema
- Make `source` optional with a default of `"DASHBOARD"` so the dashboard call works without specifying it
- This is a small schema relaxation, not a behaviour change

---

## Commit Instructions

- One commit per task minimum: `core: add GET /api/v1/anticheat/violations (P14 Task 1)`
- Push to `main` after each commit
- Do NOT touch anything outside `umbrella-core-CURRENT/`
- When all tasks are done, write `dispatches/PHASE14-BACKEND-FIXES/SUBCHAT-HANDBACK.md` with:
  - All commits (SHA + message)
  - Any tasks that couldn't be completed and why
  - Any decisions made the head chat should know about
  - Any existing code patterns you had to deviate from and why

## Verification before handback

- Every new route is mounted in `main.py`
- Every new route has a Pydantic request/response model — no raw dicts
- No existing routes broken
- No new dependencies added without updating `requirements.txt`
