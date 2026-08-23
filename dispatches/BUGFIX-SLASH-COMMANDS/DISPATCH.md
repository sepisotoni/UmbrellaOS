# DISPATCH: Slash Command Bug Fix + Audit

**Type:** Sub-chat (write access + codespace exec)
**Scope:** `umbrella-discord-CURRENT/` only
**Write PAT:** [WRITE_PAT — see head chat]
**Secondary PAT:** [SECONDARY_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Codespace:** `stunning-adventure-6v9694r9rjv4fr4vq` (account: secondary — always)
**HeavenCloud API key:** [HEAVENCLOUD_API_KEY — see head chat]
**HeavenCloud server:** `671e0e33`
**Tip:** 11118fa

---

## Context

The Discord bot (Moon-Bot#4491) is live on HeavenCloud but `/ask` and other slash commands are broken. Bot is at `umbrella-discord-CURRENT/`.

Read files lazily — only what you need. Commit after every fix. Keep token usage lean.

---

## Task 1 — Audit slash commands

Read only these files to understand the command structure:
- `umbrella-discord-CURRENT/bot/bot.py` — how cogs are loaded, how tree.sync() is called
- `umbrella-discord-CURRENT/bot/cogs/knowledge_cog.py` — where /ask lives

Check:
- Is `tree.sync()` called with a guild? If not, global commands take up to 1hr to register
- Does `/ask` have correct parameter types?
- Any description over 100 chars? (Discord hard limit — caused a bug in 16A)
- Are all cogs actually loaded without errors?

From the codespace, check the live bot logs:
```bash
curl -s -H "Authorization: Bearer [HEAVENCLOUD_API_KEY]" \
  -H "Accept: application/json" \
  "https://control.heavencloud.in/api/client/servers/671e0e33/logs" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['attributes']['data'][-3000:])"
```

Report exactly what errors appear.

---

## Task 2 — Fix all broken commands

Based on what the audit finds, fix the issues. Common causes:
- `tree.sync()` missing guild scope — add `guild=discord.Object(id=GUILD_ID)` for instant registration
- Description >100 chars — truncate to 99
- Parameter annotation wrong — use `str` not `Optional[str]` for required params
- Cog failing to load silently — add explicit error logging in `bot.py` load loop

Fix whatever is broken. Keep changes minimal and targeted.

---

## Task 3 — Upload fixes and restart

Upload only the changed files to HeavenCloud:
```bash
curl -s -X POST \
  -H "Authorization: Bearer [HEAVENCLOUD_API_KEY]" \
  -H "Content-Type: application/octet-stream" \
  "https://control.heavencloud.in/api/client/servers/671e0e33/files/write?file=/bot/bot.py" \
  --data-binary @/path/to/fixed/bot.py
```

Then restart:
```bash
curl -s -X POST \
  -H "Authorization: Bearer [HEAVENCLOUD_API_KEY]" \
  -H "Accept: application/json" \
  "https://control.heavencloud.in/api/client/servers/671e0e33/power" \
  -d '{"signal":"restart"}'
```

Wait 15 seconds then check logs again to confirm clean startup.

---

## Task 4 — Commit fixes

Commit only the changed files to the repo:
```bash
git add umbrella-discord-CURRENT/
git commit -m "fix: slash command registration + broken command fixes"
git push origin main
```

---

## Handback

Write `dispatches/BUGFIX-SLASH-COMMANDS/SUBCHAT-HANDBACK.md` with:
- What was broken and why
- What was fixed
- Confirmation bot restarted clean
- List of working slash commands after fix
