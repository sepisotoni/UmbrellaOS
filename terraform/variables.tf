# terraform/variables.tf — Phase 7 completion, Task B.
#
# umbrella_api_key is deliberately NOT given a default and IS marked
# sensitive — the working pattern is `TF_VAR_umbrella_api_key` set in the
# shell environment (or a CI secret), never committed to a .tfvars file.
# See README.md's "Auth" section for the full reasoning and the exact
# scoped-key permissions this config needs.

variable "umbrella_api_base_url" {
  description = "Base URL of the umbrella-core instance, e.g. https://umbrella.example.com (no trailing slash)."
  type        = string
}

variable "umbrella_api_key" {
  description = <<-EOT
    Scoped UmbrellaOS API key (X-Api-Key), created via the
    identity.apikey.create capability. Needs, at minimum:
    webhooks.subscription.view, webhooks.subscription.manage,
    automation.schedule.view, automation.schedule.manage — whichever of
    this config's resource types are actually declared, plus .view so
    Terraform's own search-based read step (see webhook_subscriptions.tf
    and automation_schedules.tf) can list existing rows.
  EOT
  type        = string
  sensitive   = true
}
