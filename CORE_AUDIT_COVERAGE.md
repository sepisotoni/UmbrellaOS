# UmbrellaOS Core — file-level audit coverage (2026-11-01)

**Baseline:** PR #7 head `a4236fa4f845765bb285b6043c55b49fd20656d7` (`fix/core-shared-session-query-concurrency`). The remedial branch adds `tests/test_pr7_regressions.py` after this baseline inventory.

**Important:** A checked box below indicates a real GitHub file fetch and limited **automated/static inspection**, NOT a completed manual, end-to-end functional audit or a passing test. Source scans looked for concurrency/task markers, subprocess/eval, TODO/unfinished markers. Migration coverage inspected declared revisions and ancestors, and test coverage inventoried declared tests. The role/schema/caller analysis has only been done on a subset. Do not equate raw-fetch coverage with production readiness.

## Coverage summary

- All Core tracked files inventoried: **413 / 413**.
- Baseline Python files fetched: **390 / 390** (224 application/support modules, 57 version migration modules including `__init__.py`, 108 under `tests/`, plus standalone `test_phase4.py`).
- Other configuration/documentation/asset files: **23**, inventory only.
- Confirmed in-depth/targeted source-reading subset: **21** Python files, with no claim of complete line-by-line proof.
- CI/pytest/Ruff/Pyright/dependency audit were **not run** in this connector-only environment. Remote CI may run after the PR is submitted; record exact results separately.

## Checklist

| File | Initial read/scan | Targeted source examination | Deep E2E verified |
|---|---|---|---|
| `.env.example` | [ ] Inventory only | [ ] | [ ] |
| `.github/workflows/dependency-scan.yml` | [ ] Inventory only | [ ] | [ ] |
| `Dockerfile` | [ ] Inventory only | [ ] | [ ] |
| `README.md` | [ ] Inventory only | [ ] | [ ] |
| `alembic.ini` | [ ] Inventory only | [ ] | [ ] |
| `alembic/env.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `alembic/versions/001_initial.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/002_phase3_foundation_models.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/003_phase7_discord_bridge.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/004_phase8_verification.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/005_phase9_alt_detection.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/006_phase10_analytics.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/007_phase11_replay.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/008_phase12_snapshots.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/009_phase13_ai_tasks.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/010_mc_commands_translation.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/011_add_suspicion_score.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/012_hosting_domain.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/013_identity_phase3.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/014_phase4_automation.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/015_ai_layer.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/016_moderation_intel.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/017_investigation_knowledge.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/018_knowledge_base.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/019_memory.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/020_server_metrics.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/021_escalation_notified_at.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/022_events_outbox.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/023_webhook_subscriptions.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/024_marketplace.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/025_observability_security.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/026_dashboard_layouts.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/027_plugin_kv_entries.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/028_plugin_execution_records.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/029_feature_flags.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/030_appeal_close_fields.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/031_add_bot_registration.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/032_add_discord_avatar_hash.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/033_add_anticheat_violations_table.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/034_plugin_heartbeats_and_commands.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/035_plugin_console_lines.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/036_bot_command_manifest.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/037_bot_guild_channels.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/038_bot_guild_roles.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/039_fix_check_constraints.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/040_add_users_sessions_discord_oauth.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/041_fix_ipban_player_uuid_and_punishment_nullable.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/042_add_reduced_appeal_status.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/042_seed_ai_model_configs.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/043_ai_model_configs_unique.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/044_widen_knowledge_discord_message_id.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/045_merge_042_branches.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/046_deprecate_ai_model_setting.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/047_add_anticheat_violation_player_fk.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/048_widen_alembic_version.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/049_fix_retired_gemini_model.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/050_add_mfa_recovery_codes.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/051_add_mc_commands_server_id.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/052_add_plugin_console_lines_index.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/053_add_discord_role_id_settings.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/054_drop_redundant_console_lines_index.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/055_fix_admin_role_permissions.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `alembic/versions/__init__.py` | [x] Revision metadata and file fetched | [ ] | [ ] |
| `api/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/dependencies/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/dependencies/permissions.py` | [x] Heuristic code scan and file fetched | [x] Targeted sections | [ ] |
| `api/middleware/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/middleware/api_key_auth.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/middleware/audit.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/middleware/auth.py` | [x] Heuristic code scan and file fetched | [x] Targeted sections | [ ] |
| `api/middleware/errors.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/middleware/metrics.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/middleware/rate_limit.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/middleware/session.py` | [x] Heuristic code scan and file fetched | [x] Targeted sections | [ ] |
| `api/middleware/tracing.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/middleware/waf.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/ai_config.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/ai_copilot.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/ai_tasks.py` | [x] Heuristic code scan and file fetched | [x] Targeted sections | [ ] |
| `api/routers/alt_detection.py` | [x] Heuristic code scan and file fetched | [x] Targeted sections | [ ] |
| `api/routers/analytics.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/anticheat.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/appeals.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/audit.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/auth.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/bot_registration.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/bridge.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/dashboard.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/feature_flags.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/health.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/hosting_console_ws.py` | [x] Heuristic code scan and file fetched | [x] Targeted sections | [ ] |
| `api/routers/knowledge.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/logs.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/mc_commands.py` | [x] Heuristic code scan and file fetched | [x] Targeted sections | [ ] |
| `api/routers/metrics.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/moderation.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/players.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/plugin.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/punishments.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/replay.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/roles.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/security.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/server_control.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/settings.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/snapshot.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/staff.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/translation.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/verification.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/routers/webhooks_rest.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/schemas/plugin_control.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `api/validators.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/alt_detection_maintenance.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/anticheat_maintenance.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/archive_search.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/automation.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/dashboard_layout.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/dev_auth.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/feature_flags.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/hosting.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/identity.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/investigation.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/knowledge.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/marketplace.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/memory.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/moderation_intelligence.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/observability.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/operational_intelligence.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/player_risk.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/plugin_sandbox.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/shared.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/system.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/verification.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `capabilities/webhooks.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `cli.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `config/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `config/settings.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `database/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `database/engine.py` | [x] Heuristic code scan and file fetched | [x] Targeted sections | [ ] |
| `database/redis_client.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `docker-compose.yml` | [ ] Inventory only | [ ] | [ ] |
| `docs/adr/0001-capability-registry.md` | [ ] Inventory only | [ ] | [ ] |
| `docs/adr/0003-hosting-domain.md` | [ ] Inventory only | [ ] | [ ] |
| `docs/adr/0004-identity-and-console-gateway.md` | [ ] Inventory only | [ ] | [ ] |
| `docs/adr/0005-backups-scheduling-self-healing.md` | [ ] Inventory only | [ ] | [ ] |
| `docs/adr/phase-6-notes-from-phase-5.md` | [ ] Inventory only | [ ] | [ ] |
| `docs/adr/phase-7-notes-from-phase-5.md` | [ ] Inventory only | [ ] | [ ] |
| `docs/design/phase10-decision2-config-write-capability-shape.md` | [ ] Inventory only | [ ] | [ ] |
| `docs/design/plugin-sdk-manifest-and-registration.md` | [ ] Inventory only | [ ] | [ ] |
| `docs/design/public-rest-api-and-webhooks.md` | [ ] Inventory only | [ ] | [ ] |
| `docs/observability/README.md` | [ ] Inventory only | [ ] | [ ] |
| `docs/observability/grafana-dashboard.json` | [ ] Inventory only | [ ] | [ ] |
| `main.py` | [x] Heuristic code scan and file fetched | [x] Targeted sections | [ ] |
| `models/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/ai.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/ai_config.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/ai_tasks.py` | [x] Heuristic code scan and file fetched | [x] Targeted sections | [ ] |
| `models/alt_detection.py` | [x] Heuristic code scan and file fetched | [x] Targeted sections | [ ] |
| `models/analytics.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/anticheat_violation.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/api_key.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/audit_log.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/automation.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/bot_command_manifest.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/bot_guild_channels.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/bot_guild_roles.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/bot_registration.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/dashboard_layout.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/discord.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/events.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/feature_flag.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/hosting.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/investigation.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/knowledge.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/log_entry.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/marketplace.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/mc_commands.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/memory.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/moderation_intelligence.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/permissions.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/player.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/plugin_command.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/plugin_console_line.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/plugin_execution.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/plugin_heartbeat.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/plugin_kv.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/replay.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/security_event.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/server_metrics.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/setting.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/snapshot.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/translation.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/user.py` | [x] Heuristic code scan and file fetched | [x] Targeted sections | [ ] |
| `models/verification.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `models/webhook.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `package-lock.json` | [ ] Inventory only | [ ] | [ ] |
| `package.json` | [ ] Inventory only | [ ] | [ ] |
| `pytest.ini` | [ ] Inventory only | [ ] | [ ] |
| `registry/README.md` | [ ] Inventory only | [ ] | [ ] |
| `registry/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `registry/adapters/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `registry/adapters/ai.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `registry/adapters/cli.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `registry/adapters/rest.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `registry/audit.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `registry/context.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `registry/decorator.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `registry/registry.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `registry/spec.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `requirements-dev.txt` | [ ] Inventory only | [ ] | [ ] |
| `requirements.txt` | [ ] Inventory only | [ ] | [ ] |
| `scripts/export_openapi_schema.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `scripts/generate_sbom.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `scripts/scan_dependencies.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/ai/action_guard.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/ai/anthropic_provider.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/ai/base.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/ai/constitution_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/ai/copilot_tools.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/ai/gemini_provider.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/ai/model_router.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/ai/openrouter_provider.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/ai/orchestrator.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/ai/provider_factory.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/ai_config_service.py` | [x] Heuristic code scan and file fetched | [x] Targeted sections | [ ] |
| `services/ai_service.py` | [x] Heuristic code scan and file fetched | [x] Targeted sections | [ ] |
| `services/allocation_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/alt_detection_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/analytics_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/anticheat_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/api_key_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/archive_search/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/archive_search/service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/backup_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/bot_push_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/daemon_client.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/dashboard_layout/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/dashboard_layout/pages.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/dashboard_layout/service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/discord_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/events/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/events/bus.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/events/dispatcher.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/events/subscribers.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/feature_flag_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/investigation/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/investigation/repository.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/investigation/service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/investigation/tools.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/knowledge/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/knowledge/repository.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/knowledge/service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/log_aggregation_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/memory/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/memory/repository.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/memory/service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/metrics_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/mfa_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/moderation_intelligence/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/moderation_intelligence/heuristics.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/moderation_intelligence/repository.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/moderation_intelligence/service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/node_auth_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/node_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/operational_intelligence/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/operational_intelligence/crash_prevention.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/operational_intelligence/metrics.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/operational_intelligence/nl_query.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/operational_intelligence/postmortem.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/operational_intelligence/sampler_loop.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/permission_resolution.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/player_risk/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/player_risk/risk_score.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/plugin_kv/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/plugin_kv/service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/plugins/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/plugins/manifest.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/plugins/marketplace_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/plugins/registration.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/plugins/runtime.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/plugins/sandbox.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/plugins/sandbox_guard.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/plugins/source_store.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/rate_limit_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/replay_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/roles_service.py` | [x] Heuristic code scan and file fetched | [x] Targeted sections | [ ] |
| `services/scheduler_loop.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/scheduler_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/secrets_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/server_control_service.py` | [x] Heuristic code scan and file fetched | [x] Targeted sections | [ ] |
| `services/server_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/server_template_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/settings_service.py` | [x] Heuristic code scan and file fetched | [x] Targeted sections | [ ] |
| `services/snapshot_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/staff_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/threat_detection_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/tracing_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/translation_service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/verification/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/verification/service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/webhooks/__init__.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `services/webhooks/service.py` | [x] Heuristic code scan and file fetched | [ ] | [ ] |
| `test_phase4.py` | [x] File fetched | [ ] | [ ] |
| `tests/__init__.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/conftest.py` | [x] Test inventory and file fetched | [x] Targeted sections | [ ] |
| `tests/registry/__init__.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/conftest.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_adapters_ai.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_alt_detection_maintenance.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_anticheat_maintenance.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_archive_search.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_automation.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_backup.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_dashboard_layout.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_discord_delegation.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_hosting.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_identity.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_investigation.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_knowledge.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_marketplace.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_memory.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_moderation_intelligence.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_operational_intelligence.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_player_risk.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_plugin_sandbox.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_system.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_verification.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_capabilities_webhooks.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_cli_adapter.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_marketplace_service.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_plugin_execution_telemetry.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_plugin_manifest.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_plugin_registration.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_plugin_runtime.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_plugin_sandbox.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_plugin_sandbox_guard.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_plugin_source_store.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/registry/test_registry_core.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_action_guard.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_ai_config.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_ai_providers.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_ai_service.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_ai_tasks.py` | [x] Test inventory and file fetched | [x] Targeted sections | [ ] |
| `tests/test_alt_detection.py` | [x] Test inventory and file fetched | [x] Targeted sections | [ ] |
| `tests/test_analytics.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_anticheat_retention.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_api_key_auth.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_api_key_service.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_appeals.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_archive_search.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_audit.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_auth.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_auth_security.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_backup_service.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_bridge.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_constitution_service.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_copilot_tools.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_crash_prevention.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_daemon_client.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_dashboard.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_dependency_scanning.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_dev_auth.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_event_bus.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_event_dispatcher.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_feature_flags.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_health.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_hosting_console_ws.py` | [x] Test inventory and file fetched | [x] Targeted sections | [ ] |
| `tests/test_hosting_services.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_investigation.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_knowledge.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_log_aggregation.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_mc_commands.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_memory.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_metrics.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_mfa_service.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_model_router.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_moderation.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_moderation_intelligence.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_nl_query.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_node_auth_service.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_observability_routers.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_operational_intelligence_metrics.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_orchestrator.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_permissions.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_players.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_plugin_control.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_plugin_punishment_check.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_postmortem.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_provider_factory.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_punishments.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_rate_limit.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_rate_limit_middleware.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_rate_limit_service.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_replay.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_risk_score.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_roles_service.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_scheduler_loop.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_scheduler_service.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_secrets_service.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_self_healing.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_server_control.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_server_staff.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_settings.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_settings_seed_from_env.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_snapshots.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_suspicion_decay.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_threat_detection.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_translation.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_verification.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_waf_middleware.py` | [x] Test inventory and file fetched | [ ] | [ ] |
| `tests/test_webhook_delivery.py` | [x] Test inventory and file fetched | [ ] | [ ] |

## Next systematic checks

1. Execute import/compile checks, Ruff, Pyright, dependency scan, Postgres and SQLite test suites, and WebSocket browser-to-daemon tests.
2. Generate an OpenAPI schema, compare to dashboard/Discord/Minecraft callers, and verify exact field names.
3. Per-route permission matrix, server-specific resource authorization, plugin credential scoping, secret redaction, SSRF and sandbox escape tests.
4. Verify service transaction semantics, migrations on a real migrated database, event dispatch outbox delivery, and background task cleanup.
5. Update each remaining unchecked **deep E2E verified** cell only when runtime evidence exists.
