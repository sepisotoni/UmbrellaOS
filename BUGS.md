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


## Core request-to-output tracing — route-order pass 1 (2026-10-31)

**Method:** Followed the actual `main.py` router registration order, inspecting health, metrics, settings, roles, players, punishments, appeals, Minecraft commands, and feature flags. Checked Minecraft command polling against the Java plugin. Other routes remain for later review; this is **not yet exhaustive**.

| ID | Severity | Confidence | Request → output chain | Finding / test |
|---|---|---|---|---|
| UOS-CORE-008 | High | Authorization design risk; test needed | `POST /api/v1/mc/command` → `require_admin_hmac_or_session` → `MCCommand` DB row → plugin polls → Bukkit console executes | Enqueue accepts the admin/HMAC/session authentication dependency, but the route itself has no explicit command-specific permission such as `mc.command.execute`. Verify session authorization inside the dependency and test low-permission authenticated users; require explicit command execution authorization and audit true actor identity. |
| UOS-CORE-009 | High | Cross-server authorization risk | `GET /api/v1/mc/commands/pending?server_id=...` and `POST /commands/{id}/complete` → `require_plugin_key` → commands DB | Server-specific queue selection uses a caller-supplied `server_id`, and completion looks up by numeric command ID alone. The auth dependency appears to validate a global plugin credential, not an identity bound to one server. A compromised plugin with this credential may retrieve or acknowledge another server's commands. Bind token identity to server, scope completion by server, and test cross-server isolation. |
| UOS-CORE-010 | Medium | Concrete behavior / monitoring issue | `GET /health` → DB/Redis ping → response | Health endpoint intentionally returns HTTP **200** even when body says `status: degraded`. HTTP-only load balancers and uptime checks may classify an unusable instance as healthy. Consider separate `/live` (200) and `/ready` (503 if dependencies unavailable) and test both. |
| UOS-CORE-011 | Medium | Cross-table consistency risk | `PATCH /api/v1/settings/{key}` → `SettingsService.update` commits → `sync_task_model_setting` commits | AI task settings and corresponding `ai_model_configs` can diverge if second write fails. The source code explicitly documents this trade-off, but it may leave the old model active while UI displays the new setting. Consider one transaction or a visible explicit `sync_pending/sync_failed` response and reconciliation. |
| UOS-CORE-012 | Low | Verified routing contract | `GET /api/v1/mc/commands/pending` → `server_id` filter → `minecraft-plugin/.../CommandPoller.java` | Java caller correctly appends `server_id` when configured; default queue compatibility is intentional. **Not a dead setting.** Check deployment config to ensure each server sets a unique ID; avoid deleting fallback without migration. |

### Naming and response-contract checks

- `MCCommandRequest.server_id`, `MCCommandResponse.server_id`, `CommandPoller.serverId` and the serialized `server_id` query are **consistent** across inspected producer/consumer paths.
- `MCCommandCompleteRequest.output/success` matches the plugin acknowledgment shape at a conceptual level; integration test remains recommended.
- `SettingsService.update` and `sync_task_model_setting` have intentionally separate commits, which is a **state-consistency issue**, not a misspelled symbol.
- Do not remove role, router, registry, or schema classes only because they lack direct import references; they may be used through FastAPI dependency injection, decorators, generated API clients, or plugin calls.

### Remaining route-order audit queue

Logs, security, audit, plugins, moderation, auth, Discord bridge, verification, alternate detection, analytics, replay, snapshots, AI tasks/copilot, translations, anti-cheat, server control, staff, registry, webhook, hosting, bot registration, and knowledge modules all require further end-to-end coverage.

**No application behavior was changed.**


## Core request-to-output tracing — route-order pass 2 (2026-10-31)

> Inspected routers for logs, security, audit, plugins, moderation, bridge, anti-cheat, server control, webhooks and knowledge, plus database session dependency and server control implementation. Findings below are source-grounded, but **not runtime-tested**.

| ID | Severity | Confidence | Chain and finding |
|---|---|---|---|
| UOS-CORE-013 | High | **Confirmed implementation/documentation mismatch** | `POST /api/v1/server/control` → `api/routers/server_control.py` claims power/restart route through the Minecraft plugin command queue → `services/server_control_service.py: _run_configured_command` actually invokes **local host processes** with `asyncio.create_subprocess_exec` based on `server.control.*_cmd` settings. On a remote host this may do nothing useful or invoke an unintended local command; on a privileged host it expands the execution surface. Decide whether to implement the claimed plugin queue or explicitly document and restrict local command execution. Test all actions against the actual hosting architecture. |
| UOS-CORE-014 | High | **Confirmed unconsumed queue in implementation comments; verify via repo-wide search** | `POST /api/v1/plugin/control` → creates `PluginCommand` pending row → returns 202 with an explicit note that no worker consumes it. This endpoint is currently **not functional as a control mechanism**; do not advertise as working or silently remove until its consumer is designed. |
| UOS-CORE-015 | Medium | Potential cross-origin / trust boundary | `POST /api/v1/bridge/message` accepts `source` in `minecraft/discord/DASHBOARD`, authenticated by `require_admin_key`; values are client-provided and the resulting actor identity is not separately cryptographically bound to that source. Review whether all callers legitimately have full admin key, and whether unauthorized source impersonation is possible inside that trusted caller population. **Not a demonstrated exploit.** |
| UOS-CORE-016 | Medium | Semantic delivery gap | Bridge message route computes `forwarded=True` and targets, commits to DB, then for DASHBOARD→Discord invokes push-event. The response's `forwarded` represents intent/routing rather than confirmed downstream delivery. Consider `queued` or `dispatch_attempted` vs `delivered` and add retry/ack visibility, especially for Discord and Minecraft targets. |
| UOS-CORE-017 | Low | Verified non-issue | `database/engine.py:get_db` commits the session after the endpoint returns. Therefore `db.flush()` without an explicit `db.commit()` in plugin/knowledge routers is **not by itself** an uncommitted-write bug. Preserve this transaction design when auditing other handlers. |
| UOS-CORE-018 | Medium | Testing scope | Webhook test path calls `WebhookDeliveryService.deliver`; verify outbound URL validation, redirects, DNS rebinding resistance and timeouts at the delivery service rather than assuming SSRF merely because webhooks accept URLs. This is a **test requirement**, not a confirmed SSRF finding. |

### Feature chain status

- **Known nonfunctional:** `PluginCommand` queue has a producer without an implemented consumer.
- **Confirmed cross-file mismatch:** power/restart path documented as remote plugin commands but implemented as local subprocess execution.
- **Intent vs outcome:** bridge routing response does not guarantee Discord/Minecraft delivery.
- **Verified persistence mechanism:** shared `get_db` dependency commits a successful request automatically.
- **Remaining:** inspect the services called by other routers, verify generated schemas and downstream consumers, test authentication boundaries and error cases.

No application source code changed.


## Core request-to-output tracing — route-order pass 3 (2026-10-31)

Reviewed route declarations and permission dependencies for alt detection, analytics, replay, snapshot, AI tasks/copilot, translation, AI config, dashboard, staff and bot registration. Inspected representative implementations and request/response contracts. **This is a route-level pass, not an exhaustive inspection of every downstream service.**

| ID | Priority | Confidence | Trace and finding |
|---|---|---|---|
| UOS-CORE-019 | Medium | Confirmed actor attribution risk | `POST /api/v1/ai/tasks/{task_id}/approve` / `deny` → `require_permission("punishments.create")` → `ApproveTaskRequest.reviewed_by` / `DenyTaskRequest.reviewed_by` → `AITask.reviewed_by` and `AuditLog.actor`. The audit actor is supplied by the request body rather than derived from the authenticated user. A permitted reviewer can claim another reviewer identity. Resolve actor from auth dependency and treat client-provided labels as non-authoritative. |
| UOS-CORE-020 | Medium | Confirmed actor attribution risk | `POST /api/v1/alt-detection/false-positive` (verify router prefix) → `require_permission("players.manage")` → `FalsePositiveRequest.reviewed_by` → `SuspicionEvent.reviewed_by`. Similarly trusts a caller-provided reviewer label. Derive from authenticated principal for reliable audit trails. |
| UOS-CORE-021 | Medium | Possible reporting/data-integrity flaw | `POST /api/v1/snapshot` → `create_snapshot()` → `_parse_json_field`. Invalid serialized inventory/armor/offhand JSON logs a warning and stores null while returning HTTP 201. Code documents intentional partial success; response should explicitly surface partial-data warnings so forensic consumers do not mistake missing evidence for absent inventory. |
| UOS-CORE-022 | Low | Contract validation candidate | `POST /api/v1/replay/sessions/{replay_id}/events` → event normalization. `data` or `event_data` dicts are converted to serialized `event_data_json`; if `event_data_json` already exists, its format is not normalized here. Confirm the service validates the payload shape and add malformed-string tests rather than assuming a syntax bug. |
| UOS-CORE-023 | Low | Verified feature wiring | `api/routers/ai_copilot.py` resolves `CallContext` from the authenticated actor, including the `/commands` fast path. The feature is **not** dead or inherently unauthenticated; test actual tool-permission enforcement when expanded. |
| UOS-CORE-024 | Low | Coverage pending | API schemas, `umbrella-sdk-ts` generated contracts, Discord/Minecraft callers | Verify reviewed field names (`reviewed_by`, `event_data_json`, `server_id`, `minecraft_uuid`) against all real consumers and generated OpenAPI. No complete automated cross-language contract comparison was performed. |

No application source code was changed.


## Core service/capability chain — pass 4 (2026-10-31)

Reviewed `registry/registry.py`, `registry/context.py`, `registry/adapters/rest.py`, `services/ai_config_service.py`, `services/settings_service.py`, `services/verification/service.py`, and the surrounding API route interfaces. No full dynamic-call graph or runtime tests yet.

| ID | Priority | Confidence | Request-to-output finding |
|---|---|---|---|
| UOS-CORE-025 | High | **Confirmed transaction-handling bug in source** | AI config approval → `services/ai_config_service.py:apply_config_action()` → multiple `SettingsService.set_value()` calls (`db.flush()` each) → on any exception the catch branch sets `action.status='rejected'` and calls `db.commit()` **without rolling back previously applied changes**. A failure after some successful upserts can persist partial configuration changes while reporting the whole action as rejected; certain database errors may also leave the session in failed state so commit itself errors. Wrap application in a transactional savepoint / atomic operation and rollback before recording rejection using a fresh clean transaction. Add fault-injection test failing after the first settings mutation. |
| UOS-CORE-026 | Medium | Security-review target | Capability invocation → `registry.call()` → audit event stores `params.model_dump(mode='json')` on success and error. Check all registered capability parameter schemas for credentials/tokens/passwords or private values: their raw values may be copied to audit records. Redact sensitive params centrally before logging. **Exposure not proven without schema inventory**. |
| UOS-CORE-027 | Low | Verified architecture | `registry/adapters/rest.py` → `CallContext.from_web_auth/from_discord_user` → `registry.call()` → capability decorator handlers. Direct source references are intentionally sparse because decorated capabilities register at import time. Do not classify handlers as unused based only on import count; verify registration imports in startup and compare list of registered names against API clients. |
| UOS-CORE-028 | Low | Naming consistency | AI config proposal `action_type` switches on `plugin_config`, `dashboard_layout`, `discord_config`; each maps to differently named DB setting prefixes (`dashboard.layout.*`, `discord.config.*`). Check that real consumers read those prefixes before claiming the generated layout/Discord config is operational; a successful settings write alone proves only persistence. |

### Follow-up tests
1. Reproduce UOS-CORE-025 with multi-setting proposal and injected later failure; verify no partial writes.
2. Inventory capability parameter schemas and audit payload redaction.
3. Check consumer reads for the AI-config-generated dashboard/Discord setting prefixes.
4. Reconcile decorators, dynamic imports, and actual registered capability names.

No application code changed.


## Whole-Core progress checkpoint — deeper cross-file checks (2026-10-31)

**Audit status: incomplete.** Repository source could not be cloned into the audit runtime (network DNS unavailable); GitHub connector supports file and indexed-search reads but not a recursive source-tree checkout. Consequently no claim of exhaustive all-script coverage, complete dead-symbol analysis, or successful Python test execution is justified.

| ID | Priority | Evidence level | Source → consequence |
|---|---|---|---|
| UOS-CORE-029 | High | Concrete unsupported-session-use pattern; runtime test needed | `api/routers/players.py:327+`: full-profile endpoint uses `asyncio.gather()` to concurrently execute **five database query coroutines on the same injected `AsyncSession`**. Same failure class as UOS-CORE-001 in `services/ai_service.py`; serialize queries or provide independent sessions per coroutine. Test under Postgres concurrent load. |
| UOS-CORE-030 | High in debug deployments | Auth boundary requires explicit test | `capabilities/dev_auth.py`: `auth.dev.mint_test_session` is registered with `required_permission=None` and can mint real sessions when `settings.debug` is true. Production debug=false blocks it, but **debug=true installations must be isolated**; inspect caller requirements in the REST registry and test low-privilege callers. Do not leave debug enabled on any exposed deployment. |
| UOS-CORE-031 | Medium | Sensitive-result audit distinction | `registry/registry.py` logs **request params** via `params.model_dump(mode='json')`, not result bodies. `dev_auth` session token, node signing secret and webhook secret are returned in result models, and are *not automatically dumped by this audit line*. However any future capability **input** containing secrets may leak; inventory and redact sensitive input fields. Refines UOS-CORE-026. |

### Verification / cleanup guidance

- Reuse one concurrency regression suite for both `services/ai_service.py` and `api/routers/players.py`.
- Do not call decorated capability handlers dead solely because callers use string names; registry imports them at runtime.
- Confirm `debug` is false and secret validation succeeds on all public deployments.
- After obtaining a recursive repository checkout, run a module inventory, Ruff unused-import checks, Pyright field/type checks, Python AST-based call-reference analysis, OpenAPI-to-SDK contract diff, pytest, then review any findings manually for dynamic dispatch.

**No application code modified.**


## Continuous Core audit checkpoint — 2026-11-01 (PR #7 review follow-up)

**Reference state:** PR #7 head `a4236fa4`; change branch `audit/phase1-pr7-regressions-20261101`. See [CORE_AUDIT_COVERAGE.md](CORE_AUDIT_COVERAGE.md) for the full file-level checklist. **This is a partial repair pass, not a production-readiness sign-off.**

**Coverage:** 413/413 Core tracked files inventoried; all 390 Python files were fetched and subjected to an initial static/metadata pass (224 non-migration/non-test support and app modules, 57 migration Python files including one `__init__.py`, 108 `tests/` Python files, and standalone `test_phase4.py`). Source scans looked for risky concurrency/exec/unfinished markers; migrations checked revision declarations and tests enumerated declarations. This is **not** equivalent to manual end-to-end review of every file. Remaining 23 non-Python files were inventoried but not fully audited.

### Confirmed defects addressed on the follow-up branch (pending runtime validation)

| Key | Severity | Evidence / root cause | Fix on branch | Status |
| --- | --- | --- | --- | --- |
| UOS-PR7-001 | High | PR #7 `api/routers/alt_detection.py:mark_false_positive` declares `_auth` but uses undefined `auth`; requests with an existing event raise `NameError` | Bind the actual permission-check principal; add non-skipping API regression test checking persisted reviewer and spoofed client value | Source fix committed; tests not run |
| UOS-PR7-002 | Medium | PR #7 attributes AI review actions to `User.username` although `users.username` is not unique/immutable | Persist `user:<UUID>` for authenticated User, retain `api-key:<id>` and `admin-key` sentinels; fix stale tests that expected body-supplied reviewer | Source fix committed; tests not run |
| UOS-PR7-003 | High | `ConsoleView.tsx` sends JSON text frames and assumes text responses; Core console proxy calls `receive_bytes()` and `send_bytes()` | Send binary encoded command lines and decode received binary frames | Source fix committed; browser/daemon test not run |
| UOS-002 | High | Console proxy only checks `hosting.server.view` then permits console input, allowing view-only users to send daemon commands | Permit console input only with already-seeded `hosting.server.control`; deny unauthorized frames and add proxy regression test | Source fix committed; live RBAC test not run |
| UOS-CORE-010 | Medium | `/health` intentionally returns HTTP 200 on degraded DB/Redis, unsuitable as strict readiness signal | Preserve existing `/health` contract, add `/ready` with HTTP 503 on degraded dependencies and unit regression tests | Source fix committed; tests not run |

### PR #7 review / unchanged or not fully verified

- **UOS-CORE-001 and UOS-CORE-029:** PR #7 removes observed shared-AsyncSession `asyncio.gather` uses in AI service, profile, and analytics. Change is reasonable by static inspection; no Postgres concurrency regression run. More complete async-session ownership verification remains.
- **UOS-CORE-003:** PR #7 changes Alembic migration failures to fail startup. Source improvement confirmed; boot failure-injection test outstanding.
- **UOS-CORE-019 and UOS-CORE-020:** PR #7 replaces body-supplied review attribution; branch additionally corrects undefined binding and stable User IDs. Existing test assumptions needed revision.
- **UOS-CORE-025:** PR #7 uses `db.begin_nested()` (SAVEPOINT). `SettingsService.set_value()` flushes, not commits, which supports atomicity for correctly configured DB transactions. **SQLite legacy transaction mode** can release a SAVEPOINT without a parent BEGIN; test engine configuration and rollback under SQLite and Postgres before calling this complete.
- **UOS-001:** PR #7 corrects the dashboard WebSocket URL, while this follow-up fixes binary framing. **UOS-004 remains:** long-lived *session* token is still in query and may be logged; design short-lived, single-use WS tickets before production.
- **UOS-CORE-013/014:** legacy server control executes local configured processes, not Minecraft commands; the plugin command queue has an unimplemented consumer. These are still unresolved functional design mismatches.
- **UOS-CORE-003 (config), UOS-006:** `cors_origins` remains ineffective against wildcard CORS middleware; no verified exploit, but configuration mismatch remains.
- **Unused/unfinished integration candidates:** unused `auto_action_confidence_threshold` (pending dynamic-setting check), AI orchestrator without automated tool dispatch, Discord nickname sync responsibility, `PluginCommand` unconsumed queue, and AI-proposed `dashboard.layout.*` / `discord.config.*` consumer validation.

### Unresolved highest-risk items

1. **P0 issue #1:** Minecraft plugin queue has globally shared plugin credential and caller-selected `server_id`; cross-server completion authorization not proven. The command enqueue authorization matrix is also unresolved. Do not deploy to mutually untrusted servers without server-scoped credentials and tests.
2. **High:** WebSocket bearer tokens in URLs; dedicated short-lived tickets, proxy log redaction, reconnect and expiration tests required.
3. **High:** `dev_auth` session minting when debug=true; test low-privilege registry access and prohibit exposed debug deployments.
4. **High:** Local host-process server control path, unconsumed plugin command queue, and AI configuration SQLite SAVEPOINT parent-transaction semantics.
5. **Medium:** Outbound webhook SSRF and redirect/DNS behavior, capability request-param secret redaction, dashboard/Discord/Java OpenAPI contract diff, event/delivery semantics, database and Redis failure behavior, configuration key mismatch and dead-code proof remain unverified.

### Actual validation status

- GitHub source fetch, file inventory, and static marker/revision/test-declaration scans: **performed**.
- Local clone into test container: **failed** (network DNS resolution of github.com unavailable).
- `pytest` / `compileall` on complete repo: **NOT RUN**; source not present in runtime.
- `ruff`, `pyright`, Postgres integration, browser WebSocket, dependency vulnerability checks: **NOT RUN**.
- CI: check remote status after opening follow-up PR. Do not merge if the tests fail or checks are missing.

**No modification to the Minecraft plugin implementation.** Full production sign-off remains **blocked**.
