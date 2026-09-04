# Plugin-Facing API

## Auth
All plugin endpoints use `require_plugin_key()`. Never session or admin key.

## Existing plugin endpoints
- POST /api/v1/plugin/heartbeat — server health ping
- POST /api/v1/plugin/servers/{id}/console/lines — push console output
- GET  /api/v1/plugin/servers/{id}/console/recent — fetch recent lines
- POST /api/v1/plugin/verify-code — submit verification code
- GET  /api/v1/verification/status/{minecraft_uuid} — check link status
- GET  /api/v1/staff/{id} — check if player is staff (plugin key accepted)
- POST /api/v1/ai/tasks — request async AI analysis
- GET  /api/v1/ai/tasks/{id} — poll for AI result
- GET  /api/v1/knowledge?search={q} — search knowledge base
- GET  /api/v1/punishments?player_uuid={uuid} — active punishments on join

## Plugin extensibility rules
- Any business logic the plugin might trigger → expose via plugin-key endpoint
- Events (punishments, alerts, joins) → go through bridge so plugin can receive
- New endpoints for plugin use → always require_plugin_key, never session

## Skills system (planned)
Plugin will declare capabilities on startup (e.g. anticheat, verification, economy).
Core will use this to filter AI analysis and bot alerts per server.
Not yet implemented — log as future feature when designing new subsystems.
