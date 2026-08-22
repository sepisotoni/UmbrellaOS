# PHASE 16B DISPATCH — Auth Hardening + Bidirectional Push

**Status:** Ready to implement
**Depends on:** Phase 16A complete ✅ (bot live at Moon-Bot#4491)
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Branch:** work off `main`, commit directly

---

## Overview

Two tasks, implement in order (A before B — B adds the HTTP listener that A's
push calls need to exist):

| Task | Description | Touches |
|------|-------------|---------|
| A | PBKDF2-HMAC auth — replace raw key on the wire | `umbrella-core-CURRENT/` + `umbrella-discord-CURRENT/` |
| B | Bidirectional push — Core pushes events to bot | `umbrella-core-CURRENT/` + `umbrella-discord-CURRENT/` |

---

## TASK A — PBKDF2-HMAC Auth

### What exists now

`umbrella_core_client.py` sends:
```python
headers = {"X-Admin-Key": self._api_key}
```

`umbrella-core-CURRENT/api/middleware/auth.py` accepts it with:
```python
if x_admin_key and x_admin_key == settings.admin_key:
    return x_admin_key
```

Raw key travels over the wire. Replace with PBKDF2-derived request MAC.

### Design

**Both sides share the same secret** (`UMBRELLA_CORE_API_KEY` / `settings.admin_key`).
Neither side sends it — each derives a MAC from it and compares.

**Request MAC construction** (bot side, per request):
```
timestamp = int(time.time())          # Unix seconds UTC
salt      = f"{timestamp}"            # timestamp as UTF-8 string used as salt
mac       = PBKDF2-HMAC-SHA256(
                password = shared_secret.encode(),
                salt     = salt.encode(),
                iterations = 100_000,
                dklen    = 32
            ).hex()
```

**Headers sent** (replace `X-Admin-Key`):
```
X-Auth-MAC:       <mac hex>
X-Auth-Timestamp: <timestamp int>
```

**Core verification** (per request):
1. Read `X-Auth-Timestamp`. Reject if `|now - timestamp| > 30` seconds (replay window).
2. Derive MAC with the same KDF using `settings.admin_key` as password and `str(timestamp)` as salt.
3. Compare with `hmac.compare_digest()`. Reject if mismatch.

`cryptography==50.0.0` is already in core's requirements. Use:
```python
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
```

`hashlib.pbkdf2_hmac` is fine on the bot side (stdlib, no extra dep).

### Files to change

#### `umbrella-discord-CURRENT/bot/services/umbrella_core_client.py`

Add a `_make_auth_headers()` method:
```python
import hashlib, time

def _make_auth_headers(self) -> dict[str, str]:
    ts = int(time.time())
    mac = hashlib.pbkdf2_hmac(
        "sha256",
        self._api_key.encode(),
        str(ts).encode(),
        100_000,
        dklen=32,
    ).hex()
    return {"X-Auth-MAC": mac, "X-Auth-Timestamp": str(ts)}
```

Replace every `{"X-Admin-Key": self._api_key}` with `self._make_auth_headers()`.
That is two places: `invoke()` and `list_capabilities()`.

#### `umbrella-core-CURRENT/api/middleware/auth.py`

Add a new dependency `require_admin_hmac_or_session()` alongside the existing ones:

```python
import hashlib, hmac, time
from fastapi import Header

async def require_admin_hmac_or_session(
    x_auth_mac: str | None = Header(default=None),
    x_auth_timestamp: str | None = Header(default=None),
    x_admin_key: str | None = Security(admin_key_header),
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> str:
    if x_auth_mac and x_auth_timestamp:
        try:
            ts = int(x_auth_timestamp)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid timestamp")
        if abs(time.time() - ts) > 30:
            raise HTTPException(status_code=401, detail="Timestamp out of window")
        expected = hashlib.pbkdf2_hmac(
            "sha256",
            settings.admin_key.encode(),
            str(ts).encode(),
            100_000,
            dklen=32,
        ).hex()
        if not hmac.compare_digest(expected, x_auth_mac):
            raise HTTPException(status_code=401, detail="Invalid MAC")
        return "hmac"
    # fall through to existing key/session logic
    return await require_admin_key(x_admin_key, authorization, db)
```

**Do NOT remove `require_admin_key`** — the dashboard and other callers still use
it. Only the bot-facing path uses the new MAC auth. The capability registry
middleware (`api_key_auth.py`) is separate — leave it as-is, it handles
database-stored API keys for external integrations.

Wire `require_admin_hmac_or_session` into whichever routes the bot actually calls
(capability invoke + list). Check `umbrella-core-CURRENT/api/routes/` for the
capabilities router and swap its dependency.

### env / config changes

None — both sides already have the shared secret. No new env vars needed.

---

## TASK B — Bidirectional Push (Core → Bot)

### What exists now

`notifications_cog.py` polls `moderation_intelligence.escalation.list` every 60 seconds.
It works but is slow (up to 60s delay) and wastes a round-trip when nothing changed.

### Design

**Bot side — aiohttp HTTP listener**

On startup, the bot brings up a small aiohttp server (aiohttp>=3.9.0 is already
in requirements.txt) on a configurable port (`BOT_CALLBACK_PORT`, default `8080`).

Single endpoint:
```
POST /webhook
Headers: X-Auth-MAC, X-Auth-Timestamp  (same PBKDF2 scheme from Task A — core authenticates to bot with the shared secret)
Body: { "event": "<event_type>", "payload": { ... } }
```

The listener verifies the MAC before processing (same 30-second window, same KDF).
On valid event, it dispatches to the appropriate cog handler.

**Bot registration — Core side**

New Core endpoint:
```
POST /api/v1/bot/register
Auth: require_admin_hmac_or_session (from Task A)
Body: { "callback_url": "http://<bot-ip>:<port>/webhook" }
```

Core stores the URL in a new `bot_registration` table (single row, upsert):
```sql
CREATE TABLE IF NOT EXISTS bot_registration (
    id         INTEGER PRIMARY KEY DEFAULT 1,
    callback_url TEXT NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Use Alembic migration for this — name it `add_bot_registration`.

**Bot startup flow:**
1. Bot starts, aiohttp listener comes up on `BOT_CALLBACK_PORT`.
2. Bot calls `POST /api/v1/bot/register` with its own `BOT_CALLBACK_URL`
   (new env var — set to the public HeavenCloud address, e.g. `http://<ip>:8080`).
3. Core stores it. Subsequent restarts overwrite (upsert on `id=1`).

**Core push — which events**

Replace polling with push for these (at minimum):

| Event type | When Core fires it | Target cog |
|---|---|---|
| `staff.escalation.new` | New `StaffEscalation` row created | `NotificationsCog` |
| `punishment.issued` | `POST /api/v1/punishments` succeeds | new `PunishmentsCog` handler |
| `player.verification.complete` | Player successfully verifies | `VerificationCog` |

Start with `staff.escalation.new` since it directly replaces the existing poll.
The others can be added without further architecture decisions.

**Core push implementation**

Add `bot_push_service.py` in `umbrella-core-CURRENT/services/`:

```python
# services/bot_push_service.py
import hashlib, hmac, time
import httpx
from config import get_settings

settings = get_settings()

async def push_event(event: str, payload: dict) -> None:
    """Fire-and-forget push to the bot's webhook. Logs on failure, never raises."""
    url = await _get_callback_url()
    if not url:
        return
    ts = int(time.time())
    mac = hashlib.pbkdf2_hmac(
        "sha256", settings.admin_key.encode(), str(ts).encode(), 100_000, dklen=32
    ).hex()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                url,
                json={"event": event, "payload": payload},
                headers={"X-Auth-MAC": mac, "X-Auth-Timestamp": str(ts)},
            )
    except Exception:
        import logging
        logging.getLogger(__name__).warning("Bot push failed for event %s", event)
```

`_get_callback_url()` does a DB lookup for the `bot_registration` row.
Cache it in memory with a short TTL (60s) so every event push doesn't hit the DB.

**Wire push into existing services** — find where `StaffEscalation` rows are
created (grep for `StaffEscalation(` in `services/moderation_intelligence/`).
After the DB insert, call `await bot_push_service.push_event("staff.escalation.new", {...})`.

**Keep the poll as a fallback**

Don't delete `notifications_cog.py`'s poll loop. Change it:
- Poll every **5 minutes** instead of 60 seconds (the push handles real-time)
- It catches any pushes that failed (bot was restarting, HeavenCloud hiccup, etc.)
- This makes the system eventually consistent even under failures

**New bot files to create:**

```
umbrella-discord-CURRENT/
  bot/
    webhook_server.py       ← aiohttp app, MAC verification, event dispatch
    cogs/
      webhook_cog.py        ← loads webhook_server, integrates with bot lifecycle
```

**Config additions** (`bot/config.py`):
```python
bot_callback_url: str | None = None       # e.g. http://5.x.x.x:8080 — set on HeavenCloud
bot_callback_port: int = 8080
```

**HeavenCloud:** port 8080 needs to be open/forwarded. Note this in the handback — the sub-chat cannot do this, it needs manual action.

---

## Commit structure

Commit A and B separately with clear messages:
```
feat: PBKDF2-HMAC auth — replace raw admin key on the wire (P16B Task A)
feat: bidirectional push — core pushes events to bot webhook (P16B Task B)
```

Then a handback doc at:
```
dispatches/PHASE16B-AUTH-PUSH/SUBCHAT-HANDBACK.md
```

---

## Handback checklist

- [ ] Task A: `_make_auth_headers()` implemented in `umbrella_core_client.py`
- [ ] Task A: `require_admin_hmac_or_session()` in `auth.py`, wired to capabilities routes
- [ ] Task A: existing `require_admin_key` untouched (dashboard still works)
- [ ] Task B: `bot_registration` migration applied (`add_bot_registration`)
- [ ] Task B: `POST /api/v1/bot/register` endpoint live
- [ ] Task B: `bot_push_service.py` implemented in core
- [ ] Task B: push wired into StaffEscalation creation (at minimum)
- [ ] Task B: `webhook_server.py` + `webhook_cog.py` on bot side
- [ ] Task B: `BOT_CALLBACK_URL` / `BOT_CALLBACK_PORT` in config
- [ ] Task B: poll loop kept but slowed to 5 min
- [ ] Both tasks committed and pushed to `main`
- [ ] **Manual action required:** open port 8080 on HeavenCloud server `671e0e33`
- [ ] Handback doc committed to `dispatches/PHASE16B-AUTH-PUSH/SUBCHAT-HANDBACK.md`

---

## What NOT to touch

- Do not touch `api_key_auth.py` — that's for database-stored API keys (external integrations), not the bot's admin-key path
- Do not change the dashboard's auth flow — it uses `require_admin_key` / session tokens, both stay
- Do not delete the 60-second poll immediately — slow it, keep it as fallback
- Do not add new env vars beyond `BOT_CALLBACK_URL` and `BOT_CALLBACK_PORT`
