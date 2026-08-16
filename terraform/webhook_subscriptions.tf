# terraform/webhook_subscriptions.tf — Phase 7 completion, Task B.
#
# Manages WebhookSubscription rows via capabilities/webhooks.py's four
# capabilities (webhooks.subscription.create/list/update/delete — see
# umbrella-core's capabilities/webhooks.py). Chosen as the primary
# resource for this dispatch because it's the cleanest real fit: a
# stable server-generated id (subscription.id), and idempotent
# create/delete with a real update capability — see README.md's
# "Why webhook subscriptions" for the full comparison against the other
# candidates this dispatch considered and rejected.
#
# Read-shape caveat, stated plainly (see README.md's "A real limitation
# found while scoping this" section for the full explanation): there is
# no `webhooks.subscription.get`-by-id capability, only
# `webhooks.subscription.list` (optionally filtered by topic). This
# resource's `read_search` block works around that by searching the list
# response for the row matching `object_id`, rather than the provider's
# more common GET-by-id-path read. This is a real, load-bearing part of
# making this resource work against UmbrellaOS's actual capability
# shape, not a stylistic choice.

resource "restapi_object" "example_subscription" {
  path = "/api/v1/capabilities/webhooks.subscription.create/invoke"

  create_path = "/api/v1/capabilities/webhooks.subscription.create/invoke"
  create_method = "POST"

  # No get-by-id capability exists (see module docstring above) — list
  # and search client-side for the row whose "id" matches this resource's
  # object_id instead of hitting a per-id read path.
  read_path   = "/api/v1/capabilities/webhooks.subscription.list/invoke"
  read_method = "POST"

  update_path   = "/api/v1/capabilities/webhooks.subscription.update/invoke"
  update_method = "POST"

  destroy_path   = "/api/v1/capabilities/webhooks.subscription.delete/invoke"
  destroy_method = "POST"

  id_attribute = "id"

  # webhooks.subscription.create's params (see
  # capabilities/webhooks.py::CreateWebhookSubscriptionParams): topic + url.
  data = jsonencode({
    topic = "hosting.server.crashed"
    url   = "https://ops.example.com/hooks/umbrella-crash-alert"
  })

  # webhooks.subscription.update accepts a partial body
  # (UpdateWebhookSubscriptionParams: subscription_id, url?, active?) —
  # subscription_id is threaded in via object_id/id_attribute
  # automatically by the provider, not repeated in update_data.
  update_data = jsonencode({
    active = true
  })

  # webhooks.subscription.delete's param name doesn't match id_attribute
  # ("subscription_id", not "id") — destroy_data supplies it explicitly,
  # using the provider's documented `{id}` path-templating token, since
  # the provider can't infer a differently-named field on its own. NOT
  # independently confirmed that `{id}` substitution also applies inside
  # a data/destroy_data JSON body (vs. only in path strings) — see
  # README.md's "What's NOT verified here"; re-check against the
  # provider's own docs during a real `terraform init` before relying on
  # this in production.
  destroy_data = jsonencode({
    subscription_id = "{id}"
  })

  # Search-based read: webhooks.subscription.list has no query params
  # narrowing to a single id, so this searches the full (optionally
  # topic-filtered) list response for the entry whose "id" field equals
  # this resource's tracked id. See README.md's "A real limitation found
  # while scoping this" — this block's exact argument names should be
  # re-verified against the provider's own docs during a real `terraform
  # init` (registry.terraform.io wasn't reachable from this dispatch's
  # sandbox — see README.md's "What's NOT verified here").
  read_search = {
    search_key   = "id"
    search_value = ""
    results_key  = ""
  }
}

output "example_subscription_id" {
  value       = restapi_object.example_subscription.id
  description = "Server-generated id of the example-managed webhook subscription."
}
