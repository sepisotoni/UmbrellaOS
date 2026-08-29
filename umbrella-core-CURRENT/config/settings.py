"""
config/settings.py — Central configuration loaded from .env
All settings live here. Never import os.environ directly elsewhere.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://umbrella:changeme@localhost:5432/umbrella_core"
    database_url_sync: str = "postgresql+psycopg2://umbrella:changeme@localhost:5432/umbrella_core"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Rate limiting (Phase 3) — per-client-IP, applied globally except /healthz
    rate_limit_requests_per_window: int = 120
    rate_limit_window_seconds: int = 60

    # Rate limiting (Phase 7) — additive per-API-key limit, layered on top of
    # the per-IP limit above rather than replacing it (see
    # docs/design/public-rest-api-and-webhooks.md, Decision 1). Only applied
    # when a request presents X-Api-Key. Independently configurable from the
    # per-IP pair since a machine integration's legitimate request volume
    # looks different from a browser's.
    rate_limit_api_key_requests_per_window: int = 300
    rate_limit_api_key_window_seconds: int = 60

    # Secrets encryption (Phase 4) — a Fernet key (44 base64 chars). Generate
    # with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # No default: an unset key must fail loudly (services/secrets_service.py),
    # not silently fall back to storing secrets in plaintext.
    secrets_encryption_key: str | None = None

    # AI operating-system layer (Phase 5) — provider API keys and
    # enabled/disabled toggles live in the DB-backed Setting model
    # (category="ai"), not here — see services/settings_service.py's
    # DEFAULT_SETTINGS and services/ai/provider_factory.py. That's the
    # pre-existing, working pattern this codebase already used for
    # ai.anthropic_api_key (confirmed by reading services/ai_service.py's
    # actual usage before choosing this over a new mechanism) — it's also
    # what makes providers dashboard-toggleable at runtime without a
    # restart, which a pydantic Settings field (env-var-sourced, fixed at
    # process start) cannot do.
    ai_model_health_cooldown_seconds: int = 300  # half-open retry window after a model is marked unhealthy
    ai_model_unhealthy_after_failures: int = 3
    dual_review_enabled: bool = True
    confidence_escalation_threshold: float = 0.6  # below this, an AI decision is flagged for staff review

    # Moderation intelligence heuristic detectors (services/moderation_intelligence/heuristics.py)
    # - defaults are Moo-assistant's original tuned values, ported as-is rather than re-derived.
    spam_message_threshold: int = 6  # N+ messages within spam_window_seconds -> flagged
    spam_window_seconds: int = 10
    raid_join_threshold: int = 8  # N+ joins within raid_window_seconds -> flagged as a possible raid
    raid_window_seconds: int = 30
    repeat_offender_warning_count: int = 3  # N+ warnings within the lookback window -> auto-report
    repeat_offender_lookback_hours: int = 24
    # Consumed once Phase 6 wires up real auto-apply execution (see
    # services/moderation_intelligence/service.py's module docstring) -
    # added now since it's a real, already-decided value, not speculative.
    auto_action_confidence_threshold: float = 0.75
    # Which channel names (comma-separated, without the leading '#') get
    # auto-indexed into the knowledge base - deployment-specific, unlike
    # the source (bot/knowledge/constants.py), which hardcoded one Discord
    # server's own channel names as a Python constant. Empty by default:
    # there's no universally-sensible default for a differently-branded
    # deployment, and an empty list means "index nothing" rather than
    # silently indexing channels that happen to share a name with Moo's
    # original server.
    knowledge_channel_names: str = ""
    short_term_memory_ttl_seconds: int = 1800  # 30 min - ported default from Moo's config
    server_metric_sample_interval_seconds: int = 60
    server_metric_retention_hours: int = 168  # 7 days
    # Predictive crash prevention thresholds (services/operational_intelligence/crash_prevention.py)
    crash_prevention_lookback_minutes: int = 15
    crash_prevention_min_samples: int = 3
    crash_prevention_critical_tps: float = 10.0  # below this, flag critical regardless of trend
    crash_prevention_watch_tps: float = 18.0  # below this AND trending down -> flag watch
    crash_prevention_trend_drop_threshold: float = 2.0  # min TPS drop (2nd half avg vs 1st half avg) to count as "trending down"
    # Unified player risk score weights (services/player_risk/risk_score.py) -
    # deliberately simple, explainable point-based weights, not a trained
    # model - same philosophy as crash prevention's heuristic.
    risk_score_anticheat_points_cap: int = 100  # unreviewed, non-false-positive SuspicionEvent.points, capped here
    risk_score_confirmed_alt_penalty: int = 30
    risk_score_per_moderation_action: int = 5
    risk_score_moderation_action_cap: int = 30
    risk_score_per_investigation: int = 2
    risk_score_investigation_cap: int = 10

    # Marketplace plugin storage (Phase 7 item 3) — local disk, per the
    # marketplace design decision: published plugin zips and their
    # extracted source live under
    # f"{plugin_storage_root}/{plugin_id}/{version}/", never a shared
    # location versions could clobber each other in. Relative paths are
    # resolved against the process working directory, matching how
    # `database_url_sync`'s sqlite fallback and other file-based settings
    # in this codebase already behave — no separate "make this absolute"
    # step exists elsewhere to mirror.
    plugin_storage_root: str = "data/plugins"

    # Security
    secret_key: str = "change-me-in-production"
    admin_key: str = "change-me-in-production"

    # Initial admin bootstrap
    initial_admin_discord_id: str = ""

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8765
    debug: bool = False
    cors_origins: list[str] = [
        "https://umbrella-os-phi.vercel.app",
        "https://umbrella-os-ndilimqeni-6825s-projects.vercel.app",
        "https://umbrella-dashboard.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # Optional — will be moved to DB settings after first boot
    discord_client_id: str = ""
    discord_client_secret: str = ""
    discord_bot_token: str = ""
    rcon_host: str = "localhost"
    rcon_port: int = 25575
    rcon_password: str = ""

    # Emergency recovery: when true, settings seeding force-overwrites
    # DB values from .env on next boot (instead of only filling gaps).
    # Meant to be set manually for a single restart, then turned back off.
    force_env_override: bool = False

    # Phase 5 addition: gates the ENTIRE .env-to-DB sync on boot (both the
    # default gap-fill path and force_env_override's force-overwrite
    # path) behind an explicit opt-in, auto-reset after it runs — see
    # SettingsService.seed_defaults. Previously the gap-fill sync ran
    # unconditionally on every boot; while idempotent, an operator asked
    # for boot-time .env syncing to be opt-in and self-disabling rather
    # than always-on, so a stale .env value can't silently resurface after
    # being intentionally cleared via the dashboard.
    seed_from_env: bool = False

    # Phase 9 — threat detection thresholds (see
    # services/threat_detection_service.py for the scoping rationale).
    # Defaults chosen for a single-operator, internet-exposed Minecraft
    # server platform, not enterprise SIEM tuning: a real brute-force
    # attempt against a small admin platform looks like a handful of
    # failures in a short window, not thousands.
    threat_detection_window_seconds: int = 300
    threat_detection_auth_failure_threshold: int = 5
    threat_detection_rate_limit_threshold: int = 10
    threat_detection_alert_cooldown_seconds: int = 900

    # Tracing (Phase 9, item 2) — real OpenTelemetry SDK (see
    # services/tracing_service.py). Both default off/unset: with neither
    # set, spans are still created in-process (trace_id/span_id
    # propagation via the real W3C TraceContextTextMapPropagator, and log
    # stamping via services/log_aggregation_service.py, both keep working
    # exactly as before) but nothing is exported anywhere, which is a
    # supported, intentional TracerProvider configuration — this project
    # has no bundled collector to point at by default. Set
    # otel_exporter_otlp_endpoint to export real spans via OTLP/HTTP to a
    # collector you run yourself; otel_console_export is a separate, purely
    # local debugging toggle (prints spans to stdout) — independent of the
    # OTLP endpoint so either, both, or neither can be on.
    otel_exporter_otlp_endpoint: str | None = None
    otel_console_export: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance. Use this everywhere."""
    return Settings()
