# HEAD CHAT HANDOFF — 2026-08-25

**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip at handoff:** 9c8aa26

---

## Credentials

**GitHub:**
- Write PAT (sepisotoni): `[WRITE_PAT — ask Sepiso]`
- Read-only PAT (sepisotoni): `[READ_ONLY_PAT — ask Sepiso]`
- Secondary PAT (Sepisoton1): `[SECONDARY_PAT — ask Sepiso]`

**Codespace (secondary account — always use `account: secondary`):**
- Name: `stunning-adventure-6v9694r9rjv4fr4vq`
- Repo: sepisotoni/UmbrellaOS

**Supabase:**
- Project ID: `isofkwkivftnssorqzkd`
- DB password: `[DB_PASSWORD — ask Sepiso]`
- Direct port: 5432 (NOT 6543)

**Render:**
- Service: `srv-da3k11f10e5c73eka6o0`
- Workspace: `tea-da11bcdbedkc73bqdi80`
- Live core URL: `https://umbrellaos-core.onrender.com`

**Vercel:**
- Token: `[VERCEL_TOKEN — ask Sepiso]` (use from codespace only)
- Team ID: `team_jxYs3eCsymnBsVpR7sBO1ueu`
- Project ID: `prj_LuWG741T5pgWaNRb3smeepRn7Sor`
- Dashboard URL: `https://umbrella-os-ndilimqeni-6825s-projects.vercel.app`

**HeavenCloud (Discord bot hosting):**
- Panel: `https://control.heavencloud.in`
- API key: `[HEAVENCLOUD_API_KEY — ask Sepiso]`
- Server identifier: `671e0e33`
- Bot port allocation: 3607

**Discord:**
- Client ID: `1515725320865710110`
- Client secret: `[DISCORD_CLIENT_SECRET — ask Sepiso]`

**Admin key:** `[ADMIN_KEY — ask Sepiso]`

---

## Stack

- **umbrella-core-CURRENT** — FastAPI (Python) on Render Oregon. Single backend. All dashboard + bot calls go here.
- **umbrella-dashboard-CURRENT** — React + Vite + TypeScript SPA on Vercel. `DashboardContext.tsx` for shared state, `src/lib/api.ts` for all API calls.
- **umbrella-discord-CURRENT** — Python discord.py bot, 13 cogs (added ask_cog + webhook_cog). Hosted on HeavenCloud (Moon-Bot#4491). PBKDF2-HMAC auth to core.
- **minecraft-plugin** — Java 25 Paper plugin. Deployed on BisectHosting.
- **Database** — Supabase Postgres. Alembic migrations in `umbrella-core-CURRENT/alembic/versions/`.

**No daemon layer. No Redis. No Neon DB. Plugin = server agent.**

---

## Working Rules

1. **Sub-chats get dispatch prompts** — write the prompt in full with secrets inline, paste into a new chat.
2. **Write PAT in prompts only, never in committed files** — GitHub secret scanning blocks pushes with PATs.
3. **Sub-chats commit after every 2 tasks** — never batch everything at the end. Token limit = partial work saved.
4. **Head chat verifies before acting** — `git pull`, check log, read handback summary before touching anything.
5. **Read files via bash clone** — clone repo to sandbox, then cat/grep. Never read from codespace files directly.
6. **Codespace exec always needs `account: secondary`** — primary account codespaces 404 on GitHub MCP.
7. **HeavenCloud files upload manually** — not git-deployed. Use Pterodactyl API to write files.
8. **Bot .env has 3 vars only** — `DISCORD_BOT_TOKEN`, `UMBRELLA_CORE_URL`, `UMBRELLA_CORE_API_KEY`. Everything else comes from core's settings API at startup (wired via `RemoteConfig`). ⚠️ This migration is **not yet complete** (see Open Items).

---

## Phase Status

| Phase | Status |
|---|---|
| 0–13 | ✅ Done |
| 14 — Dashboard/Core wiring | ✅ Done |
| 15 — Player profiles, GrimAC AI review, Appeals UI | ✅ Done |
| 16A — Discord bot deployed | ✅ Done |
| 16B — PBKDF2 auth + bidirectional push | ✅ Done |
| 16C — AI task model config | ✅ Done |
| 16D — Message templates | ✅ Done |
| 16E — Greeter + chat keyword responder | ✅ Done |
| Bot role permission system | ✅ Done (commit 142147d) |
| /ask slash command + core auth fix | ✅ Done (commit 333ff9f) |
| Duplicate slash command fix | ✅ Done (commit 7098358) |
| Dashboard — session persistence, search fix, punishment names | ✅ Done |
| Dashboard — no-role full block, access denied strips layout | ✅ Done |
| Dashboard — settings full rebuild (tabbed, real backend, per-key save) | ✅ Done (commit 77eb7b2) |
| Dashboard — staff avatar, appoint modal cleanup, roles.manage perm | ✅ Done (commit f103f55) |
| Dashboard — fleet endpoint fix, Discord page real data | ✅ Done (commit 1439087) |
| Dashboard — AI Tasks field names fixed, confidence badge | ✅ Done (commit a267e7e) |
| Dashboard — staff avatar hardening | ✅ Done (commit 9c8aa26) |
| 16F — Knowledge base | ⏳ Not started |
| 17 — Plugin updates | ⏳ Not started |

---

## Open Items

### High Priority

**1. Bot is offline / crashing on HeavenCloud**
Bot was crashing because `ask_cog.py`, `webhook_cog.py`, and `bot/utils/` (with `checks.py`) are missing from the HeavenCloud server — it only has the old files. The duplicate-command fix and new cogs exist in the repo but haven't been uploaded yet.

Files missing from HeavenCloud `/bot/cogs/`:
- `ask_cog.py`
- `webhook_cog.py`

Directory missing entirely:
- `/bot/utils/__init__.py`
- `/bot/utils/checks.py`

`/bot/bot.py` on HeavenCloud is also the old version (still has `copy_global_to`).

Upload all missing/updated files via Pterodactyl API then restart. Use codespace (account: secondary) to make the curl calls since HeavenCloud isn't in sandbox allowlist.

**2. Bot .env → RemoteConfig migration incomplete**
Decision was made: bot should only have 3 env vars (`DISCORD_BOT_TOKEN`, `UMBRELLA_CORE_URL`, `UMBRELLA_CORE_API_KEY`). Everything else (guild ID, role IDs, callback URL/port, command prefix, staff alert channel) should be fetched from core's settings API at startup via a `RemoteConfig` dataclass.

Work needed:
- Add `discord.*` keys to `DEFAULT_SETTINGS` in `umbrella-core-CURRENT/services/settings_service.py`
- Add `fetch_bot_config()` method to `UmbrellaCoreClient`
- Refactor `bot/config.py` to strip removed fields, add `RemoteConfig` dataclass
- Update `bot/bot.py` to call `fetch_bot_config()` in `setup_hook`, store as `self.remote`
- Update cogs that reference moved settings (`owner_role_id`, `staff_alert_channel_id`, `discord_verified_role_id`, `bot_callback_url`, `bot_callback_port`)
- Seed current values into core's settings DB, then trim HeavenCloud `.env` to 3 vars
- Upload all changed files + missing files to HeavenCloud, restart

Current HeavenCloud `.env` (still has the old vars — not yet trimmed):
```
DISCORD_BOT_TOKEN=[in HeavenCloud]
DISCORD_GUILD_ID=1503072397828423700
UMBRELLA_CORE_URL=https://umbrellaos-core.onrender.com
UMBRELLA_CORE_API_KEY=[ADMIN_KEY]
DISCORD_VERIFIED_ROLE_ID=1540853515201544282
STAFF_ALERT_CHANNEL_ID=1503076452994650323
BOT_CALLBACK_PORT=3607
BOT_CALLBACK_URL=http://free-bots.heavencloud.in:3607
OWNER_ROLE_ID=1503074796702011582
```

Values to seed into DB when doing the migration:
- `discord.guild_id` = `1503072397828423700`
- `discord.staff_alert_channel_id` = `1503076452994650323`
- `discord.verified_role_id` = `1540853515201544282`
- `discord.owner_role_id` = `1503074796702011582`
- `discord.callback_url` = `http://free-bots.heavencloud.in:3607`
- `discord.callback_port` = `3607`
- `discord.command_prefix` = `!`

### Medium Priority

**3. Feature flags 403 — permissions seeded in DB but not in roles_service.py**
`feature_flags.view` and `feature_flags.manage` were added to the live DB via SQL in the last session, but `umbrella-core-CURRENT/services/roles_service.py`'s `DEFAULT_PERMISSIONS` and `DEFAULT_ROLES` don't include them yet. This means a fresh deploy / DB wipe would lose them. Add them to the seed file:
- Add to `DEFAULT_PERMISSIONS`: `("feature_flags.view", "View feature flags")`, `("feature_flags.manage", "Create, update, and delete feature flags")`
- Add `feature_flags.view` + `feature_flags.manage` to `owner` and `admin` roles
- Add `feature_flags.view` to `moderator` role

**4. Phase 16F — Knowledge base**
Not started. Bot reads server docs on request, staff manage from dashboard Knowledge page.

**5. Phase 17 — Plugin updates**
Not started. Console streaming on-demand, AI log filtering, plugin upload from dashboard.

### Low Priority

**6. `/verify` slash command missing from bot**
No way for players to initiate verification from Discord side.

**7. Dashboard login subtitle**
Says "Minecraft Multi-Node Fleet Operations & Sentinel Security" — aspirational copy, not accurate.

**8. Minecraft plugin — GrimAC Maven dependency**
`grimac:2.3.73` not on public Maven. Must be installed locally before `mvn package`. Blocker for plugin rebuilds.

---

## Alembic Migration State (live DB)

Dual heads (valid multi-head Alembic branching):
- `030_add_anticheat_violations_table`
- `030_appeal_close_fields`
- `031_add_bot_registration`

---

## Key Architecture Notes

- **PBKDF2 auth** — bot→core uses `X-Auth-MAC` + `X-Auth-Timestamp`, not raw admin key
- **Bidirectional push** — core pushes `staff.escalation.new` to bot at `http://free-bots.heavencloud.in:3607`. Poll fallback every 5 min.
- **AI on-demand only** — never runs automatically. Staff clicks a button.
- **Settings system** — all configurable values in Supabase `settings` table. Dashboard Settings page fetches/saves via `/api/v1/settings`. Bot should fetch `discord.*` category at startup.
- **Permissions** — resolved fresh from DB per request (request-scoped cache only). Adding a permission to a role in the DB takes effect immediately, no re-login needed.
- **HeavenCloud upload** — Pterodactyl API: `POST https://control.heavencloud.in/api/client/servers/671e0e33/files/write?file=<url-encoded-path>` with `Authorization: Bearer [HEAVENCLOUD_API_KEY]` and body `{"content": "<file contents>"}`. Must exec from codespace since HeavenCloud not in sandbox allowlist.
- **Dashboard fleet** — calls `/api/v1/dashboard/servers` (3-min heartbeat cutoff). NOT `/api/v1/servers`.
- **Message templates** — stored in settings, vars: `$CODE`, `$PLAYER`, `$DISCORD_INVITE`, `$SERVER`, `$EXPIRES`.

---

## Dashboard Tab Status (after last session)

| Tab | Status |
|---|---|
| Overview | ✅ Real data — 3 servers, players, GrimAC flags, pending appeals |
| Fleet/Servers | ✅ Real data from `/api/v1/dashboard/servers` |
| Players | ✅ Real data, search works |
| Moderation | ✅ Punishments show player names |
| Appeals | ✅ 1 pending (HackerX), 1 rejected |
| AI Tasks | ✅ Field names fixed, confidence badge shown |
| Staff | ✅ Discord avatar, no username field, loads for admin+ |
| Feature Flags | ✅ Loads (perms seeded in live DB) |
| Settings | ✅ Tabbed, real backend, per-key save |
| Discord Hub | ✅ Real staff roster + bot config, no mock data |
| Alt Detection | ✅ |
| Verification | ✅ |
| Audit | ✅ |
| Console | ✅ On-demand WebSocket |
| No-role users | ✅ Full-screen block, no layout |
