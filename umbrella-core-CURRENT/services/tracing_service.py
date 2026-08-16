"""
services/tracing_service.py — Request-path tracing (Phase 9, item 2:
"OpenTelemetry tracing across core <-> daemon <-> dashboard request
paths"), now backed by the real OpenTelemetry SDK.

**This is a swap-in, done in a follow-up session with real network
access; the original version of this module (Phase 9's building session)
was a hand-rolled shim because `opentelemetry-sdk` wasn't installable in
that session's sandbox.** Its docstring claimed the shim was "wire-format
compatible with real OTel" — that claim was checked here, empirically,
against `opentelemetry-api`/`opentelemetry-sdk` 1.44.0 (installed fresh
from PyPI, not assumed), rather than taken on faith. Result: **mostly
right, with one real gap**, documented below rather than glossed over.

**What was actually verified, and how:**
1. Built a real `TracerProvider`, started a real span, and compared its
   injected `traceparent` header against what the hand-rolled
   `format_traceparent()` would have produced for the same trace/span id
   pair — structurally identical: `version-trace_id(32 hex)-span_id(16
   hex)-flags(2 hex)`.
2. Fed a hand-rolled-style header to the real SDK's
   `TraceContextTextMapPropagator.extract()` and confirmed it parses the
   trace_id/span_id correctly — so a request already in flight through
   this shim would have chained correctly onto a real OTel consumer
   downstream, which was the actual interoperability claim being made.
3. **The one real gap, found by that same comparison, not assumed:** the
   old shim always hardcoded `flags="01"` (sampled). The real SDK's
   default is `03` — sampled (`0x01`) *and* `random-trace-id` (`0x02`),
   the latter being part of the W3C Trace Context **Level 2** spec
   (https://www.w3.org/TR/trace-context-2/#trace-flags), which marks
   whether the trace ID has at least 56 bits of real entropy. The old
   shim's IDs (`secrets.token_hex`) actually qualify for that bit — it
   just never set it, because it was written against Level 1. Not fatal
   (bit 0 is what virtually every consumer actually branches on; other
   bits are specified as forward-compatible/ignorable by parsers that
   don't understand them), but it was a real, verifiable inaccuracy in
   the old docstring's "same wire format" claim, not just a hypothetical
   one — worth recording here since the fix (swapping to the real SDK,
   which sets this correctly on its own) is exactly what this change
   does.

**Two more discrepancies found while verifying the above, unrelated to
wire format, worth flagging since they were stated as fact in the old
docstring and turned out not to match the code:**
- The old docstring claimed "`daemon_client` calls forward the current
  traceparent header as a best effort (see services/daemon_client.py)."
  `services/daemon_client.py` has zero tracing-related code — grepped for
  `trace`/`Trace`, no hits. That forwarding was never actually
  implemented; the docstring described an intent, not a fact. Out of
  scope to add here per this task's own boundary (touching daemon_client
  to *send* a header is core-side only and wouldn't need daemon source,
  but it's still cross-service-tracing-shaped work the handoff explicitly
  scoped out pending daemon source — flagging rather than guessing at
  whether daemon would even do anything useful with it) — noted, not
  silently fixed, not silently left as a false claim either.
- The old docstring's item 3 implied `start_span()` was already in use
  "e.g. [by] the event dispatcher, a plugin sandbox invocation" — grepped
  the whole codebase (app code and tests): zero callers of `start_span`
  anywhere outside this file. It's real, working, tested-by-inspection
  code, just unused today. Kept as-is (still a reasonable tool for a
  future call site to reach for), but the docstring no longer implies
  it's already wired up anywhere.

**What actually changed, mechanically:** the hand-rolled trace/span id
generation, `traceparent` string parsing/formatting, and per-request
contextvars are gone, replaced by a real `TracerProvider` + the SDK's own
`TraceContextTextMapPropagator` for both directions (extracting an
inbound header, injecting an outbound one). `current_trace_id()` /
`current_span_id()` keep their exact old names and signatures — nothing
downstream (`services/log_aggregation_service.py`'s log stamping) needed
to change. `api/middleware/tracing.py` did change (see that file): the
old `start_request_trace()` / `reset_trace()` / `format_traceparent()`
functions are gone, replaced by one context manager
(`request_span()`) plus `inject_traceparent()`, since a real OTel span
needs to be properly entered/exited (not just have contextvars set/reset)
for its duration to be recorded correctly. Confirmed this is genuinely
contained: grepped the whole codebase first — `api/middleware/tracing.py`
was the *only* caller of any of the functions being replaced.

**Export:** still nothing is exported anywhere by default — this project
has no bundled collector, and a `TracerProvider` with zero span
processors is a supported configuration (spans are still created,
`current_trace_id()`/`current_span_id()` still work, log stamping still
works — nothing about in-process behavior depends on export existing).
Set `OTEL_EXPORTER_OTLP_ENDPOINT` (see `config/settings.py`) to point at
a real collector via OTLP/HTTP, `OTEL_CONSOLE_EXPORT=true` to print spans
to stdout for local debugging. This closes the specific gap the old
docstring called out ("the only thing missing is this process exporting
its own spans to a collector via OTLP") — the export path is now real,
just off by default since there's nothing to point it at out of the box.

Scope boundary, unchanged from before: only umbrella-core's own request
path is instrumented. Propagating a *received* traceparent onward to
umbrella-daemon, and umbrella-daemon/-dashboard emitting their own spans
at all, needs daemon/dashboard-side code, which is outside this code
source — same loose end as the Phase 7->8 Discord/dashboard boundary and
the daemon_client gap noted above.
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from config import get_settings

logger = logging.getLogger("umbrella.tracing")

_propagator = TraceContextTextMapPropagator()
_provider_initialized = False


def _init_tracer_provider() -> None:
    """Idempotent: safe to call more than once (e.g. re-imports during
    test collection) — only the first call actually builds a provider.
    Calling `trace.set_tracer_provider()` a second time in the same
    process is a documented no-op in the SDK (it logs a warning and
    keeps the original), so guarding here avoids that noise rather than
    relying on the SDK to swallow it silently."""
    global _provider_initialized
    if _provider_initialized:
        return
    settings = get_settings()
    provider = TracerProvider(resource=Resource.create({"service.name": "umbrella-core"}))

    if settings.otel_exporter_otlp_endpoint:
        # Local import: only needed if an endpoint is actually configured,
        # so a process that never sets one doesn't pay for importing the
        # HTTP exporter's own dependency chain (requests, protobuf codecs).
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint))
        )
    if settings.otel_console_export:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _provider_initialized = True


_init_tracer_provider()
_tracer = trace.get_tracer("umbrella.core")


def current_trace_id() -> str | None:
    """Same name/signature as before the SDK swap — every existing caller
    (services/log_aggregation_service.py) needed no changes."""
    ctx = trace.get_current_span().get_span_context()
    return trace.format_trace_id(ctx.trace_id) if ctx.is_valid else None


def current_span_id() -> str | None:
    ctx = trace.get_current_span().get_span_context()
    return trace.format_span_id(ctx.span_id) if ctx.is_valid else None


@contextmanager
def request_span(incoming_headers):
    """One call per inbound request (api/middleware/tracing.py).
    `incoming_headers` is any mapping-like carrier the propagator can read
    `traceparent`/`tracestate` from (a Starlette `Request.headers` works
    directly). Extracts an existing trace to continue if present, starts a
    real span either way, and makes it the current OTel context for the
    duration of the `with` block — properly ending the span and
    detaching the context on exit, including on an unhandled exception.
    Yields (trace_id, span_id) hex strings for anything that wants them
    directly (e.g. to inject the outbound response header — see
    inject_traceparent below)."""
    parent_ctx = _propagator.extract(incoming_headers)
    token = otel_context.attach(parent_ctx)
    try:
        with _tracer.start_as_current_span("http.request") as span:
            span_ctx = span.get_span_context()
            yield trace.format_trace_id(span_ctx.trace_id), trace.format_span_id(span_ctx.span_id)
    finally:
        otel_context.detach(token)


def inject_traceparent(carrier) -> None:
    """Writes the current span's traceparent (and tracestate, if any)
    into `carrier` (a Starlette `Response.headers` works directly) via
    the same real W3C propagator used for extraction in request_span —
    so an outbound response header round-trips through the exact code
    path a real OTel-instrumented consumer would use, not a hand-rolled
    parallel implementation of it."""
    _propagator.inject(carrier)


@contextmanager
def start_span(name: str):
    """Child span within the current trace/request. API-compatible in
    spirit with `opentelemetry.trace.Tracer.start_as_current_span()`
    because it now *is* that, wrapped with the same start/end debug
    logging the old hand-rolled version had (duration included) for
    parity with existing log-based debugging habits. Not currently called
    anywhere in this codebase — see this module's docstring."""
    parent_span_id = current_span_id()
    start = time.perf_counter()
    with _tracer.start_as_current_span(name) as span:
        span_ctx = span.get_span_context()
        trace_id = trace.format_trace_id(span_ctx.trace_id)
        span_id = trace.format_span_id(span_ctx.span_id)
        logger.debug(
            "span start name=%s trace_id=%s span_id=%s parent_span_id=%s",
            name, trace_id, span_id, parent_span_id,
        )
        try:
            yield span_id
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.debug(
                "span end name=%s trace_id=%s span_id=%s duration_ms=%.2f",
                name, trace_id, span_id, duration_ms,
            )
