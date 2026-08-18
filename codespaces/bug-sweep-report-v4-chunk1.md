# UmbrellaOS Bug Sweep Report — Chunk 1
**Generated:** 2026-08-18T15:18:30.660Z
**Default model:** gemini-2.5-flash (auto-upgrades to gemini-3.1-flash / gemini-3.6-flash on 503)
**Scope:** Chunk 1 only
**Raw findings:** 5

---

## ✅ Verified Issues

umbrella-core-CURRENT/api/middleware/audit.py | 79 | high | LOGIC_ERROR | log_action can crash if action string does not match AuditAction enum member, as it directly casts str to AuditAction without validation. | Investigate call sites of `log_action` to understand input sources. Implement validation (e.g., `try-except ValueError` or `AuditAction.__members__.get()`) or ensure upstream inputs are always valid enum members.
umbrella-core-CURRENT/api/middleware/auth.py | 30 | high | AUTH_BYPASS | `require_plugin_key` incorrectly validates `X-Admin-Key` against `settings.secret_key` instead of `settings.admin_key`, potentially allowing unauthorized access if `secret_key` is compromised or different. | Correct the key comparison to use `settings.admin_key`. Ensure `settings.admin_key` is a distinct, strong secret used solely for admin authentication.
umbrella-core-CURRENT/api/middleware/rate_limit.py | 114 | medium | WRONG_LOGIC | Rate limit headers `X-RateLimit-Limit` and `X-RateLimit-Remaining` may reflect only API key limits, not the stricter of IP-based or API key limits, leading to misleading information. | Adjust the logic for calculating and setting rate limit headers to always reflect the most restrictive active limit (e.g., `min(ip_limit, api_key_limit)`).
umbrella-core-CURRENT/api/routers/ai_tasks.py | 210 | high | SECURITY_VULNERABILITY | Manual JSON string construction for `details_json` in audit log is vulnerable to injection and can lead to malformed JSON if `body.action_taken` contains special characters. | Replace manual JSON string construction with a robust JSON serialization library function (e.g., `json.dumps()`) to properly escape user-provided data.
umbrella-core-CURRENT/api/routers/ai_tasks.py | 255 | high | SECURITY_VULNERABILITY | Manual JSON string construction for `details_json` in audit log is vulnerable to injection and can lead to malformed JSON if input contains special characters. | Replace manual JSON string construction with a robust JSON serialization library function (e.g., `json.dumps()`) to properly escape user-provided data.

---

## 📋 Raw Explore Findings

| File | Area | Sev | Type | Description |
|------|------|-----|------|-------------|
| `umbrella-core-CURRENT/api/middleware/audit.py` | 79 | **medium** | LOGIC_ERROR | log_action can crash if action string does not match AuditAction enum member, as it directly casts str to AuditAction without validation. |
| `umbrella-core-CURRENT/api/middleware/auth.py` | 30 | **high** | AUTH_BYPASS | require_plugin_key incorrectly validates X-Admin-Key against settings.secret_key instead of settings.admin_key, potentially allowing unauthorized access if secret_key is compromised or different. |
| `umbrella-core-CURRENT/api/middleware/rate_limit.py` | 114 | **medium** | WRONG_LOGIC | Rate limit headers X-RateLimit-Limit and X-RateLimit-Remaining may reflect only API key limits, not the stricter of IP-based or API key limits. |
| `umbrella-core-CURRENT/api/routers/ai_tasks.py` | 210 | **high** | SECURITY_VULNERABILITY | Manual JSON string construction for details_json in audit log is vulnerable to injection and can lead to malformed JSON if body.action_taken contains special characters. |
| `umbrella-core-CURRENT/api/routers/ai_tasks.py` | 255 | **high** | SECURITY_VULNERABILITY | Manual JSON string construction for details_json in audit log is vulnerable to injection and can lead to malformed JSON |
