# HEAD CHAT HANDOFF — 2026-08-24

**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip at handoff:** 9e4f06a

---

## Credentials

**GitHub:**
- Write PAT (sepisotoni): `[WRITE_PAT — ask Sepiso]`
- Read-only PAT (sepisotoni): `[READ_ONLY_PAT — ask Sepiso]`
- Secondary PAT (Sepisoton1): `[SECONDARY_PAT — ask Sepiso]`

**Codespace (secondary account — always use `account: secondary`):**
- Name: `stunning-adventure-6v9694r9rjv4fr4vq`
- Repo: sepisotoni/UmbrellaOS
- Java 25 at `/home/codespace/java/jdk-25`

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
- SFTP: `free-bots.heavencloud.in:2022`
- Bot port allocation: 3607

**Discord:**
- Client ID: `1515725320865710110`
- Client secret: `[DISCORD_CLIENT_SECRET — ask Sepiso]`
- Bot token: in HeavenCloud `.env` — do not expose

**Admin key:** `[ADMIN_KEY — ask Sepiso]`

---

## Stack

- **umbrella-core-CURRENT** — FastAPI (Python) on Render Oregon. The only backend. All dashboard and bot calls go through here.
- **umbrella-dashboard-CURRENT** — React + Vite + TypeScript SPA. Deployed on Vercel. `DashboardContext.tsx` for shared state. `src/lib/api.ts` for all API calls.
- **umbrella-discord-CURRENT** — Python discord.py bot. 12 cogs. Hosted on HeavenCloud (Moon-Bot#4491). Uses PBKDF2-HMAC auth (`X-Auth-MAC` + `X-Auth-Timestamp`) to talk to core.
- **minecraft-plugin** — Java 25 Paper plugin. BanEnforcer (fail-closed), GrimBridge, HeartbeatManager, ChatResponderListener, GreeterListener, MessageTemplateManager. Built with Maven.
- **Database** — Supabase Postgres. Alembic migrations tracked (dual heads: `030_add_anticheat_violations_table` + `030_appeal_close_fields` + `031_add_bot_registration`).

**No daemon layer. No Redis. No Neon DB. No RAM pools. Plugin = server agent.**

---

## Working Rules

1. **Sub-chats get dispatches** — write a dispatch doc to `dispatches/PHASE-NAME/DISPATCH.md`, commit it, then give the sub-chat the prompt with secrets inline.
2. **Write PAT in prompts only, never in dispatch docs** — GitHub secret scanning blocks pushes with PATs in files.
3. **Sub-chats commit after every task** — never batch. If token limit hits, work already done is safe.
4. **Head chat verifies before merging** — read the handback, check git log, pull before acting.
5. **Read files lazily** — only read what you need to avoid burning tokens.
6. **AI is on-demand only** — no background AI processing, no auto-flagging. Only runs when staff clicks a button.
7. **Console WebSocket on-demand** — only connects when staff opens the Console page.
8. **Codespace exec always needs `account: secondary`** — primary account codespaces 404 on the MCP.

---

## Phase Status

| Phase | Status |
|---|---|
| 0–13 | ✅ Done (historical) |
| 14 — Dashboard/Core wiring | ✅ Done |
| 15 — Player profiles, GrimAC AI review, Appeals UI | ✅ Done |
| 16A — Discord bot deployed | ✅ Done (Moon-Bot#4491 on HeavenCloud) |
| 16B — PBKDF2 auth + bidirectional push | ✅ Done |
| 16C — AI task model config | ✅ Done |
| 16D — Message templates | ✅ Done |
| 16E — Greeter + chat keyword responder | ✅ Done |
| 16 P0 ports — Toast, PunishModal, BroadcastModal, Sidebar | ✅ Done |
| Bot critical bugfixes (BUG-1, BUG-2, SILENT-2) | ✅ Done |
| Dashboard OAuth + flicker fixes | ✅ Done |
| Dashboard active fixes (session persistence, punishment names) | ✅ Done (tip 9e4f06a) |

---

## Open Items

### High Priority

**1. Bot is offline on HeavenCloud**
Last seen offline during audit. Needs restart. From codespace (account: secondary):
```bash
curl -s -X POST -H "Authorization: Bearer [HEAVENCLOUD_API_KEY — ask Sepiso]" \
  -H "Content-Type: application/json" \
  "https://control.heavencloud.in/api/client/servers/671e0e33/power" \
  -d '{"signal":"restart"}'
```

**2. `/ask` slash command not appearing in Discord**
Bot uses guild-scoped sync but commands not showing. Likely `DISCORD_GUILD_ID` mismatch. Verify the guild ID `1503072397828423700` matches your actual Discord server.

**3. Dashboard Vercel build may still be erroring**
Check `https://umbrella-os-ndilimqeni-6825s-projects.vercel.app` — if still showing old dashboard, check Vercel build logs for TypeScript errors from the new dashboard.

**4. `POST /api/v1/ai/copilot` permission — FIXED**
Plugin key now accepted via `require_admin_key_or_session`. Confirmed fixed in `session.py`.

### Medium Priority

**5. Phase 16F — Knowledge base**
Not started. Bot reads server docs on request, staff manage from dashboard Knowledge page. Spec in `dispatches/PHASE16-SPEC.md`.

**6. Phase 17 — Plugin updates**
- Console streaming on-demand only (currently always-on if connected)
- AI log filtering before sending to AI provider
- Plugin upload from dashboard (marketplace wiring)
- `server_id` in anticheat flags ✅ already done in Phase 15A

**7. Minecraft server version**
Server is on BisectHosting. Plugin compiled for Java 25 / Paper. MC version unclear — "26.2" was mentioned previously but is non-standard. Needs confirming.

**8. GrimAC Maven dependency**
`grimac:2.3.73` not on public Maven. Must be installed locally before `mvn package` works. Phase 13 blocker still open.

### Low Priority

**9. Phase 18 — E2E test**
Full end-to-end test across everything once Phase 17 is done.

**10. `/verify` slash command missing from bot**
No way to initiate verification from Discord side. Users must DM the bot after in-game prompt. Consider adding `/verify` command.

**11. Dashboard login page subtitle**
Says "Minecraft Multi-Node Fleet Operations & Sentinel Security" — this is aspirational Gemini copy, not what UmbrellaOS actually is. Consider updating to something accurate.

---

## Alembic Migration State (live DB)

```
030_add_anticheat_violations_table
030_appeal_close_fields
031_add_bot_registration
```

Both `030` heads are valid Alembic multi-head branching. Tables verified:
- `anticheat_violations` — 8 columns, 4 indexes
- `appeals` — 6 new close/AI-review columns
- `punishments` — `status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'`
- `bot_registration` — id=1 upsert table

---

## Key Architecture Notes

- **No daemon language** anywhere — "Servers Online" not "Daemons Online"
- **PBKDF2 auth** — bot→core uses `X-Auth-MAC` + `X-Auth-Timestamp`, not raw admin key
- **Bidirectional push** — core pushes `staff.escalation.new` events to bot at `http://free-bots.heavencloud.in:3607`. Poll fallback every 5 min.
- **Verified role** — bot assigns `DISCORD_VERIFIED_ROLE_ID` on verification confirm
- **IP blacklist** — `blacklist_ip: bool` on punishment creation. Stored in `IPBlocklist` table. BanEnforcer checks on login (fail-open, unlike bans which are fail-closed).
- **Message templates** — all bot/plugin messages stored in settings table, editable from dashboard. Variables: `$CODE`, `$PLAYER`, `$DISCORD_INVITE`, `$SERVER`, `$EXPIRES`
- **AI on-demand** — staff clicks "AI Review" button. Never runs automatically.
- **Log filtering** — before any AI call: strip chat, heartbeat noise; keep errors, warnings, GrimAC flags. Cap at 200 relevant lines.

---

## Dashboard Notes

- Auth: Discord OAuth → core issues token → stored in `DashboardContext` (in memory, not localStorage). Also supports admin key login.
- `VITE_UMBRELLA_CORE_URL` — only env var needed on Vercel. Set to `https://umbrellaos-core.onrender.com`.
- Ideas docs: `DASHBOARD-IDEAS-FROM-GEMINI.md` and `DASHBOARD-IDEAS-FROM-GEMINI-V2.md` — pixel-perfect UI spec for future improvements.
- P0 components done: Toast (5 types incl. `grim`), PunishModal, BroadcastModal, Sidebar live instances.

---

## Bot `.env` on HeavenCloud (current)

```
DISCORD_BOT_TOKEN=[BOT_TOKEN — in HeavenCloud .env]
DISCORD_GUILD_ID=1503072397828423700
UMBRELLA_CORE_URL=https://umbrellaos-core.onrender.com
UMBRELLA_CORE_API_KEY=[ADMIN_KEY — ask Sepiso]
DISCORD_VERIFIED_ROLE_ID=1540853515201544282
STAFF_ALERT_CHANNEL_ID=1503076452994650323
BOT_CALLBACK_PORT=3607
BOT_CALLBACK_URL=http://free-bots.heavencloud.in:3607
```
