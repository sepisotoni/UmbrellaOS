# DISPATCH: Discord Bot Audit

**Type:** Sub-chat (read-only — no commits)
**Read-only PAT:** [READ_ONLY_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip:** 2a1ebf9
**Codespace:** `stunning-adventure-6v9694r9rjv4fr4vq` (account: secondary)
**Secondary PAT:** [SECONDARY_PAT — see head chat]
**HeavenCloud API key:** [HEAVENCLOUD_API_KEY — see head chat]
**HeavenCloud server:** `671e0e33`

Read files lazily. No commits. Output findings as a file artifact.

---

## What to read

Read every file in `umbrella-discord-CURRENT/bot/`:
- `bot.py` — startup, cog loading, tree sync
- `config.py` — env var handling
- `webhook_server.py` — bidirectional push listener
- `umbrella_core_client.py` — how it talks to core (PBKDF2 auth)
- Every cog in `cogs/` — what each one actually does

Also check the live bot from the codespace:
```bash
curl -s -H "Authorization: Bearer [HEAVENCLOUD_API_KEY]" \
  "https://control.heavencloud.in/api/client/servers/671e0e33/resources" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); a=d['attributes']; print('state:', a['current_state'], 'memory:', a['resources']['memory_bytes']//1024//1024, 'MB')"
```

---

## What to assess

### 1. Cog completeness
For each of the 11 cogs, answer:
- What does it actually do?
- Does it connect to real core endpoints?
- Are those endpoints real (check `umbrella-core-CURRENT/api/routers/`)?
- Any hardcoded values, fake data, or unimplemented stubs?
- Any obvious bugs?

### 2. Verification flow
- Does `verification_cog.py` handle the full flow: DM → code → confirm → nickname → verified role?
- Does it read message templates from core (`GET /api/v1/settings/{key}`)?
- Does it assign the verified role (`DISCORD_VERIFIED_ROLE_ID`)?
- Any edge cases not handled (already linked, expired code, wrong code)?

### 3. PBKDF2 auth
- Does `umbrella_core_client.py` correctly implement PBKDF2-HMAC?
- Does it send `X-Auth-MAC` + `X-Auth-Timestamp`?
- Does core's `session.py` verify it correctly?

### 4. Bidirectional push
- Does `webhook_server.py` listen on port 3607?
- Does `webhook_cog.py` register with core on startup?
- Does it verify incoming MAC before dispatching events?

### 5. Slash commands
- List every slash command registered across all cogs
- Which ones are actually implemented vs stubbed?
- Is `tree.sync()` using guild scope?

### 6. What's missing or broken
- Features in the Phase 16 spec that aren't implemented
- Cogs that are mostly stubs
- Error handling gaps
- Things that will silently fail

---

## Output

Produce `BOT-AUDIT.md` as a file artifact with all findings. Be specific — name the file, line number, exact issue. No fluff.
