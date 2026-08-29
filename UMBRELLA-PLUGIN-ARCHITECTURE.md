# UmbrellaOS — Plugin & Integration Architecture

This document explains how UmbrellaOS plugins work, how they differ from
scripts, and what each integration type is responsible for. Read this before
building anything new that touches server↔core communication.

---

## The Big Picture

```
Minecraft Server                 UmbrellaOS Core (Render)         Clients
─────────────────                ────────────────────────         ───────
UmbrellaPlugin (Java)   ──────▶  FastAPI + PostgreSQL    ◀──────  Dashboard (Vercel)
  CommandPoller          HTTP     /api/v1/plugin/*               Discord Bot (HC)
  HeartbeatManager       push     /api/v1/mc/*                   AI CLI
  ConsoleStreamManager   pull     /api/v1/ai/*
  ConsoleStreamManager
  GrimBridge
  BanEnforcer
  ChatResponderListener
```

The plugin is the **only thing that talks directly to the Minecraft server**.
Everything else (dashboard, bot, AI) goes through core via HTTP. The plugin
pushes data up to core and polls core for instructions to execute.

---

## What a "Plugin" Is vs a "Script"

### UmbrellaOS Plugin (Java, runs inside the server JVM)

- A Paper/Bukkit plugin loaded by the Minecraft server at startup
- Has direct access to the Bukkit API: players, events, scheduler, commands
- Runs inside the server's thread model — async tasks must use `runTaskAsynchronously`
- Communicates with core over HTTP using `CoreApiClient`
- Is the **only** way to interact with the live game world
- Single JAR deployed to `/plugins/` on the Minecraft server
- Registers event listeners, slash commands, and scheduled tasks in `onEnable()`
- Must clean up (cancel tasks, remove handlers) in `onDisable()`

**Use the plugin when you need to:**
- Listen to game events (player join, chat, death, block place)
- Execute console commands or Bukkit API calls
- Read live server state (TPS, online players, world data)
- Enforce rules in real-time (kick, ban, teleport on login)

### Script (Python/bash, runs outside the server)

- Runs on a separate machine or in a cron job
- Has no access to the live game world
- Talks to core via HTTP (same as dashboard/bot)
- Used for: data imports, bulk operations, scheduled reports, migrations
- Examples: seeding the knowledge base, bulk-importing punishment history,
  running a nightly player activity report

**Use a script when you need to:**
- Process data that doesn't require live server access
- Run a one-off bulk operation
- Automate something that core's API can do without the plugin

---

## Plugin Subsystems

### 1. HeartbeatManager
**What it does:** Sends a heartbeat to core every 30 seconds with live server
stats — TPS, online player count, plugin version, Grim connection status.

**Core endpoint:** `POST /api/v1/plugin/heartbeat`

**Dashboard reads:** Server list, online indicators, TPS display

**Key rule:** One heartbeat row per `server_id` — upserted, never duplicated.
If heartbeat stops, core considers the server offline after the stale threshold.

---

### 2. CommandPoller
**What it does:** Polls core every 5 seconds for queued commands, executes
them on the server console, and posts the result back.

**Core endpoint (poll):** `GET /api/v1/plugin/servers/{server_id}/commands/pending`
**Core endpoint (result):** `POST /api/v1/plugin/servers/{server_id}/commands/{id}/result`

**Who queues commands:**
- Dashboard → `POST /api/v1/mc/command`
- AI CLI → same table, same poller picks them up
- Discord bot → same

**Key rule:** Commands are fire-and-forget from the sender's perspective.
The poller executes them in order. Output comes back via console lines, not
a direct command response. Don't expect synchronous return values.

---

### 3. ConsoleStreamManager
**What it does:** Attaches a `java.util.logging.Handler` to the root logger,
buffers the last 500 console lines in-JVM, and pushes new lines to core
every 5 seconds (delta only — only lines not yet pushed).

**Core endpoint:** `POST /api/v1/plugin/servers/{server_id}/console/lines`
**Dashboard reads:** `GET /api/v1/plugin/servers/{server_id}/console/recent`

**Key rule:** The push is delta-tracked — `totalPushed` vs `totalAppended`.
Only new lines since the last push are sent. Core caps storage at 500 lines
per server and deletes oldest when over the cap.

---

### 4. BanEnforcer
**What it does:** On `AsyncPlayerPreLoginEvent`, checks core for active bans
against the player's UUID and IP. If found, denies login with the ban reason.

**Core endpoint:** `GET /api/v1/plugin/servers/{server_id}/bans/{uuid_or_ip}`

**Key rule:** This is the enforcement point — bans issued via dashboard or
bot are stored in core's DB and enforced here. The plugin doesn't maintain
its own ban list. IP bans check `ban_ip_address`; UUID bans check `player_uuid`.

---

### 5. GrimBridge
**What it does:** Listens to GrimAC anticheat events (if Grim is installed)
and forwards violations to core.

**Core endpoint:** `POST /api/v1/plugin/servers/{server_id}/anticheat/violation`

**Key rule:** Optional — plugin starts without Grim and logs a warning if
it's not present. `grim_connected: true/false` appears in the heartbeat.
Dashboard anticheat tab reads from the `anticheat_violations` table.

---

### 6. ChatResponderListener
**What it does:** Listens to `AsyncChatEvent` (Paper 1.19+). When a player's
message matches configured trigger keywords, sends the message to core's AI
endpoint for a response, then sends the AI reply back to the player in-game.

**Core endpoint:** `POST /api/v1/ai/chat-respond` (or similar)

**Key rule:** Uses `AsyncChatEvent` not the deprecated `AsyncPlayerChatEvent`.
Message text is extracted via `PlainTextComponentSerializer.plainText()
.serialize(event.message())`. Has a per-player cooldown to prevent spam.

---

### 7. PlayerTelemetryListener
**What it does:** Tracks join/leave events and session data, pushes to core.

**Core endpoint:** `POST /api/v1/plugin/players/session`

---

### 8. VerificationCommand
**What it does:** In-game `/verify <code>` command. Player runs it with the
code they got from the Discord bot's `/verify` command. Plugin sends the
code to core, core links the Minecraft UUID to the Discord user ID.

**Core endpoint:** `POST /api/v1/verification/link`

**Key rule:** The code is single-use and expires. Core validates it and
creates the link. No sensitive data stored plugin-side.

---

## Data Flow Patterns

### Push (Plugin → Core)
Plugin sends data to core unprompted on a schedule or event trigger.
Examples: heartbeat, console lines, anticheat violations, player sessions.
These are fire-and-forget — plugin doesn't wait for a meaningful response.

### Poll (Plugin ← Core)
Plugin asks core "do you have anything for me?" on a schedule.
Examples: CommandPoller checking for queued commands.
Response is a list of pending items; plugin processes and acknowledges each.

### Request-Response (Dashboard/Bot → Core → Plugin → Core → Dashboard/Bot)
Dashboard queues a command → plugin polls and executes → console output
comes back via ConsoleStreamManager → dashboard reads recent console lines.
This is **not synchronous** — there's no direct response path from plugin
back to the original caller. The caller must poll for results.

### Event-Driven (Plugin → Core, triggered by game event)
BanEnforcer checking bans on login, ChatResponder reacting to messages.
These are synchronous from the plugin's perspective (they block the event)
but async from core's perspective.

---

## What Goes Where — Decision Table

| I want to... | Use |
|---|---|
| Execute a command on the live server | Queue via `POST /api/v1/mc/command` → CommandPoller executes |
| Read live console output | `GET /api/v1/plugin/servers/{id}/console/recent` |
| Ban/mute/kick a player | Core API → stored in DB → BanEnforcer enforces on next login |
| React to a game event in real-time | Plugin event listener |
| Send a message to a player in-game | Queue `/msg PlayerName text` via mc/command |
| Send a message to Discord | Bot webhook `POST /internal/send-message` |
| Check if a server is online | Heartbeat table — `last_seen` within stale threshold |
| Run AI reasoning about server state | `POST /api/v1/ai/cli/execute` |
| Link Minecraft ↔ Discord accounts | Verification flow — bot gives code, plugin redeems it |
| Store server-specific config | `plugin_kv_entries` table — key-value per server_id |
| Add a new game mechanic | New event listener class in plugin, registered in `onEnable()` |
| Add a new admin action | Core endpoint + dashboard UI + optional bot command |

---

## Authentication

### Plugin → Core
Uses `X-Plugin-Key` header. The key is the `UMBRELLA_CORE_API_KEY` env var
on the bot/plugin side, validated by `require_plugin_key` dependency on core.
This is a shared secret — rotate it by updating the env var on both sides.

### Dashboard → Core
Uses `X-Admin-Key` header (admin key login) or `Authorization: Bearer <token>`
(Discord OAuth session token). Both validated by `require_admin_hmac_or_session`.

### Bot → Core
Same `X-Plugin-Key` as the Minecraft plugin — both are trusted server-side
processes. Bot also uses PBKDF2-derived HMAC for some endpoints.

### Core → Bot (webhook)
Core POSTs to the bot's HTTP webhook server (port configured in `RemoteConfig.callback_port`).
Authenticated via HMAC signature using `UMBRELLA_CORE_API_KEY`.

---

## RemoteConfig — What Stays in .env vs What Comes from DB

### Always in `.env` (3 vars only):
```
DISCORD_BOT_TOKEN       # Discord auth — never in DB
UMBRELLA_CORE_URL       # Where to reach core — needed before DB is accessible
UMBRELLA_CORE_API_KEY   # HMAC secret — never in DB (it's used to auth TO core)
```

### Everything else comes from `RemoteConfig` (fetched from core DB at startup):
```
guild_id                # Discord server ID
staff_role_id           # Role that gets staff access
owner_role_id           # Role that gets owner access
verified_role_id        # Role given after Minecraft verification
staff_alert_channel_id  # Where to post staff alerts
callback_url            # Bot's public webhook URL (for core to call back)
callback_port           # Port the bot's webhook server listens on
```

These live in the `settings` table and are editable from the dashboard
Settings tab. Changing them takes effect on bot restart (or when
`RemoteConfig` is refreshed).

---

## Adding a New Plugin Feature — Checklist

1. **Core first** — add the endpoint(s) the plugin will call. No migration
   needed if using existing tables; add a migration if new columns/tables needed.
2. **Read before writing** — check `models/`, `alembic/versions/` before
   adding anything to the DB layer.
3. **Plugin second** — add the Java class, register it in `onEnable()`,
   cancel/remove it in `onDisable()`. Use `runTaskTimerAsynchronously` for
   polling loops, never block the main thread with HTTP calls.
4. **Dashboard/bot third** — add the UI or bot command to surface the data.
5. **Auth** — plugin endpoints use `require_plugin_key`. Dashboard endpoints
   use `require_admin_hmac_or_session`. Don't mix them.
6. **Test the poll/push cadence** — don't poll faster than every 5 seconds.
   Core is on Render free tier; hammering it will cause rate limiting.

---

## Common Mistakes

| Mistake | Why it breaks | Fix |
|---|---|---|
| Blocking main thread with HTTP | Server freezes, TPS drops to 0 | Always use `runTaskAsynchronously` |
| Using `AsyncPlayerChatEvent` | Deprecated in Paper 1.19+, removed in 1.21 | Use `AsyncChatEvent` + `PlainTextComponentSerializer` |
| Manual JSON string concat | Breaks on special chars, newlines, unicode | Use `JSONObject` / `json.dumps()` / proper escaping |
| Reading `.env` for DB-backed settings | Ignores dashboard changes | Use `self.bot.remote.*` for anything editable in Settings |
| Storing state in-JVM only | Lost on server restart | Push to core DB; read back on startup |
| Expecting sync command response | CommandPoller is async poll-execute-log | Read console lines after a delay instead |
| `credentials: 'include'` in fetch | Blocks `allow_origins: *` CORS | Use `credentials: 'omit'` — auth is header-based |
| `asyncio.run()` inside FastAPI lifespan | Event loop conflict | Use `asyncio.to_thread()` to run sync code |
