# terraform/provider.tf — Phase 7 completion, Task B.
#
# Mastercard/restapi (community REST provider), not a custom Go provider
# — see README.md's "Why this isn't a real provider" section for the
# full reasoning behind that scoping decision.

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    restapi = {
      source  = "Mastercard/restapi"
      version = "~> 1.19"
    }
  }
}

provider "restapi" {
  uri                  = var.umbrella_api_base_url
  write_returns_object = true

  # Every UmbrellaOS capability — create, read-via-list, update, delete
  # alike — is reached through the same generic
  # `POST /api/v1/capabilities/{name}/invoke` RPC-style path (see
  # registry/adapters/rest.py's module docstring in umbrella-core). This
  # is the concrete consequence of that shape: every HTTP verb this
  # provider would normally vary (GET for read, PUT/PATCH for update,
  # DELETE for destroy) is POST here instead, and what varies per
  # operation is the capability name baked into each resource's
  # `create_path`/`read_path`/`update_path`/`destroy_path` (see
  # webhook_subscriptions.tf, automation_schedules.tf) — not the method.
  create_method  = "POST"
  read_method    = "POST"
  update_method  = "POST"
  destroy_method = "POST"

  headers = {
    "X-Api-Key"    = var.umbrella_api_key
    "Content-Type" = "application/json"
  }
}
