# UmbrellaOS — Terraform config (REST-backed, not a real provider)

Phase 7 completion, Task B. Read `PROJECT-PRINCIPLES-AND-WORKING-RULES.md`
and `dispatches/PHASE7-COMPLETION/SUBCHAT-HANDOFF-PHASE7-COMPLETION.md`
first if you haven't — this doc assumes that context.

## What this is, and isn't

This is a working Terraform configuration against UmbrellaOS's real REST
API, using the community
[`Mastercard/restapi`](https://registry.terraform.io/providers/Mastercard/restapi)
provider — **not** a real, registry-published HashiCorp-style Terraform
provider written in Go. That was an explicit, stated scoping decision
(head chat + Sepiso Toni, see the dispatch doc's Task B framing), not a
corner cut: a real provider is genuinely weeks of Go-toolchain work for a
single-developer project with zero existing Terraform footprint, and this
REST-backed config is a much smaller upgrade path to a real provider
later than starting from nothing.

If someone finds this later and it looks like "just Terraform files,"
that's correct — it is. Don't read more into it.

## What's managed

Two resource types, each mapped to a real, tested capability set:

- **Webhook subscriptions** (`webhook_subscriptions.tf`) —
  `webhooks.subscription.create/list/update/delete`
  (`capabilities/webhooks.py`). Full CRUD.
- **Automation schedules** (`automation_schedules.tf`) —
  `automation.schedule.create/list/set_enabled/delete`
  (`capabilities/automation.py`). Create/read/delete are real; "update"
  is limited to the `enabled` toggle only (see that file's own comments
  and `force_new` list) — changing the cron expression, name, or target
  capability requires a real replace, not an in-place update, because
  the backend has no capability to do that in-place update at all.

### Why webhook subscriptions and automation schedules

The dispatch doc suggested three candidates: plugin installs
(`marketplace.install.*`), settings (`api/routers/settings.py`), and
webhook subscriptions. I added automation schedules as a fourth
candidate and picked two of the four:

- **Webhook subscriptions — picked.** Real server-generated `id`,
  idempotent create/delete, and (unlike every other candidate here) a
  real partial-update capability
  (`webhooks.subscription.update`, url/active). Cleanest fit to
  Terraform's resource model of the four.
- **Automation schedules — picked, with the update caveat above.** Also
  a real server-generated `id` and real create/delete. Added because
  plugin installs (below) turned out to have a real precondition problem
  that made it a worse first example than I'd assumed going in.
- **Marketplace plugin installs — considered, not picked.** The
  `marketplace.install.install` capability (`capabilities/marketplace.py`)
  needs a `plugin_id` + `version` that's already been *published*
  (`marketplace.listing.publish`, which itself needs a real plugin zip
  — `PublishListingParams` takes a base64-encoded zip blob). A Terraform
  example resource here would either need to also declare a
  `marketplace.listing.publish` step with a real fixture plugin package
  checked into this repo (out of scope — this dispatch doesn't touch
  plugin packaging), or document "assumes a plugin is already published"
  as an untested precondition. Neither felt like a real, runnable
  example, so this candidate is documented here rather than built.
- **Settings — considered, not picked, same as the dispatch doc's own
  reasoning.** `api/routers/settings.py`'s endpoints require
  `require_owner` (session or admin-key auth) — they are **not**
  capabilities, so they're not reachable through the
  `POST /api/v1/capabilities/{name}/invoke` + `X-Api-Key` path this
  entire Task B config is built around. Managing settings via Terraform
  would need either a real capability wrapper around
  `SettingsService` (a backend change, explicitly out of scope per the
  dispatch's "What NOT to do") or session-cookie auth wired into the
  REST provider (a materially different, more fragile auth story than
  a scoped API key). Out of scope, not a gap.

## A real limitation found while scoping this

**Every candidate capability set here has the same shape: create, list,
update-if-any, delete — but no `get`-by-single-id.** Checked directly:
`webhooks.subscription.*`, `automation.schedule.*`, and
`marketplace.install.*` (`list_installed`) all expose `list` (optionally
filtered) as the only read operation, never a `.get(id)`. This isn't
specific to the two resources this config manages — it's uniform across
the capability sets I checked, which suggests it's a real pattern in how
this codebase's domains are designed (list-first, no assumption that a
caller already has an id to look up directly), not an oversight in any
one of them. Worth flagging to Sepiso Toni rather than silently working
around it forever: **if this API grows more Terraform-managed resource
types later, a real `get`-by-id capability per resource would make this
config (and any future one) meaningfully more robust** — this is
exactly the kind of design decision rule 2.2 says to surface rather than
paper over.

The workaround here (`read_search` in both `.tf` files) uses the
`Mastercard/restapi` provider's search-based read: hit the list endpoint,
search the response for the row whose `id` matches this resource's
tracked id. It's real and I traced through the exact HTTP calls it
implies by hand (see "What IS verified here" below) — but see the next
section for what's still open about it.

## What's NOT verified here — stated plainly, not rounded up

**`terraform plan` / `terraform apply` were never run against a live
backend.** The Terraform CLI binary itself could not be installed in
this dispatch's sandbox — network egress is allowlisted to a fixed set
of domains (package registries: PyPI, npm, crates.io, GitHub; no
`releases.hashicorp.com`, no `registry.terraform.io`), and neither `apt`
nor any reachable package registry had a usable `terraform` binary. I
confirmed this directly (tried `apt-cache search terraform`, `npm view
terraform-bin`) rather than assuming it — see this dispatch's handback
doc for the exact commands. This is a real, sandbox-specific constraint,
not a "didn't get to it."

Concretely, still open, in order of how much they matter:

1. **The provider itself was never installed or exercised.** `terraform
   init` was never run. The `required_providers` block's version
   constraint (`~> 1.19`) is a reasonable current guess, not confirmed
   against the actual registry.
2. **The `read_search` block's exact argument names
   (`search_key`/`search_value`/`results_key`) are written from memory
   of this provider's general shape, not confirmed against its current
   docs** (`registry.terraform.io` wasn't reachable to check). This is
   the single most likely thing to need a real fix on first `terraform
   init`/`plan`.
3. **Whether `{id}` templating works inside a `data`/`destroy_data` JSON
   body (not just inside `*_path` strings) is unconfirmed** — see the
   inline comments on both `.tf` files' `destroy_data` blocks. If it
   doesn't, `destroy_data`'s `subscription_id`/`schedule_id` fields will
   need a different mechanism (a provisioner, or restructuring which
   value the provider's `object_id` tracks).
4. **HCL syntax only, not semantics, was checked** — via
   `terraform-config-inspect` (available through `apt`, unlike the real
   `terraform` binary), which confirmed the files parse as valid HCL
   with the variables/resources/outputs shape shown above. It does not
   validate against the actual provider schema.

### What IS verified here

Every HTTP call each `.tf` resource's lifecycle would make — create,
list-and-search, update, destroy — for both webhook subscriptions and
automation schedules, run by hand via `curl` against a real local
umbrella-core instance (fresh SQLite DB, real `identity.apikey.create`
scoped key, same as this dispatch's SDK integration test in
`umbrella-sdk-ts/`). Every step returned the expected shape, including
the search-based read finding the right row by id in the list response.
See the handback doc for the full transcript. This confirms the
*backend* side of this config is real and works; it's specifically the
*Terraform/provider* side (items 1–3 above) that's unverified.

## Auth

`TF_VAR_umbrella_api_key`, set in the environment, never committed —
matching this project's existing convention
(`PROJECT-PRINCIPLES-AND-WORKING-RULES.md` D5's PAT handling is the same
shape). Create the key first via `identity.apikey.create` with the
`webhooks.subscription.*` and `automation.schedule.*` permissions listed
in `variables.tf`. Not a session cookie, not the admin-key bootstrap tier
— a real scoped key is the only auth mode this config (or the SDK in
`umbrella-sdk-ts/`) supports, deliberately (see that package's README for
the same point made about the SDK).

```bash
export TF_VAR_umbrella_api_base_url="https://umbrella.example.com"
export TF_VAR_umbrella_api_key="umbr_..."
terraform init
terraform plan
```
