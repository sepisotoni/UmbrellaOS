# DISPATCH: Bugfix — Plugin API Key needs operational_intelligence.view permission

**Type:** Sub-chat (write access)
**Scope:** `umbrella-core-CURRENT/` only
**Write PAT:** [WRITE_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip:** 19a0b66

Small focused fix — read lazily, one commit, done.

---

## Context

`POST /api/v1/ai/copilot` requires `operational_intelligence.view` permission.
The Minecraft plugin uses a plugin API key to call this endpoint for the chat responder feature.
The plugin key doesn't have this permission mapped, so the call silently fails.

---

## Task

Read these files first:
- `umbrella-core-CURRENT/api/dependencies/` — find how plugin key permissions are checked
- `umbrella-core-CURRENT/api/routers/ai_tasks.py` — find how `operational_intelligence.view` is required on the copilot endpoint

Find where plugin key permission scopes are defined or checked. Add `operational_intelligence.view` to the plugin key's allowed permissions.

This might be:
- A hardcoded list of permissions granted to plugin keys
- A DB seeded default for plugin key capability scopes
- A capability check in the router that needs a plugin-key exemption

Fix whichever applies. Keep the change minimal and targeted.

---

## Commit

`core: grant plugin key operational_intelligence.view for copilot endpoint`

Then write `dispatches/BUGFIX-PLUGIN-PERMISSION/SUBCHAT-HANDBACK.md` and push.
