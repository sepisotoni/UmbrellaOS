# UmbrellaOS — Phase Status, Corrected (v3 numbering)

Written 2026-08-15, by the head chat working the current
`UMBRELLAOS-FULL-PROJECT-HANDOFF_1.zip` package. Exists because
`phase10/UMBRELLAOS_MASTER_ROADMAP_v3_CONSOLIDATED.md`'s own summary
table (marking Phase 9 and Phase 10 both "not started") directly
contradicts `MASTER-PROJECT-STATUS-AND-HANDOFF.md`'s own phase history
(which describes Phase 9 as closed and Phase 10 as well underway) —
those two docs disagreeing with each other is itself the bug this doc
fixes.

**Confidence key**, so the next session knows what's solid vs. still a
claim:
- ✅ **checked** — I ran a command or read the actual file myself, this
  session, and I'm reporting what it showed.
- 🔶 **partially checked** — some direct evidence, not a full audit
  against the phase's full definition-of-done.
- ❓ **unverified claim** — reported by a cross-chat findings doc, not
  independently checked by a head chat yet. Treat as a pointer, not a
  fact, same as `PROJECT-PRINCIPLES-AND-WORKING-RULES.md` section 4
  requires.

---

| Phase | Theme | Status | Confidence |
|---|---|---|---|
| 0–6 | Platform contract → notification fabric | Done | 🔶 |
| 7 | Public API, SDKs, webhooks, Terraform | Partial | 🔶 |
| 8 | Plugin SDK, sandboxing, marketplace | Partial | 🔶 |
| 9 | Observability & security hardening | **Done** — table below is stale | ✅ |
| 10 | Unified Experience Layer (dashboard rewrite) | Substantially done | ✅ |
| 11 | Multi-node clustering & HA | Not started | ✅ |
| 12 | Platform maturity | Not started | ✅ |

## Phases 0–6 — 🔶

The full backend test suite (838/838, fresh venv, offline install from
`wheels/`) passes, and that suite's coverage spans this range. I
directly read and fixed-scope two specific files in this range
(`services/alt_detection_service.py`, `api/routers/auth.py`) as part of
a separate bug-fix dispatch and confirmed the specific defects reported
there were real. I have **not** done a feature-by-feature audit of
Phases 0–6 against the roadmap's per-phase definition-of-done. The
quality read in `cross-chat-findings/phase0-6_quality_verdict.md` (RBAC
layer, staff service, etc.) is plausible given what I've seen of this
codebase's general style, but is itself an unverified claim as of this
doc — a head chat hasn't independently re-checked it beyond the two
files above.

**Also see `PROJECT-PRINCIPLES-AND-WORKING-RULES.md` decision D2**: this
foundation is carried over from the abandoned first attempt
(`UmbrellaOS.zip`) and is scheduled for independent re-derivation as its
own future dispatch — "done" here means done under the current
carried-over implementation, not done under the post-D2 rebuilt one.

## Phase 7 — 🔶, genuinely partial

Checked directly this session:
- `services/webhooks/`, `capabilities/webhooks.py`, `models/webhook.py`,
  a real migration (`023_webhook_subscriptions.py`), and dedicated test
  files exist. Webhooks are real.
- Searched the whole backend for anything Terraform-related or a
  generated-SDK output directory: **found nothing.** No Terraform
  provider, no generated SDK code anywhere in `umbrella-core-CURRENT/`.

The public REST API + webhook delivery half of this phase is real. The
SDK-generation and Terraform-provider half is not built.

## Phase 8 — 🔶, genuinely partial

Checked directly this session:
- `services/plugins/sandbox.py` and `sandbox_guard.py` exist — real
  sandbox isolation code, and I separately confirmed (while building the
  Phase 10 Tier 2 settings work) that the plugin manifest parsing,
  registration, and marketplace install/uninstall flow are real, tested
  code, not stubs.
- Searched for a plugin debugger, profiler, or sandbox visualizer:
  **found nothing.**

Core SDK/sandbox/marketplace is real and working. The debugger/profiler/
visualizer tooling from the roadmap's Phase 8 scope isn't built.

## Phase 9 — ✅ done, the roadmap table is wrong

Checked directly this session — `api/middleware/` contains real files
for `waf.py`, `metrics.py`, `rate_limit.py`, `tracing.py`, plus
`audit.py`, and `docs/observability/grafana-dashboard.json` exists as a
committed, real config file, not a placeholder. This matches
`MASTER-PROJECT-STATUS-AND-HANDOFF.md`'s own claim (Prometheus metrics,
OpenTelemetry tracing, threat detection, CVE scanner) and directly
contradicts the roadmap doc's summary table. **The roadmap table is
stale — correct it to ✅ done next time someone edits that file.**

## Phase 10 — ✅ substantially done

This is the phase I've done the most direct, hands-on verification on
this session — not just file-existence checks. Fresh `npm install`,
`npm audit` (0 vulnerabilities), `npm run build` (clean, 13 routes),
`npx tsc --noEmit` (clean), `npm run lint` (clean), all run for real
against the current `umbrella-dashboard-CURRENT/`, which now includes a
verified Tier 2 Settings page (steps 0–8 of the roadmap's sequencing are
complete). Backend side: 838/838 tests, `pip check` clean, `pip-audit`
clean.

**What's still actually open, not stale info:**
1. `app/marketplace/page.tsx` — browse/publish/install/uninstall from
   the dashboard itself — is still the step-2 placeholder. Install/
   uninstall currently only works via CLI/API.
2. **Zero manual/browser runtime testing has happened anywhere in this
   phase.** Every check across every step, including this session's, has
   been static (tests, build, lint, audit, tsc). Nobody has clicked
   through the actual running dashboard in a browser yet.

## Phase 11 — ✅ not started

Searched for any cluster/HA-related code: nothing found. Consistent with
every prior doc's claim — not a surprise, just confirmed.

## Phase 12 — ✅ not started

Searched for installer, i18n, feature-flag code: nothing found. Same as
Phase 11 — confirmed, not previously in doubt.
