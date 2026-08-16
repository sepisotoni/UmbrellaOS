# UmbrellaOS — Sub-chat dispatch: Phase 7 completion (SDK + Terraform)

Read this, then `PROJECT-PRINCIPLES-AND-WORKING-RULES.md`, then
`MASTER-PROJECT-STATUS-AND-HANDOFF.md`. **Session label:
`subchat-phase7-completion`.**

Phase 7's public API + webhooks are already done (see
`PHASE-STATUS-CORRECTED.md`). Two things are missing: generated SDK code
and a Terraform provider. This dispatch is both, scoped deliberately
smaller than "build a real HashiCorp provider" — see the reasoning
below, this was an explicit decision, not a corner cut.

## Task A — Generated TypeScript SDK

`main.app.openapi()` (in `umbrella-core-CURRENT/main.py`) already
produces a complete OpenAPI schema — `/openapi.json` stays reachable
even with `docs_url`/`redoc_url` disabled in production (only those two
are gated on `settings.debug`, not `openapi_url`). You don't need a
running server to generate from it: write a small script that imports
`main.app` directly and dumps `app.openapi()` to a file, then feed that
into a real generator.

1. **Schema export script** (`umbrella-core-CURRENT/scripts/export_openapi_schema.py`
   or similar) — imports the app, writes `openapi.json`. Check it runs
   clean against a fresh venv before building anything on top of it.
2. **SDK generation** — use `openapi-typescript` (generates types) plus
   a thin typed-fetch wrapper, or `openapi-generator-cli` targeting
   `typescript-fetch` if you'd rather have a fuller generated client —
   your call, state which and why. Output goes in a new top-level
   package, e.g. `umbrella-sdk-ts/`, with its own `package.json` (name it
   something like `@umbrellaos/sdk`), README showing real usage
   (authenticate, call a capability via
   `POST /api/v1/capabilities/{name}/invoke` — check
   `api/routers/audit.py`'s docstring for how that generic invoke path
   works, it's the same for every capability, not just audit).
3. **This SDK is for external consumers of the public API** — don't wire
   the dashboard (`umbrella-dashboard-CURRENT/`) to use it instead of its
   own hand-written `lib/api.ts`. That's a real, separate migration with
   its own risk (the dashboard's fetch wrappers have grown their own
   conventions — session cookie handling, `ApiError` typing — that a
   generic SDK won't replicate for free) and is explicitly out of scope
   here. Flag it as a future option in your handback, don't do it.
4. **Verification:** the SDK needs its own build/typecheck — `tsc
   --noEmit` on the generated package at minimum. If you can, write one
   real integration test against a running local backend (fresh venv,
   `uvicorn main:app`) calling one real capability end-to-end through the
   generated client — that's the actual proof the SDK works, not just
   that it type-checks.

## Task B — REST-backed Terraform config (deliberately not a custom provider)

**Scoping decision, explicit, not a guess:** a real registry-quality
Terraform provider is normally written in Go against HashiCorp's
provider framework — genuinely weeks of work (new toolchain, acceptance
testing, versioning, registry publishing) for a single-developer project
with zero existing Terraform footprint. Head chat and Sepiso Toni agreed
explicitly to scope this down: **a working Terraform configuration using
a generic REST/HTTP provider** (e.g. Terraform's own `http` data source
for reads, or the community `Mastercard/restapi` provider for full
CRUD), wired against the same generic
`POST /api/v1/capabilities/{name}/invoke` path Task A's SDK uses. If a
custom Go provider is ever wanted later, this is a much smaller upgrade
from "a working REST config" than from nothing — don't build the Go
provider now, that's out of scope even if it seems like the "more
correct" answer.

1. Pick 2–3 real, meaningful resources to manage declaratively — good
   candidates: plugin install/uninstall (`marketplace.install.install`/
   `.uninstall`/`.list` — you've seen this exact capability set before,
   `dispatches/PHASE10-COMPLETION/` built the dashboard UI for it),
   settings values (`api/routers/settings.py`), webhook subscriptions
   (`capabilities/webhooks.py`). Read the actual capability
   params/results before picking — a resource needs a stable identifier
   and idempotent create/read/delete to map cleanly to Terraform's model,
   not every capability will fit that shape well. State which you picked
   and why one you considered *didn't* fit.
2. Write real `.tf` files demonstrating it — `terraform plan`/`apply`
   against a running local backend, not just written and never run.
   Document the auth story (how does the REST provider send the bearer
   token — a `TF_VAR_` env var, almost certainly, not hardcoded).
3. A README under `terraform/` explaining what's managed, what isn't,
   and the explicit "this is REST-backed, not a real provider" framing
   from above — someone reading this later shouldn't think it's more
   than it is.

## What NOT to do

- No custom Go Terraform provider (see Task B's framing).
- No dashboard migration to the new SDK (see Task A point 3).
- No backend capability changes — everything here reads/wraps existing,
  already-tested capabilities. If you find yourself wanting to add or
  modify a capability, stop and flag it (rule 2.2), don't just do it.

## Verification

Standard loop for whatever you touch. Backend unaffected — confirm
844/844 still passes (rule 2.1, don't assume "I didn't touch it" means
"still green"). Leak-check before every commit, not just before
handback — this project's git history has already had two real
mistakes this session from insufficiently scoped `git add`, don't be a
third.

## What to hand back

A handback doc (model: `phase10/handback/STEP9-MARKETPLACE-UI-AND-FIRST-TEST-PASS.md`
or the closeout dispatch's `HANDBACK-PHASE10-CLOSEOUT.md` — both are
good examples of stating real gaps honestly instead of rounding up), a
`git format-patch` diff (same format the last dispatch used — applies
cleanly with `git am`, preserves your commit's real authorship instead
of being squashed). Commit under `subchat-phase7-completion`.
