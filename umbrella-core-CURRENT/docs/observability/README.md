# Observability & Security Hardening (Phase 9)

Status: **umbrella-core side only**. See the scope note in each module's
docstring — daemon-side and dashboard-side instrumentation is out of
reach from this code source (same loose end as the Phase 7→8
Discord/dashboard boundary) and isn't claimed as done here.

## Metrics

`GET /metrics` (admin-key/session gated) exposes Prometheus text format.
Implemented from scratch in `services/metrics_service.py` — not the
`prometheus_client` package, which wasn't installable in the sandbox this
was built in (no network access; not in the local wheel cache). If/when
`prometheus_client` becomes available, swapping it in only touches that
one file — nothing else depends on the storage internals.

Point Prometheus at it with a static header for the admin key, e.g.:

```yaml
scrape_configs:
  - job_name: umbrella-core
    metrics_path: /metrics
    static_configs:
      - targets: ["your-host:PORT"]
    authorization:
      credentials: <your ADMIN_KEY>
      # or use `params`/custom headers depending on your Prometheus
      # version's support for a non-standard header name like X-Admin-Key
```

Load `docs/observability/grafana-dashboard.json` into Grafana as a
starting point — 7 panels, each mapped to a metric this process actually
emits. It's a starting point, not a finished dashboard: no alerting rules,
no annotations, no multi-instance/`instance` label handling (this project
runs single-node, so none of the panels aggregate across instances).

## Tracing

`services/tracing_service.py` is backed by the real OpenTelemetry SDK
(`opentelemetry-api`/`-sdk`/`-exporter-otlp-proto-http`, all pinned in
`requirements.txt`) — the original hand-rolled W3C `traceparent` shim
from Phase 9's building session (no network access, couldn't install the
SDK) was swapped out in a follow-up session with real network access,
after empirically verifying its wire-format-compatibility claim rather
than trusting it. See that module's docstring for exactly what was
verified (mostly right, one real gap — a missing W3C Trace Context Level
2 flag bit, fixed by the swap itself) and what changed. Every request
still gets a real span, a `traceparent` response header, and every
aggregated log line is still stamped with the current trace_id
(`log_entries`). Export to a real OTLP collector is now genuinely wired
up (`OTEL_EXPORTER_OTLP_ENDPOINT`) but off by default — this project
doesn't bundle a collector.

## Log aggregation

`GET /api/v1/logs` (permission: `observability.logs.view`) searches
`log_entries`, populated by a root-logger handler
(`services/log_aggregation_service.py`) that queues records and flushes
them to the DB every few seconds. Search is a portable `ILIKE` substring
match, not a dedicated FTS index — see `models/log_entry.py`'s docstring
for why, and what to change if log volume ever outgrows it.

Only umbrella-core's own log records land here today (see the scope note
above).

## Threat detection

`services/threat_detection_service.py` watches three signals — repeated
auth failures, repeated rate-limit violations, and any plugin sandbox
violation — scoped to this project's actual threat model (Phase 0: a
single-operator, internet-exposed platform, not enterprise SIEM tooling).
Crossing a threshold publishes a `security.threat_detected` event on the
existing EventBus, the same mechanism Phase 6/7's webhook subscribers and
Discord bot already use — no new delivery path was invented.

`GET /api/v1/security/events` (permission: `security.events.view`) lists
the raw recorded signals. Thresholds/cooldown are configurable via
`.env` — see `.env.example`.

## WAF-style hardening

`api/middleware/waf.py` rejects a small, specific set of automated-scanner
patterns (path traversal, obvious SQLi/XSS payloads, oversized bodies)
before routing/auth. It is a cheap early-reject layer, not the actual
defense against SQL injection (parameterized queries, already used
throughout this codebase, are that). Every block is recorded as a
`waf_block` security event, feeding the same threat-detection path above.

## Plugin sandboxing hardening

`services/plugins/sandbox_guard.py` and `sandbox.py` gained: a handful of
additional forbidden dunder-attribute names found during Phase 8
adversarial hand-testing, a max-source-size cap, and — new in Phase 9 —
every static-guard rejection and resource-limit kill is now recorded as a
`sandbox_violation` security event and a `umbrella_sandbox_violations_total`
metric, instead of only surfacing as a raised exception to the caller.

## Dependency / CVE scanning

`scripts/scan_dependencies.py` (pip-audit wrapper) and
`scripts/generate_sbom.py` (CycloneDX SBOM from `requirements.txt`), run
by `.github/workflows/dependency-scan.yml` on a weekly schedule and on
every `requirements.txt` change. **Could not be run end-to-end in the
sandbox this was built in** — pip-audit needs network access this sandbox
doesn't have. What *was* verified locally: SBOM generation (fully local,
ran successfully against the real `requirements.txt`), and — importantly —
two real false-negative bugs in the scan script were found and fixed
while testing what *could* be tested offline (see that script's
docstring and `tests/test_dependency_scanning.py` for the specifics). The
actual vulnerability scan itself needs to run in CI, where real network
access exists.
