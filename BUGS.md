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


## Core-only follow-up audit — cross-file and unused-feature checks (2026-10-31)

> **Coverage boundary:** Searched the indexed core codebase for unfinished markers, uses of configured fields, and registry/router references; read key service/router/configuration implementations. This is **not** proof that every core file and line has been inspected. Dynamic registration, migrations and external API consumers can make apparently unused symbols genuinely necessary. Do not remove code solely based on text search.

| ID | Priority | Confidence | Location | Evidence and follow-up |
|---|---|---|---|---|
| UOS-CORE-001 | High | Concrete concurrency design risk; reproduction required | `umbrella-core-CURRENT/services/ai_service.py:184–218,366–393` | Both AI moderation and appeal review pass a **single shared SQLAlchemy `AsyncSession`** to several coroutines executed concurrently with `asyncio.gather()`. Concurrent operations on the same `AsyncSession` are unsupported and can produce session-state/connection errors. Execute these queries sequentially on that session or use independent per-task sessions with explicit ownership. Add integration tests on actual production DB engine. |
| UOS-CORE-002 | Medium | Verified configuration mismatch | `umbrella-core-CURRENT/config/settings.py`, `umbrella-core-CURRENT/main.py:224–253` | `cors_origins` is declared with a concrete allowlist, but middleware explicitly uses `allow_origins=["*"]`. The field presently has no runtime effect at this middleware. Either honor it in production or remove/relabel the misleading unused setting and update documentation. Wildcard with `allow_credentials=False` is not itself proof of a CSRF vulnerability. Overlaps UOS-006. |
| UOS-CORE-003 | Medium | Candidate unused setting | `umbrella-core-CURRENT/config/settings.py` (`auto_action_confidence_threshold`) | Indexed repository search found this identifier only at its definition. Nearby comment says the value is intended for later auto-apply execution; classify as **reserved/not implemented**, not active safety protection. Check direct/dynamic settings access before removing or relying on it. |
| UOS-CORE-004 | Medium | Deferred integration | `umbrella-core-CURRENT/services/ai/orchestrator.py:158+`, `registry/adapters/ai.py` | AI tool adapter and action guard are implemented, but orchestrator currently only generates/reviews text. There is no demonstrated autonomous tool-calling loop connected to it. Label this feature **scaffolded, not fully integrated**; ensure future execution passes through guarded `call_tool()`. Do not misclassify adapter code as dead. |
| UOS-CORE-005 | Low | Intentional incomplete cross-service feature | `umbrella-core-CURRENT/capabilities/verification.py`, `api/routers/verification.py` | Nickname synchronization after verification is described as Discord-side responsibility, not implemented inside Core. Core lacks a live Discord gateway; confirm Discord bot handles it. Do **not** implement nickname updates directly in Core as a purported bug fix. |
| UOS-CORE-006 | Low | Ambiguous naming / permission consistency | `umbrella-core-CURRENT/api/routers/verification.py`, `capabilities/verification.py` | Legacy verification endpoints mix `require_admin_key` and `require_plugin_key` while capability wrappers use granular `verification.link.manage/view`. This can be intentional for distinct clients; document an endpoint-to-caller permission matrix and test compatibility before renaming or consolidating. |
| UOS-CORE-007 | Medium | Incomplete cross-file validation | Core models, Pydantic schemas, settings service, API routers, dashboard/Discord/MC clients | No complete AST/reference graph or generated OpenAPI/schema comparison has been run, so variable/type naming consistency **across every script remains unverified**. Run Ruff/Pyright, inspect unreferenced exports, compare response fields with generated SDK and consumers, and check dynamic registry decorators. Mark findings as confirmed only with call-site evidence. |

### Confirmed-versus-candidate distinctions

- **Concrete mismatch:** `cors_origins` configuration does not control the active CORS middleware.
- **Code-level risk:** simultaneous calls on a single async SQLAlchemy session. Reproduce with integration tests before claiming observed production errors.
- **Candidates, not proven dead code:** `auto_action_confidence_threshold`; currently unused in indexed source, but potentially consumed through dynamic settings resolution.
- **Planned feature:** AI tool execution, and bot-side nickname synchronization.
- **Do not delete** registration-only capability handlers, Alembic migration scripts, CLI adapters, or dynamically discovered plugins on the basis of reference-count searches.

### Suggested core test commands (from the core directory)

```sh
python -m compileall -q .
python -m pytest -q
ruff check .
# If configured:
pyright
```

A separate repository-wide symbol/reference and API compatibility pass is still necessary before claiming every script, field name, and feature is audited.
