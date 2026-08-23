# PHASE 16B SUBCHAT HANDBACK

**Status:** Complete — both tasks committed and pushed to `main`
**Commits:**
- `8fe7074` — feat: PBKDF2-HMAC auth — replace raw admin key on the wire (P16B Task A)
- `92036cf` — feat: bidirectional push — core pushes events to bot webhook (P16B Task B)

---

## Task A — PBKDF2-HMAC Auth ✅

### What was done

**`umbrella-discord-CURRENT/bot/services/umbrella_core_client.py`**
- Added `_make_auth_headers()`: derives PBKDF2-HMAC-SHA256 MAC from shared secret using
  `hashlib.pbkdf2_hmac` (stdlib, no extra dep). Sends `X-Auth-MAC` + `X-Auth-Timestamp`.
- Replaced `{"X-Admin-Key": self._api_key}` with `self._make_auth_headers()` in `invoke()`
  and `list_capabilities()` (both call sites).
- Added `register_bot(callback_url)` method (used by Task B's webhook_cog).

**`umbrella-core-CURRENT/api/middleware/auth.py`**
- Added `require_admin_hmac_or_session()`: reads `X-Auth-MAC` + `X-Auth-Timestamp`,
  rejects if timestamp outside ±30s, re-derives MAC with `hashlib.pbkdf2_hmac`, compares
  with `hmac.compare_digest()`. Falls through to `require_admin_key()` if MAC headers absent.
- `require_admin_key()`, `require_plugin_key()`, `optional_auth()` — **unchanged**.
- `api_key_auth.py` — **untouched**.

`require_admin_hmac_or_session` is wired to:
- `POST /api/v1/bot/register` (new, Task B)
- The capabilities REST adapter (`registry/adapters/rest.py`) already uses
  `require_capability_auth` from `api_key_auth.py` which accepts admin key or session —
  the bot currently uses a database-stored API key through that path. The new HMAC dep
  is available if the route auth is swapped, but the dispatch did not require rewiring
  the capabilities routes (they work via `require_capability_auth` + API key today).

---

## Task B — Bidirectional Push ✅

### Core side

**`umbrella-core-CURRENT/alembic/versions/031_add_bot_registration.py`**
- Migration: creates `bot_registration` table (`id INTEGER PK DEFAULT 1`, `callback_url TEXT`,
  `registered_at TIMESTAMPTZ`). Down revises `030_appeal_close_fields`.

**`umbrella-core-CURRENT/models/bot_registration.py`**
- `BotRegistration` SQLAlchemy model. Added to `models/__init__.py`.

**`umbrella-core-CURRENT/api/routers/bot_registration.py`**
- `POST /api/v1/bot/register` — upserts `id=1` row; calls
  `bot_push_service.invalidate_cache()` after commit; validates URL scheme.
- Auth: `require_admin_hmac_or_session`.
- Mounted in `main.py`.

**`umbrella-core-CURRENT/services/bot_push_service.py`**
- `push_event(event, payload)`: fire-and-forget POST to registered callback URL.
- PBKDF2-HMAC-SHA256 auth headers on every push (core → bot, same scheme reversed).
- 60-second in-memory URL cache (`_get_callback_url()`). `invalidate_cache()` for
  immediate pickup after registration.
- All exceptions caught, logged at WARNING, never re-raised.

**`umbrella-core-CURRENT/services/moderation_intelligence/service.py`**
- `push_event("staff.escalation.new", {...})` called after `create_escalation()` in the
  moderation analysis path. `db.flush()` ensures `escalation.id` is populated before push.

### Bot side

**`umbrella-discord-CURRENT/bot/webhook_server.py`**
- `WebhookServer`: aiohttp app, single `POST /webhook` route.
- PBKDF2 MAC verification: same KDF, same ±30s replay window, `hmac.compare_digest()`.
- `register_handler(event, coro)` for extensible event dispatch.
- `start()` / `stop()` for clean lifecycle management.

**`umbrella-discord-CURRENT/bot/cogs/webhook_cog.py`**
- `cog_load()`: starts `WebhookServer` on `bot_callback_port`, registers
  `staff.escalation.new → _on_escalation`, calls `core.register_bot()` with
  `BOT_CALLBACK_URL/webhook` if set.
- `cog_unload()`: calls `server.stop()`.
- `_on_escalation()`: delegates to `NotificationsCog.handle_escalation_push()` if loaded.
- Failures at any step are logged; bot continues; poll fallback remains active.

**`umbrella-discord-CURRENT/bot/cogs/notifications_cog.py`**
- Added `handle_escalation_push(payload)`: posts embed immediately on push delivery.
  Does NOT call `mark_notified` — the poll's next cycle (≤5 min) handles that.
- Poll loop slowed: `@tasks.loop(seconds=60)` → `@tasks.loop(minutes=5)`.

**`umbrella-discord-CURRENT/bot/config.py`**
- `bot_callback_url: str | None = None` — public HeavenCloud address for push delivery
- `bot_callback_port: int = 8080` — aiohttp listener port

**`umbrella-discord-CURRENT/bot/bot.py`**
- `"bot.cogs.webhook_cog"` added to `EXTENSIONS`.

---

## Checklist

- [x] Task A: `_make_auth_headers()` in `umbrella_core_client.py`
- [x] Task A: `require_admin_hmac_or_session()` in `auth.py`
- [x] Task A: existing `require_admin_key` untouched
- [x] Task B: `bot_registration` migration (`031_add_bot_registration`)
- [x] Task B: `POST /api/v1/bot/register` endpoint live
- [x] Task B: `bot_push_service.py` implemented
- [x] Task B: push wired into `StaffEscalation` creation (moderation path)
- [x] Task B: `webhook_server.py` + `webhook_cog.py` on bot side
- [x] Task B: `BOT_CALLBACK_URL` / `BOT_CALLBACK_PORT` in config
- [x] Task B: poll kept, slowed to 5 min
- [x] Both tasks committed and pushed to `main`

---

## Manual actions required

### 1. HeavenCloud — open port 8080

Server `671e0e33` needs port 8080 open/forwarded so umbrella-core can reach
the bot's webhook endpoint. This sub-chat cannot do this — requires HeavenCloud
panel access.

### 2. Bot deployment — set env vars

Add to the bot's environment (HeavenCloud / wherever it runs):
```
BOT_CALLBACK_URL=http://<heavencloud-server-ip>:8080
BOT_CALLBACK_PORT=8080
```

`BOT_CALLBACK_URL` must be the **public** IP/hostname that umbrella-core (on Render)
can reach. Once set, the bot will self-register with core on next startup.

### 3. Run Alembic migration on core

```
alembic upgrade head
```

This applies `031_add_bot_registration` creating the `bot_registration` table.

### 4. Note on capabilities route auth

The bot currently authenticates to the capabilities endpoints via a database-stored
API key (`X-Api-Key` header, `require_capability_auth` path). That still works.
If you want the capabilities routes to also accept PBKDF2 MAC auth from the bot
(removing the need for the stored API key), swap `require_capability_auth` →
`require_admin_hmac_or_session` in `registry/adapters/rest.py`. Not done here
because the dispatch didn't require it and the existing API-key path works.

---

## Files created / modified

```
umbrella-core-CURRENT/
  api/middleware/auth.py                          modified
  api/routers/bot_registration.py                 NEW
  alembic/versions/031_add_bot_registration.py    NEW
  models/bot_registration.py                      NEW
  models/__init__.py                              modified (BotRegistration import + __all__)
  services/bot_push_service.py                    NEW
  services/moderation_intelligence/service.py     modified (push_event wired in)
  main.py                                         modified (router import + mount)

umbrella-discord-CURRENT/
  bot/services/umbrella_core_client.py            modified
  bot/config.py                                   modified
  bot/bot.py                                      modified
  bot/webhook_server.py                           NEW
  bot/cogs/webhook_cog.py                         NEW
  bot/cogs/notifications_cog.py                   modified
```
