# SUBCHAT HANDBACK: Slash Command Bug Fix

**Status:** Code fixed and pushed. HeavenCloud upload/restart blocked (see below).

---

## What was broken and why

**Root cause: global `tree.sync()` with no guild scope.**

`bot/bot.py` `setup_hook()` called `await self.tree.sync()` unconditionally with no guild argument. Discord requires up to **1 hour** to propagate globally-synced slash commands. Since the bot has `discord_guild_id` available in config (`Settings.discord_guild_id`), it should be syncing to that guild for **instant** registration.

No other issues found:
- All 11 cog files parse without syntax errors
- No command descriptions exceed 100 chars (longest is 98 chars)
- All parameter annotations are correct (`str`, not `Optional[str]`, for required params)
- Cog load errors are already caught and logged via `logger.exception()`

---

## What was fixed

**`umbrella-discord-CURRENT/bot/bot.py` — `setup_hook()`:**

```python
# Before (broken — global sync, up to 1hr delay):
await self.tree.sync()
logger.info("Slash commands synced globally.")

# After (fixed — guild sync when DISCORD_GUILD_ID is set, instant):
if self.settings.discord_guild_id:
    guild = discord.Object(id=self.settings.discord_guild_id)
    self.tree.copy_global_to(guild=guild)
    await self.tree.sync(guild=guild)
    logger.info("Slash commands synced to guild %s (instant registration).", self.settings.discord_guild_id)
else:
    await self.tree.sync()
    logger.info("Slash commands synced globally (up to 1hr propagation — set DISCORD_GUILD_ID for instant registration).")
```

`copy_global_to(guild=guild)` copies the globally-registered command tree to the guild before syncing, so all commands appear instantly. Falls back to global sync if `DISCORD_GUILD_ID` is not set in `.env`.

---

## HeavenCloud upload/restart

**Blocked.** `control.heavencloud.in` is not in the sub-chat network egress allowlist. 

Head chat must:
1. Upload fixed `umbrella-discord-CURRENT/bot/bot.py` to HeavenCloud server `671e0e33` at `/bot/bot.py`
2. Ensure `.env` on the server has `DISCORD_GUILD_ID=<your guild id>` set
3. Restart the server (`POST /api/client/servers/671e0e33/power` with `{"signal":"restart"}`)
4. Check logs for: `Slash commands synced to guild <id> (instant registration).`

---

## Expected slash commands after fix

Once restarted with `DISCORD_GUILD_ID` set, these commands should appear instantly in Discord:

| Command | Cog |
|---|---|
| `/archive_search` | archive_search_cog |
| `/server_list`, `/server_status`, `/server_stats`, `/server_start`, `/server_stop`, `/server_restart`, `/server_kill`, `/server_delete` | hosting_cog |
| `/investigate` | investigation_cog |
| `/knowledge_search` | knowledge_cog |
| `/marketplace_sync` | marketplace_cog |
| `/memory_set`, `/memory_list`, `/memory_cleanup` | memory_cog |
| `/moderation_report` | moderation_report_cog |
| `/ops_assess`, `/ops_ask`, `/ops_postmortem` | operational_intelligence_cog |
| `/player_risk`, `/member_risk` | player_risk_cog |
| `/verify` | verification_cog |
