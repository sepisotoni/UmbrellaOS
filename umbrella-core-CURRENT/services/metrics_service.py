"""
services/metrics_service.py — In-process Prometheus-format metrics registry
(Phase 9, item 1: "Prometheus-format metrics exposition from core").

Deliberately hand-rolled rather than built on the `prometheus_client`
package: this environment has no network access to fetch it (see Phase 9
handoff notes), and the exposition format itself (text/plain 0.0.4) is
small and stable enough to implement directly without meaningfully more
risk than vendoring the real library. If/when `prometheus_client` becomes
installable here, swapping this module's internals for it is a drop-in
change — nothing outside this file depends on the storage details, only on
`registry.render()` producing valid exposition text and the
Counter/Gauge/Histogram helper methods below.

Process-wide, module-level state (mirrors the EventBus subscriber registry
and CapabilityRegistry pattern already used elsewhere in this codebase):
metrics are held in memory for this process's lifetime and reset on
restart, which is the correct behavior for a Prometheus counter/gauge —
Prometheus itself is responsible for persisting the time series, not the
exposition target.

Thread/task safety: increments use plain dict mutation, not locks. This
matches CPython's GIL-backed atomicity for simple dict item assignment and
the fact that this process is a single-event-loop asyncio app (no
multiprocessing worker pool sharing this object) — safe for read-modify-write
performed via the helper methods below because there's no `await` between
the read and the write, so no other coroutine can interleave.
"""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock


class Counter:
    """Monotonically increasing value, e.g. total requests served."""

    def __init__(self, name: str, help_text: str, label_names: tuple[str, ...] = ()):
        self.name = name
        self.help_text = help_text
        self.label_names = label_names
        self._values: dict[tuple[str, ...], float] = defaultdict(float)
        self._lock = Lock()

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        key = tuple(labels.get(n, "") for n in self.label_names)
        with self._lock:
            self._values[key] += amount

    def render(self) -> list[str]:
        lines = [f"# HELP {self.name} {self.help_text}", f"# TYPE {self.name} counter"]
        for key, value in self._values.items():
            lines.append(f"{self.name}{_label_str(self.label_names, key)} {value}")
        return lines


class Gauge:
    """Value that can go up or down, e.g. currently-installed plugin count."""

    def __init__(self, name: str, help_text: str, label_names: tuple[str, ...] = ()):
        self.name = name
        self.help_text = help_text
        self.label_names = label_names
        self._values: dict[tuple[str, ...], float] = defaultdict(float)
        self._lock = Lock()

    def set(self, value: float, **labels: str) -> None:
        key = tuple(labels.get(n, "") for n in self.label_names)
        with self._lock:
            self._values[key] = value

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        key = tuple(labels.get(n, "") for n in self.label_names)
        with self._lock:
            self._values[key] += amount

    def dec(self, amount: float = 1.0, **labels: str) -> None:
        self.inc(-amount, **labels)

    def render(self) -> list[str]:
        lines = [f"# HELP {self.name} {self.help_text}", f"# TYPE {self.name} gauge"]
        for key, value in self._values.items():
            lines.append(f"{self.name}{_label_str(self.label_names, key)} {value}")
        return lines


# Fixed bucket boundaries in seconds — tuned for API request latencies
# (sub-millisecond to multi-second), not a generic default. Matches the
# smallest set that still gives useful p50/p95/p99 resolution for an
# admin-tool-scale API rather than a high-throughput service.
DEFAULT_LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


class Histogram:
    """Distribution of observed values, e.g. request duration."""

    def __init__(
        self,
        name: str,
        help_text: str,
        label_names: tuple[str, ...] = (),
        buckets: tuple[float, ...] = DEFAULT_LATENCY_BUCKETS,
    ):
        self.name = name
        self.help_text = help_text
        self.label_names = label_names
        self.buckets = buckets
        self._bucket_counts: dict[tuple[str, ...], list[int]] = defaultdict(lambda: [0] * (len(buckets) + 1))
        self._sums: dict[tuple[str, ...], float] = defaultdict(float)
        self._counts: dict[tuple[str, ...], int] = defaultdict(int)
        self._lock = Lock()

    def observe(self, value: float, **labels: str) -> None:
        key = tuple(labels.get(n, "") for n in self.label_names)
        with self._lock:
            self._sums[key] += value
            self._counts[key] += 1
            counts = self._bucket_counts[key]
            for i, bound in enumerate(self.buckets):
                if value <= bound:
                    counts[i] += 1
            counts[-1] += 1  # +Inf bucket

    def render(self) -> list[str]:
        lines = [f"# HELP {self.name} {self.help_text}", f"# TYPE {self.name} histogram"]
        for key, counts in self._bucket_counts.items():
            cumulative = 0
            for i, bound in enumerate(self.buckets):
                cumulative += counts[i]
                bucket_labels = dict(zip(self.label_names, key))
                bucket_labels["le"] = str(bound)
                lines.append(f"{self.name}_bucket{_label_str(tuple(bucket_labels), tuple(bucket_labels.values()))} {cumulative}")
            cumulative += counts[-1]
            bucket_labels = dict(zip(self.label_names, key))
            bucket_labels["le"] = "+Inf"
            lines.append(f"{self.name}_bucket{_label_str(tuple(bucket_labels), tuple(bucket_labels.values()))} {cumulative}")
            lines.append(f"{self.name}_sum{_label_str(self.label_names, key)} {self._sums[key]}")
            lines.append(f"{self.name}_count{_label_str(self.label_names, key)} {self._counts[key]}")
        return lines


def _label_str(names: tuple[str, ...], values: tuple[str, ...]) -> str:
    if not names:
        return ""
    pairs = ",".join(f'{n}="{_escape(v)}"' for n, v in zip(names, values))
    return "{" + pairs + "}"


def _escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class MetricsRegistry:
    """Holds every metric this process exposes and renders them together."""

    def __init__(self):
        self._metrics: dict[str, Counter | Gauge | Histogram] = {}
        self.start_time = time.time()

    def counter(self, name: str, help_text: str, label_names: tuple[str, ...] = ()) -> Counter:
        if name not in self._metrics:
            self._metrics[name] = Counter(name, help_text, label_names)
        return self._metrics[name]  # type: ignore[return-value]

    def gauge(self, name: str, help_text: str, label_names: tuple[str, ...] = ()) -> Gauge:
        if name not in self._metrics:
            self._metrics[name] = Gauge(name, help_text, label_names)
        return self._metrics[name]  # type: ignore[return-value]

    def histogram(
        self, name: str, help_text: str, label_names: tuple[str, ...] = (), buckets: tuple[float, ...] = DEFAULT_LATENCY_BUCKETS
    ) -> Histogram:
        if name not in self._metrics:
            self._metrics[name] = Histogram(name, help_text, label_names, buckets)
        return self._metrics[name]  # type: ignore[return-value]

    def render(self) -> str:
        lines: list[str] = []
        for metric in self._metrics.values():
            lines.extend(metric.render())
        return "\n".join(lines) + "\n"

    def reset(self) -> None:
        """Test-only: clears all registered metrics and their values."""
        self._metrics.clear()
        self.start_time = time.time()


# Process-wide singleton, mirrors the EventBus/CapabilityRegistry pattern.
registry = MetricsRegistry()

# Core metrics, defined once at import time so every module that records
# them shares the same Counter/Histogram/Gauge instance.
http_requests_total = registry.counter(
    "umbrella_http_requests_total",
    "Total HTTP requests handled, by method/path/status.",
    label_names=("method", "path", "status"),
)
http_request_duration_seconds = registry.histogram(
    "umbrella_http_request_duration_seconds",
    "HTTP request duration in seconds, by method/path.",
    label_names=("method", "path"),
)
events_dispatched_total = registry.counter(
    "umbrella_events_dispatched_total",
    "Total events dispatched from the outbox, by topic.",
    label_names=("topic",),
)
events_dispatch_failed_total = registry.counter(
    "umbrella_events_dispatch_failed_total",
    "Total event dispatch attempts that raised, by topic.",
    label_names=("topic",),
)
installed_plugins = registry.gauge(
    "umbrella_installed_plugins",
    "Currently installed marketplace plugins.",
)
sandbox_violations_total = registry.counter(
    "umbrella_sandbox_violations_total",
    "Total plugin sandbox violations detected, by kind.",
    label_names=("kind",),
)
security_events_total = registry.counter(
    "umbrella_security_events_total",
    "Total recorded security events, by event_type.",
    label_names=("event_type",),
)
threat_alerts_total = registry.counter(
    "umbrella_threat_alerts_total",
    "Total threat-detection alerts raised, by event_type.",
    label_names=("event_type",),
)


def uptime_seconds() -> float:
    return time.time() - registry.start_time


# Registered lazily so it always reflects "now" rather than being computed
# once at import time.
_uptime_gauge = registry.gauge("umbrella_process_uptime_seconds", "Seconds since this process started.")


def render_exposition() -> str:
    _uptime_gauge.set(uptime_seconds())
    return registry.render()
