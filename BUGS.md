# BUGS.md — UmbrellaOS audit backlog

> Initial cross-component static inspection on 2026-10-31. This is **not** a complete file-by-file or runtime audit of this large repository. Items marked "potential" require reproduction; do not treat them as proven exploits. Scope inspected: core startup/auth/WebSocket proxy/AI guard, dashboard API and console, Discord startup, plus code search over major subsystems.

## Prioritized findings

| ID | Severity | Confidence | Location | Finding and next action |
|---|---|---|---|---|
| UOS-001 | High | Likely integration bug | `umbrella-dashboard-CURRENT/src/lib/api.ts` (`getServerConsoleWebSocketUrl`), `umbrella-dashboard-CURRENT/src/components/console/ConsoleView.tsx`, `umbrella-core-CURRENT/api/routers/hosting_console_ws.py` | Dashboard connects to `/ws/console/{id}?source=dashboard&token=...&admin_key=...` but inspected core WebSocket route is `/api/v1/hosting/servers/{id}/console?token=...`. Verify whether another route/proxy rewrite exists; otherwise align the frontend with the actual endpoint, ensure a valid session token, and add end-to-end console connection tests. The UI currently falls back to plugin-log polling. |
| UOS-002 | High | Potential authorization weakness | `umbrella-core-CURRENT/api/routers/hosting_console_ws.py` | WebSocket proxy checks only `hosting.server.view` before establishing bidirectional console access. The code acknowledges no separate permission for console *commands*. If upstream accepts writable console messages, read-only users may send commands. Require `hosting.server.console_write` for client-to-daemon forwarding or enforce read-only mode; test with a view-only account. |
| UOS-003 | High | Startup reliability | `umbrella-core-CURRENT/main.py` (lifespan/migrations) | Alembic migration exceptions are logged as warnings and startup continues with `create_tables()`. This can leave an old/mismatched schema while services run. Prefer failing startup/readiness on required migration failure, with explicit dev-only escape hatch if necessary; test a failed migration. |
| UOS-004 | Medium | Credential exposure risk | `umbrella-dashboard-CURRENT/src/lib/api.ts` | Console WebSocket URL embeds session token and optional admin key in query parameters; URLs may be captured in logs/diagnostics/proxies. Browser WebSockets lack arbitrary header support, but the *long-lived admin key* should not travel in the query. Use a short-lived, narrowly scoped WebSocket ticket; redact query strings from all logs. Verify actual endpoint's expected auth. |
| UOS-005 | Medium | Credential persistence risk | `umbrella-dashboard-CURRENT/src/lib/api.ts` (constructor) | Dashboard loads legacy admin keys from `localStorage`. Any JavaScript running in the origin can read persistent keys after an XSS or third-party script compromise. Remove/expire legacy key persistence when possible, migrate to scoped session credentials, and audit CSP/XSS defenses. This is a threat-model concern, not evidence of exploitation. |
| UOS-006 | Medium | Configuration/defense-in-depth | `umbrella-core-CURRENT/main.py` (CORS) | Wildcard origins are intentionally enabled with `allow_credentials=False`, and bearer tokens are used; this is **not automatically a CSRF vulnerability**. Still consider honoring the configured `cors_origins` allowlist for production to minimize cross-origin access by any site possessing a token. |
| UOS-007 | Low | Future feature/guardrail | `umbrella-core-CURRENT/services/ai/orchestrator.py` | The orchestrator currently generates/reviews text but does not execute capabilities. Its TODO notes future execution must pass through `registry/adapters/ai.py:call_tool()` to enforce the action guard. Keep this as a prerequisite when adding autonomous tool execution; **not a current bypass**. |
| UOS-008 | Medium | Validation coverage | `umbrella-discord-CURRENT/bot/bot.py`, Minecraft Java plugin, core API | End-to-end tests should cover core outage/timeout, Discord permissions and rate limits, duplicate command replay, Minecraft command authentication, reconnection and degraded Redis/DB behavior. Specific defect not yet established in this initial pass. |

## Immediate verification plan

1. Trace frontend console WebSocket path through any reverse proxy to the FastAPI router; run a real-browser connection test.
2. Test read-only roles against console input forwarding and prohibit command sends without explicit permission.
3. Simulate failed Alembic upgrade; assert startup/readiness behavior.
4. Audit all URLs/logs for credentials, replace long-lived WebSocket query keys with scoped tickets.
5. Expand source audit to each Python/TS/Java module and run relevant unit/integration tests.

## Observed safeguards worth preserving

- Core validates default secrets at server startup.
- Core includes auth, rate-limiting, WAF-style middleware, and API tests.
- WebSocket proxy resolves user sessions and verifies permissions before proxying.
- AI capability adapter has a documented action-guard integration path.

**Documentation only:** This backlog does not alter application behavior.
