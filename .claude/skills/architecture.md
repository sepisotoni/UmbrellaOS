# UmbrellaOS Architecture

## Stack
- Core API: FastAPI + PostgreSQL (Render `srv-da3k11f10e5c73eka6o0`)
- Dashboard: React + Vite + Tailwind (Vercel `umbrella-os`, team `team_jxYs3eCsymnBsVpR7sBO1ueu`)
- Bot: discord.py on HeavenCloud (`e3f69e73`), bot name Moon-Bot#4491
- Plugin: Java + Paper 1.21.4 on BisectHosting
- DB: Supabase PostgreSQL (`isofkwkivftnssorqzkd`)
- Dashboard URL: https://umbrella-os-phi.vercel.app

## Auth layers
- Dashboard users: Discord OAuth → session token → `require_permission()`
- Bot → Core: PBKDF2 HMAC (WPA2-style) → `require_admin_hmac_or_session()`
- Plugin → Core: PBKDF2 HMAC → `require_plugin_key()`
- Admin scripts: raw admin key → `require_admin_key()`

## Key rules
- Dashboard endpoints: always `require_permission("subsystem.action")`
- Plugin endpoints: always `require_plugin_key()`
- Bot endpoints: always `require_admin_hmac_or_session()`
- Never use `==` for key comparison — always `hmac.compare_digest()`
- All settings changes must go through `SettingsService.update()` not raw DB

## Subsystem owners (current wave)
- [PLUGIN] — plugin.py, server_control.py, snapshot.py, mc_commands.py, Java plugin
- [DASH] — all dashboard React components
- [CURSOR] — settings.py, knowledge.py, webhooks_rest.py, bridge.py, verification.py
- [BOT] — all bot cogs, umbrella_core_client.py
- [HEAD] — orchestration, coordination, CI, cross-cutting fixes
