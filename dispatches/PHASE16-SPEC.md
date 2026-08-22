# PHASE 16 SPEC — Discord Bot, Plugins, Bot Identity

**Status:** Planned — not yet dispatched
**Depends on:** Phase 15 complete, Discord bot deployed (Phase 16A)

---

## Feature 1 — Configurable Message Templates

All bot/plugin messages must be editable from the dashboard Settings page.
No redeployment needed to change wording.

Template variable syntax:
- `$CODE` — verification code
- `$PLAYER` — Minecraft username
- `$DISCORD_INVITE` — configurable Discord invite URL (stored in settings)
- `$SERVER` — server name
- `$EXPIRES` — code expiry time

Keys to store in core settings table (minimum):
- `verification.dm_prompt`
- `verification.success_message`
- `verification.error_already_linked`
- `verification.error_invalid_code`
- `verification.error_expired_code`
- `verification.ingame_prompt`
- `verification.ingame_success`
- `verification.nickname_format` (e.g. `$PLAYER` or `$PLAYER | $SERVER`)
- `discord.invite_url`
- `greeter.first_join_message`
- `greeter.return_join_message` (optional, for returning players)
- `chat_responder.response_style`

Dashboard: Settings page has a "Message Templates" section. Staff edits template strings with variable hints shown inline.
Bot + plugin: read templates via `GET /api/v1/settings/{key}` on startup and on config reload.

---

## Feature 2 — IP Blacklist on Ban

When banning a player, staff can optionally check "Also blacklist player's current IP address" (UI already built by Gemini).

Backend:
- `POST /api/v1/punishments` gains optional `blacklist_ip: bool` field
- If true: pull player's last known IP from connection logs, insert into `IPBlocklist` table (new migration: `ip`, `player_uuid`, `reason`, `created_by`, `created_at`)
- New endpoint: `GET /api/v1/security/ip-blocklist` — list all blocked IPs
- New endpoint: `DELETE /api/v1/security/ip-blocklist/{ip}` — remove an IP

Plugin (BanEnforcer):
- On `PlayerPreLoginEvent`, check IP against blocklist via `GET /api/v1/security/ip-blocklist/check?ip={ip}`
- If blocked: kick with "Your IP address has been blocked from this server"
- Same fail-closed behaviour as ban checks — if core unreachable, deny entry

Dashboard:
- Wire the checkbox in the ban form to `blacklist_ip: true`
- Add IP blocklist management section to Security page

---

## Feature 3 — "View Evidence" Deep Link

When a punishment was issued by GrimAC AutoMod, the "View Evidence" link in the punishment row should deep-link to the player's anticheat tab filtered to flags in the ±10 minute window around the ban time.

Dashboard:
- Punishment row: if `issuer == "GrimAC AutoMod"`, show "View Evidence" link
- Link: `/players/{uuid}?tab=anticheat&from={ban_timestamp - 10min}&to={ban_timestamp + 10min}`
- Player profile anticheat tab: reads `from` and `to` query params to pre-filter the violation timeline

---

## Feature 4 — Discord Bot Handles Appeals

Instead of a web form, the bot DMs the player and walks them through the appeal conversationally.

Flow:
1. Player DMs bot "appeal" or clicks a button in a ban notification DM
2. Bot checks if they have an active punishment via `GET /api/v1/punishments?player_uuid={uuid}&status=ACTIVE`
3. If yes, bot starts the appeal interview:
   - "You were banned on [date] for: [reason]. Would you like to appeal? (yes/no)"
   - "Please explain in your own words why you think this ban should be removed."
   - "Is there anything else you'd like staff to know? (or type 'done' to skip)"
   - "Do you have any evidence to share? (link or type 'none')"
4. Bot compiles the Q&A into a structured appeal and calls `POST /api/v1/appeals` with:
   - `player_uuid`, `punishment_id`, `appeal_text` (formatted Q&A transcript), `evidence_url`
5. Bot DMs player: "Your appeal has been submitted. You'll be notified of the outcome."
6. Dashboard appeal view shows the full Q&A transcript instead of a plain text blob
7. AI review reads the transcript as structured context

---

## Feature 5 — Greeter Plugin (New Player Welcome)

Lightweight cog in the Minecraft plugin (or separate small plugin).

Triggers on `PlayerJoinEvent`:
- Check if first join: `GET /api/v1/players/{uuid}` — if `first_seen` is within last 60 seconds, treat as new player
- Fetch greeting message from `GET /api/v1/settings/greeter.first_join_message`
- Substitute `$PLAYER`, `$SERVER`, `$DISCORD_INVITE` variables
- Send as: title + subtitle on screen (5 second display) AND a chat message
- For returning players (optional): `greeter.return_join_message` sent as chat only

Configurable from dashboard Settings page.

---

## Feature 6 — Chat Keyword/Phrase Responder

Plugin cog that monitors player chat for common questions and responds via AI.

Behaviour:
- On `AsyncPlayerChatEvent`, check message against configured keyword list
- Keyword list fetched from `GET /api/v1/settings/chat_responder.keywords` (JSON array)
- Examples: "how to join", "what's the ip", "how do i rank up", "discord link", "how do i appeal"
- If keyword matched AND confidence above threshold:
  - Send message to `POST /api/v1/ai/copilot` with system context: "You are a helpful assistant for [SERVER_NAME]. Answer the player's question briefly in 1-2 sentences. Use the knowledge base for accurate information."
  - Reply to player in chat (prefix: "[Assistant]") or DM them
  - Log the exchange to audit log
- Per-player cooldown: 60 seconds (configurable)
- Configurable: keyword list, response style, reply method (chat/DM), cooldown, enabled/disabled

Knowledge base (Feature 7 below) provides the AI with server-specific context so answers are accurate.

---

## Feature 7 — Bot Identity + Knowledge Base

The bot has a set of documents it reads on request as context for decisions and responses. Staff manage these from the Knowledge page on the dashboard.

Knowledge document types:
- Server Rules
- Staff Handbook / Punishment Guidelines
- FAQ (common player questions + answers)
- Server Lore / Backstory
- Appeal Guidelines (how staff should evaluate appeals)
- Ban Reason Templates (standard reasons for common offences)

Bot behaviour:
- Before answering a complex staff question, search knowledge base via `knowledge.entry.search`
- Before processing an appeal, fetch "Appeal Guidelines" document
- Chat responder uses FAQ document as primary context
- Staff can ask the bot directly: "@UmbrellaBot what are the rules on hacking?"

Dashboard Knowledge page:
- Create/edit/delete knowledge documents (title, content, type/category)
- Documents stored in core DB (`knowledge` table — may already exist)
- Bot reads via `GET /api/v1/knowledge/{id}` or capability `knowledge.entry.search`

Bot system prompt (configurable from Settings):
- "You are [BOT_NAME], the staff assistant for [SERVER_NAME] Minecraft network."
- "Your role: help staff manage players, review appeals, answer questions."
- "Always check the knowledge base before answering policy questions."
- Full system prompt editable from dashboard so bot personality/role can be adjusted without redeployment

---

## Phase Sequencing

**16A — Discord bot deployed** (prerequisite for everything else in this phase)
- Move `umbrella-discord-CURRENT` from archive zip into main repo
- Add `fly.toml` for Fly.io deployment (256MB RAM free tier)
- Connect to live core API (`UMBRELLA_CORE_URL` + `UMBRELLA_CORE_API_KEY`)
- Verify verification flow works end-to-end

**16B — Message templates** (can run parallel with 16A)
- Backend: settings keys, bulk upsert endpoint
- Dashboard: Message Templates section in Settings

**16C — IP blacklist** (after 16A)
- Backend: migration, punishment flag, check endpoint
- Plugin: BanEnforcer IP check on login

**16D — Appeals via bot** (after 16A + Phase 15 appeals UI)

**16E — Greeter + chat responder plugins** (after 16A)

**16F — Knowledge base** (after 16A, can run parallel with 16D/E)

---

## Notes

- View Evidence deep link (Feature 3) is dashboard-only, no backend work needed, can be done in Phase 14 frontend fixes if there's capacity
- Chat responder uses OpenRouter free tier (Nemotron or similar) — model configurable from Settings
- Greeter and chat responder should be toggleable per-server from the dashboard (not global on/off)
- IP blacklist check adds latency to login — must be async and fail-open (unlike ban check which is fail-closed)
- Bot identity/system prompt should reference the server's knowledge base docs so it's always working from current information
