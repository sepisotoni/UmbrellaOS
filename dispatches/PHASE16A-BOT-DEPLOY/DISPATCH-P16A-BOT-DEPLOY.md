# DISPATCH: Phase 16A — Discord Bot into Repo + HeavenCloud Deployment

**Type:** Sub-chat (write access + codespace exec)
**Scope:** Extract bot from archive, add as `umbrella-discord-CURRENT/`, deploy to HeavenCloud
**Write PAT (sepisotoni):** [WRITE_PAT — see head chat]
**Read-only PAT (sepisotoni):** [READ_ONLY_PAT — see head chat]
**Secondary PAT (Sepisoton1):** [SECONDARY_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip at dispatch time:** cbd1b33
**Codespace (secondary account):** `stunning-adventure-6v9694r9rjv4fr4vq` (account: secondary)
**HeavenCloud panel:** https://control.heavencloud.in
**HeavenCloud API key:** [HEAVENCLOUD_API_KEY — see head chat]
**HeavenCloud server identifier:** `671e0e33`
**HeavenCloud SFTP:** `free-bots.heavencloud.in:2022`

---

## Context

The Discord bot exists as a zip on the `archive` branch at:
`other-services/umbrella-discord-PHASE8-COMPLETE.zip`

It is a Python discord.py bot with 11 cogs. It needs to:
1. Be extracted and added to main repo as `umbrella-discord-CURRENT/`
2. Be configured for the live environment
3. Be uploaded to HeavenCloud and started

The bot connects to umbrella-core at `https://umbrellaos-core.onrender.com`.
The HeavenCloud server auto-installs `requirements.txt` and runs `bot.py` on startup.

Commit after every task. Push to main after each commit.

---

## Task 1 — Extract bot from archive branch

From the codespace (account: secondary):

```bash
cd /tmp
# Download the zip from archive branch using read-only PAT
curl -s -H "Authorization: Bearer [READ_ONLY_PAT]" \
  "https://api.github.com/repos/sepisotoni/UmbrellaOS/contents/other-services/umbrella-discord-PHASE8-COMPLETE.zip?ref=archive" | \
  python3 -c "import sys,json,base64; d=json.load(sys.stdin); open('bot.zip','wb').write(base64.b64decode(d['content']))"
unzip -q bot.zip -d umbrella-discord
ls umbrella-discord/
```

Report what files are in the zip so we know the structure.

---

## Task 2 — Review and update bot files

Read the following files from the extracted bot:
- `bot.py` — main entry point
- `requirements.txt` — dependencies
- `config.py` or `.env.example` — what env vars are needed
- `cogs/verification_cog.py` — verify nickname sync is there

Then make these updates:

**`config.py` or wherever env vars are read:**
Ensure the bot reads these env vars:
- `DISCORD_BOT_TOKEN` — the bot token
- `DISCORD_GUILD_ID` — the Discord server ID
- `UMBRELLA_CORE_URL` — set default to `https://umbrellaos-core.onrender.com`
- `UMBRELLA_CORE_API_KEY` — the admin key
- `DISCORD_VERIFIED_ROLE_ID` — role ID to assign on verification (new — add if not present)

**`cogs/verification_cog.py`:**
Check if it assigns the verified role on successful verification. If not, add it:
```python
# After setting nickname:
verified_role = guild.get_role(int(os.getenv("DISCORD_VERIFIED_ROLE_ID", "0")))
if verified_role:
    await member.add_roles(verified_role, reason="Minecraft account verified")
```

**`requirements.txt`:**
Make sure these are present:
- `discord.py>=2.3.0`
- `aiohttp>=3.9.0`
- `python-dotenv>=1.0.0`

---

## Task 3 — Add to repo as umbrella-discord-CURRENT

Clone the repo in the codespace using the write PAT, copy the bot files in, commit and push:

```bash
cd /tmp
git clone https://x-access-token:[WRITE_PAT]@github.com/sepisotoni/UmbrellaOS.git repo
cp -r umbrella-discord/. repo/umbrella-discord-CURRENT/
cd repo
git config user.email "head-chat@umbrellaos"
git config user.name "UmbrellaOS Head Chat"
git add umbrella-discord-CURRENT/
git commit -m "feat: add umbrella-discord-CURRENT — Discord bot Phase 8 + verified role assignment"
git push origin main
```

---

## Task 4 — Upload bot files to HeavenCloud

Use the Pterodactyl file API to upload each bot file to the HeavenCloud server.

First get a file upload URL:
```bash
# List current files on server
curl -s -H "Authorization: Bearer [HEAVENCLOUD_API_KEY]" \
  -H "Accept: application/json" \
  "https://control.heavencloud.in/api/client/servers/671e0e33/files/list?directory=/" 
```

Upload files using the file write API:
```bash
# Upload each file - use the Pterodactyl files/write endpoint
curl -s -X POST \
  -H "Authorization: Bearer [HEAVENCLOUD_API_KEY]" \
  -H "Accept: application/json" \
  -H "Content-Type: application/octet-stream" \
  "https://control.heavencloud.in/api/client/servers/671e0e33/files/write?file=/bot.py" \
  --data-binary @/tmp/umbrella-discord/bot.py
```

Upload all files: `bot.py`, `requirements.txt`, and all files in `cogs/`. Create the `cogs/` directory first if needed:
```bash
curl -s -X POST \
  -H "Authorization: Bearer [HEAVENCLOUD_API_KEY]" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  "https://control.heavencloud.in/api/client/servers/671e0e33/files/create-folder" \
  -d '{"root": "/", "name": "cogs"}'
```

---

## Task 5 — Create .env file on server

The bot needs env vars. Create a `.env` file on the server:

```bash
curl -s -X POST \
  -H "Authorization: Bearer [HEAVENCLOUD_API_KEY]" \
  -H "Accept: application/json" \
  -H "Content-Type: application/octet-stream" \
  "https://control.heavencloud.in/api/client/servers/671e0e33/files/write?file=/.env" \
  --data-binary $'DISCORD_BOT_TOKEN=\nDISCORD_GUILD_ID=\nUMBRELLA_CORE_URL=https://umbrellaos-core.onrender.com\nUMBRELLA_CORE_API_KEY=8c186becf081a4cd4a499ed3099d564f7b81a5d6fcee769c14c0f9c424467731\nDISCORD_VERIFIED_ROLE_ID=\n'
```

Note: `DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID`, and `DISCORD_VERIFIED_ROLE_ID` are left blank — Sepiso needs to fill these in from the HeavenCloud file manager before starting the bot.

---

## Task 6 — Verify upload and report

List the files on the server to confirm everything uploaded:
```bash
curl -s -H "Authorization: Bearer [HEAVENCLOUD_API_KEY]" \
  -H "Accept: application/json" \
  "https://control.heavencloud.in/api/client/servers/671e0e33/files/list?directory=/" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); [print(f['attributes']['name']) for f in d['data']]"
```

DO NOT start the server yet — the `.env` file needs `DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID`, and `DISCORD_VERIFIED_ROLE_ID` filled in by Sepiso first.

---

## Commit Instructions

- `feat: add umbrella-discord-CURRENT — Discord bot Phase 8 + verified role (P16A Task 3)`
- When done write `dispatches/PHASE16A-BOT-DEPLOY/SUBCHAT-HANDBACK.md` with:
  - All files uploaded to HeavenCloud
  - What env vars still need filling in
  - Any issues found in the bot code
  - What Sepiso needs to do before starting the bot
