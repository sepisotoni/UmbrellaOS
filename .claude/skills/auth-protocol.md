# Auth Protocol

## PBKDF2 HMAC (WPA2-style)
Used by both bot and plugin to authenticate to core. NOT a simple API key check.

Plugin/bot sends:
- `X-API-Key: <key>` — the shared secret
- `X-Timestamp: <unix_ms>` — current time
- `X-Signature: <hmac>` — PBKDF2-HMAC-SHA256 of `key:timestamp`

Core verifies:
1. Timestamp within ±30s window
2. HMAC matches using `hmac.compare_digest()` (never `==`)

## Keys
- Admin key: set in Render env as `ADMIN_KEY`
- Plugin key: set in Render env as `PLUGIN_KEY`
- Bot uses admin key

## Common mistakes
- Using `==` instead of `hmac.compare_digest()` → timing attack
- Forgetting to check timestamp window → replay attacks
- Using `require_admin_key` on dashboard endpoints → wrong auth type
