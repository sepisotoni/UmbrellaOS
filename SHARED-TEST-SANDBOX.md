# Shared Test Sandbox (for all agents/chats)

A pre-built pytest virtualenv exists in the shared codespace
(`stunning-adventure-6v9694r9rjv4fr4vq`, account `secondary`) at:

```
/workspaces/UmbrellaOS/.shared-test-venv
```

Set up by the auth/permissions audit agent on 2026-08-30 so multiple
concurrent chats don't each burn time reinstalling the same deps. It is
**gitignored** — it lives only inside that one codespace, never in the repo.

## Usage

```bash
# Always pull first — the codespace checkout is shared too
cd /workspaces/UmbrellaOS && git pull --rebase origin main

# Run the full backend test suite
cd umbrella-core-CURRENT
/workspaces/UmbrellaOS/.shared-test-venv/bin/python -m pytest tests/ -q

# Run a specific file
/workspaces/UmbrellaOS/.shared-test-venv/bin/python -m pytest tests/test_auth_security.py -v
```

## What's installed

Exact pins from `umbrella-core-CURRENT/requirements.txt`, plus test-only
deps not needed in prod: `pytest`, `pytest-asyncio`, `httpx`, `aiosqlite`.

Tests run against an in-memory SQLite DB (see `tests/conftest.py`) — no
Postgres or Redis required. The rate limiter is stubbed to a no-op for
tests, so hermetic runs don't depend on a local Redis either.

## Adding new deps

This venv is shared and mutable on purpose:

```bash
/workspaces/UmbrellaOS/.shared-test-venv/bin/pip install <package>
```

If the package is a genuine new runtime dependency (not just test-only),
add it to `requirements.txt` too so it ships in the real deploy.

**Never `pip freeze > requirements.txt`** into this venv — it has test-only
packages (`pytest`, `httpx`, etc.) that don't belong in prod requirements.

## Known pre-existing test failures (as of 2026-08-30, ~commit ed465b5)

Confirmed via a full `pytest tests/ -q` run — none of these are caused by
the shared venv itself:

- **`tests/test_dependency_scanning.py`** — needs the `cyclonedx` package,
  not installed in the shared venv (SBOM/dependency-scanning subsystem).
- ~~`tests/test_verification.py`, `tests/registry/test_capabilities_verification.py`~~
  — **FIXED** by [AUTH] (commit `b131de1`). Root cause: `expires_at` is
  `DateTime(timezone=True)`, always tz-aware on Postgres but SQLite drops
  tzinfo on write/read, so `datetime.now(timezone.utc) > expires_at` raised
  the naive/aware TypeError under the SQLite test harness. Fixed in both
  `api/routers/verification.py` (added `_aware()` helper, 2 call sites) and
  `services/verification/service.py` (inline normalize, 1 call site — the
  Capability Registry path hits this file, not the router, so both needed
  the same fix). 28/28 tests passing as of `dd28023`.
- **`tests/test_ai_config.py`**, **`tests/test_appeals.py`**,
  **`tests/test_moderation_intelligence.py`**, **`tests/test_provider_factory.py`**
  — AI/appeals/moderation subsystems, not investigated by the auth agent.

If you fix one of the above, please update this list so the next agent
doesn't re-diagnose the same failure from scratch.

## Auth/permissions subsystem status ([AUTH])

`tests/test_auth_security.py` (15 tests), `tests/test_mfa_service.py` (7
tests), and `tests/test_auth.py` (17 tests) — **45/45 passing** as of
commit `ed465b5`. Covers: timing-safe key comparison, session token query-
param leakage, MFA enrollment/verify/disable flow, MFA pre-session token
isolation (cannot be used as a full session), WAF-adjacent auth paths,
permission-gated endpoints vs raw-key bypass.

Also picked up Settings/Knowledge/Webhooks/Bridge/Verification/Appeals work
under this same [AUTH] slot (previously mislabeled [CURSOR] in a couple of
commit messages/notices — corrected). Full subsystem sweep (157 tests) —
**157/157 passing** as of commit `5fd2462`:
`test_appeals.py`, `test_verification.py`, `test_knowledge.py`,
`test_feature_flags.py`, `test_settings.py`, `test_bridge.py`,
`test_webhook_delivery.py`, `test_settings_seed_from_env.py`, `test_auth.py`,
`test_auth_security.py`, `test_mfa_service.py`,
`registry/test_capabilities_verification.py`,
`registry/test_capabilities_knowledge.py`, `registry/test_capabilities_webhooks.py`.

Fixes along the way: knowledge.py (discord_message_id overflow,
superseded/PENDING guards, audit trail), webhooks_rest.py (missing PATCH
endpoint, catch-all-as-404, created_by=None), bridge.py (DASHBOARD
broadcasts never forwarded, settings bypassing SettingsService),
verification.py + services/verification/service.py (links filter, code
uniqueness/invalidation, revoke silent-success, naive/aware datetime
TypeError), feature_flags.py (description clearing, audit trail),
appeals.py (2 stale tests updated to match already-corrected
plugin-key/status-validation behavior from a prior audit) — see master bug
report for finding IDs.
