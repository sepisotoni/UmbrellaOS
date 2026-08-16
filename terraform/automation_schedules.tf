# terraform/automation_schedules.tf — Phase 7 completion, Task B.
#
# Manages Schedule rows (capabilities/automation.py — "run any existing
# capability on a cron expression"). Picked as the second resource
# because it also has a real stable server-generated id and real
# create/delete, but — unlike webhook subscriptions — its only "update"
# capability (automation.schedule.set_enabled) can toggle `enabled`
# alone; the cron expression, name, and target capability/params are
# create-only. Modeled here with `force_new` on those fields so Terraform
# does the honest thing (replace, not silently no-op an unsupported
# in-place update) if a plan ever tries to change one.

resource "restapi_object" "example_schedule" {
  path = "/api/v1/capabilities/automation.schedule.create/invoke"

  create_path   = "/api/v1/capabilities/automation.schedule.create/invoke"
  create_method = "POST"

  # Same "no get-by-id, only list" shape as webhook subscriptions — see
  # webhook_subscriptions.tf's module docstring and README.md's "A real
  # limitation found while scoping this" for the full explanation. This
  # is a pattern across every candidate capability set this dispatch
  # checked (marketplace installs and settings both have the same gap),
  # not specific to schedules.
  read_path   = "/api/v1/capabilities/automation.schedule.list/invoke"
  read_method = "POST"

  # automation.schedule.set_enabled only ever toggles `enabled` — see
  # capabilities/automation.py::SetScheduleEnabledParams. Anything else
  # in `data` changing must force a real replace, not a silent partial
  # update the backend doesn't actually support.
  update_path   = "/api/v1/capabilities/automation.schedule.set_enabled/invoke"
  update_method = "POST"

  destroy_path   = "/api/v1/capabilities/automation.schedule.delete/invoke"
  destroy_method = "POST"

  id_attribute = "id"

  # automation.schedule.create's params (see
  # capabilities/automation.py::CreateScheduleParams).
  data = jsonencode({
    name              = "example-nightly-backup-reconcile"
    cron_expression   = "0 3 * * *"
    capability_name   = "hosting.fleet.reconcile"
    capability_params = {}
  })

  # Only `enabled` is a real, backend-supported in-place update.
  update_data = jsonencode({
    enabled = true
  })

  # name/cron_expression/capability_name/capability_params have no
  # update capability at all (see module docstring) — changing any of
  # them in `data` must destroy+recreate, not silently no-op.
  force_new = ["name", "cron_expression", "capability_name", "capability_params"]

  # See webhook_subscriptions.tf's destroy_data comment — same
  # unverified `{id}` body-templating caveat applies here.
  destroy_data = jsonencode({
    schedule_id = "{id}"
  })

  read_search = {
    search_key   = "id"
    search_value = ""
    results_key  = ""
  }
}

output "example_schedule_id" {
  value       = restapi_object.example_schedule.id
  description = "Server-generated id of the example-managed automation schedule."
}
