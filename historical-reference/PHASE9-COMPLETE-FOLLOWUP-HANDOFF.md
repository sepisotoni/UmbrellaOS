# UmbrellaOS — Phase 9 Complete, Follow-Up Handoff

Phase 9 (Observability & Security Hardening, v3 numbering) is done and
**independently re-verified on exact pinned dependencies** — the one gap
every session in this phase flagged (no network access, couldn't confirm
against real pins) is now closed. Use `umbrella-core-PHASE9-COMPLETE.zip`
as your code source.

**Verification performed for this handoff, not inherited from the
building session's word:**
- Applied `phase9-umbrella-core.patch` to a fresh copy of the real
  Phase 8-complete baseline — clean dry-run and real apply, zero fuzz,
  across all 39 changed files.
- Fresh venv, **exact pinned `requirements.txt` — real network access,
  no version drift this time.** Full suite: **783/783 passing.**
- Ran `scripts/scan_dependencies.py` **for real, against live advisory
  data, for the first time in this project's history** — this had never
  actually executed anywhere before, including during Phase 9's own
  building session (no network access there). Result below.

## Immediate priority: 25 real CVEs found on first live scan

```
python-dotenv==1.0.1      1 finding
python-multipart==0.0.19  5 findings
pyjwt==2.7.0               7 findings
pytest==8.3.4               1 finding
starlette==0.41.3          9 findings (BLOCKING under default --fail-on=high)
```

All 25 show `severity: unknown` in the advisory data — confirmed this is
not a scan bug: `_SEVERITY_ORDER` deliberately ranks `unknown` above
`critical`, so missing severity data blocks by default rather than
silently passing. Working as designed.

**Recommended priority order, given what each package is:**
1. **`starlette`** — the framework FastAPI itself sits on. Highest blast
   radius if any of these 9 findings are exploitable in how this app
   actually uses it.
2. **`pyjwt`** — auth-critical; a JWT library vulnerability has an obvious
   direct line to account security.
3. `python-multipart`, `python-dotenv`, `pytest` — lower risk (multipart
   parsing edge cases, a dev-time dependency, and a test-runner
   respectively), but still real findings, still worth clearing.

**This session's job, first:** for each of the 5 packages, find the
oldest version that resolves the known findings (`pip index versions
<pkg>` or check each PYSEC advisory's fixed-version field), bump the pin
in `requirements.txt`, install fresh, run the full suite, confirm 783/783
still holds. **Test after each individual package bump, not all five at
once** — a broken pin should be traceable to one change, not a batch.
Re-run `scripts/scan_dependencies.py` after all five to confirm 0
findings (or document remaining ones with reasoning, if a fix genuinely
isn't available yet for one).

## Phase 9's stated gaps — real scope, not oversights, pick up after the CVE work

1. **OpenTelemetry SDK swap.** `services/tracing_service.py` currently
   implements W3C `traceparent`-format propagation and span-shaped
   structured logging by hand — wire-compatible with real OTel, but not
   the actual SDK (`opentelemetry-sdk` wasn't installable in the building
   session's no-network sandbox). You have real network access now — this
   is a good candidate to actually close: install the real SDK, confirm
   the hand-rolled implementation's wire format really is compatible (or
   fix it if it's not), swap it in. Per that module's own docstring, this
   should be a contained change, not a redesign — verify that claim while
   you're in there rather than just trusting it.
2. **Cross-service tracing (core ↔ daemon ↔ dashboard).** Only core's own
   request path is instrumented — this needs `umbrella-daemon` and
   `umbrella-dashboard` source to finish, same loose end shape as the
   Phase 7→8 Discord/dashboard boundary. Flag if you don't have that
   source; don't guess at the other services' instrumentation points.
3. **Log aggregation across all three services** — same reason, only
   core's own logs land in `log_entries` today.

## Working conventions (unchanged, still binding)

Test after every change, stop at first failure, don't batch — especially
for the dependency bumps, where isolating exactly which pin broke what
matters. Verify claims against real code and real data, the way this
handoff's own CVE scan did rather than trusting a prior session's
no-network caveat as a reason to skip re-checking. Hand back changes as a
diff/manifest package (`patch -p1` instructions), strip
`.env`/`umbrella.db` before zipping even if empty.
