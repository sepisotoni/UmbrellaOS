"""tests/registry/test_plugin_manifest.py — PluginManifest structural validation."""
import pytest

from services.plugins.manifest import ManifestValidationError, parse_manifest


def _base_manifest(**overrides) -> dict:
    manifest = {
        "schema_version": 1,
        "plugin_id": "queue-tools",
        "name": "Queue Tools",
        "version": "1.0.0",
        "author": "example-author",
        "description": "Reports queue depth.",
        "storage": "kv",
        "capabilities": [
            {
                "local_name": "queue_status",
                "summary": "Report current queue depth.",
                "entrypoint": "handlers:queue_status",
                "params": {"target_user_id": {"type": "string", "required": False}},
                "result": {"queue_depth": {"type": "integer"}},
                "required_permission": "queue.read",
            }
        ],
        "discord_commands": [
            {"name": "queue-status", "description": "Show queue depth.", "capability": "queue_status"}
        ],
        "dashboard_ui_slots": [
            {"slot": "sidebar.tools", "label": "Queue Tools", "capability": "queue_status"}
        ],
    }
    manifest.update(overrides)
    return manifest


def test_valid_manifest_parses():
    manifest = parse_manifest(_base_manifest())
    assert manifest.plugin_id == "queue-tools"
    assert manifest.capabilities[0].local_name == "queue_status"
    assert manifest.storage == "kv"


def test_default_storage_is_kv():
    raw = _base_manifest()
    del raw["storage"]
    manifest = parse_manifest(raw)
    assert manifest.storage == "kv"


def test_sqlite_storage_accepted():
    manifest = parse_manifest(_base_manifest(storage="sqlite"))
    assert manifest.storage == "sqlite"


@pytest.mark.parametrize("bad_id", ["Queue-Tools", "qt", "-queuetools", "queue tools", "queue.tools"])
def test_invalid_plugin_id_rejected(bad_id):
    with pytest.raises(ManifestValidationError):
        parse_manifest(_base_manifest(plugin_id=bad_id))


@pytest.mark.parametrize("bad_version", ["1.0", "v1.0.0", "1.0.0.0", "latest"])
def test_invalid_version_rejected(bad_version):
    with pytest.raises(ManifestValidationError):
        parse_manifest(_base_manifest(version=bad_version))


def test_unsupported_schema_version_rejected():
    with pytest.raises(ManifestValidationError):
        parse_manifest(_base_manifest(schema_version=2))


def test_unsupported_storage_mode_rejected():
    with pytest.raises(ManifestValidationError):
        parse_manifest(_base_manifest(storage="filesystem"))


def test_local_name_with_dot_rejected():
    """This is the specific namespace-spoofing guard: a plugin must not be
    able to declare a local_name that reaches into another plugin's (or
    core's) namespace once the 'plugin.<id>.' prefix is prepended."""
    raw = _base_manifest()
    raw["capabilities"][0]["local_name"] = "other_plugin.foo"
    raw["discord_commands"][0]["capability"] = "other_plugin.foo"
    raw["dashboard_ui_slots"][0]["capability"] = "other_plugin.foo"
    with pytest.raises(ManifestValidationError):
        parse_manifest(raw)


def test_duplicate_local_names_rejected():
    raw = _base_manifest()
    raw["capabilities"].append(dict(raw["capabilities"][0]))
    with pytest.raises(ManifestValidationError):
        parse_manifest(raw)


def test_discord_command_referencing_unknown_capability_rejected():
    raw = _base_manifest()
    raw["discord_commands"][0]["capability"] = "does_not_exist"
    with pytest.raises(ManifestValidationError):
        parse_manifest(raw)


def test_dashboard_slot_referencing_unknown_capability_rejected():
    raw = _base_manifest()
    raw["dashboard_ui_slots"][0]["capability"] = "does_not_exist"
    with pytest.raises(ManifestValidationError):
        parse_manifest(raw)


def test_unknown_dashboard_slot_name_rejected():
    raw = _base_manifest()
    raw["dashboard_ui_slots"][0]["slot"] = "totally_made_up_slot"
    with pytest.raises(ManifestValidationError):
        parse_manifest(raw)


def test_unsupported_param_type_rejected():
    raw = _base_manifest()
    raw["capabilities"][0]["params"]["nested"] = {"type": "object"}
    with pytest.raises(ManifestValidationError):
        parse_manifest(raw)


@pytest.mark.parametrize("bad_entrypoint", ["handlers", "handlers:", ":func", "a:b:c"])
def test_malformed_entrypoint_rejected(bad_entrypoint):
    raw = _base_manifest()
    raw["capabilities"][0]["entrypoint"] = bad_entrypoint
    with pytest.raises(ManifestValidationError):
        parse_manifest(raw)


def test_manifest_with_no_capabilities_is_valid():
    """A manifest declaring only e.g. a dashboard static asset with no
    capability at all isn't a case this schema needs to forbid — it's just
    an empty capabilities list."""
    raw = _base_manifest()
    raw["capabilities"] = []
    raw["discord_commands"] = []
    raw["dashboard_ui_slots"] = []
    manifest = parse_manifest(raw)
    assert manifest.capabilities == []


# --- Phase 10, Decision 7: render_as widget-shape signal -----------------


def test_dashboard_slot_render_as_omitted_defaults_to_none():
    """Plugins written before render_as existed, or that don't care to be
    explicit, must still parse — the dashboard falls back to shape-based
    inference in that case, not a validation error."""
    manifest = parse_manifest(_base_manifest())
    assert manifest.dashboard_ui_slots[0].render_as is None


@pytest.mark.parametrize("shape", ["stat_pair", "status_badge", "simple_list"])
def test_dashboard_slot_render_as_accepts_allowed_shapes(shape):
    raw = _base_manifest()
    raw["dashboard_ui_slots"][0]["render_as"] = shape
    manifest = parse_manifest(raw)
    assert manifest.dashboard_ui_slots[0].render_as == shape


def test_dashboard_slot_render_as_rejects_unknown_shape():
    raw = _base_manifest()
    raw["dashboard_ui_slots"][0]["render_as"] = "pie_chart"
    with pytest.raises(ManifestValidationError):
        parse_manifest(raw)


def test_dashboard_slot_render_as_rejects_table_for_now():
    """table is reserved for Tier 3 (plugin-owned pages) — Tier 1 widget
    slots don't get it yet, per DASHBOARD-PLUGIN-UI-SCOPING.md."""
    raw = _base_manifest()
    raw["dashboard_ui_slots"][0]["render_as"] = "table"
    with pytest.raises(ManifestValidationError):
        parse_manifest(raw)


# --- Phase 10, Tier 3: plugin-owned pages ---------------------------------


def _with_page(**page_overrides) -> dict:
    raw = _base_manifest()
    raw["page"] = {
        "nav_label": "Queue Tools",
        "nav_icon": "list",
        "widgets": [
            {"label": "Queue depth", "capability": "queue_status", "render_as": "stat_pair"}
        ],
    }
    raw["page"].update(page_overrides)
    return raw


def test_page_omitted_defaults_to_none():
    """Strictly opt-in (Tier 3's confirmed default): a manifest that
    doesn't declare a page must still parse cleanly with page=None, not
    an empty placeholder page."""
    manifest = parse_manifest(_base_manifest())
    assert manifest.page is None


def test_page_with_valid_widget_parses():
    manifest = parse_manifest(_with_page())
    assert manifest.page is not None
    assert manifest.page.nav_label == "Queue Tools"
    assert manifest.page.nav_icon == "list"
    assert manifest.page.widgets[0].capability == "queue_status"
    assert manifest.page.widgets[0].render_as == "stat_pair"


def test_page_widget_render_as_omitted_defaults_to_none():
    raw = _with_page()
    del raw["page"]["widgets"][0]["render_as"]
    manifest = parse_manifest(raw)
    assert manifest.page.widgets[0].render_as is None


@pytest.mark.parametrize("shape", ["stat_pair", "status_badge", "simple_list", "table"])
def test_page_widget_render_as_accepts_table_unlike_tier1(shape):
    """The one real difference from Tier 1's vocabulary — a page widget
    can be a table, a dashboard slot widget currently cannot."""
    raw = _with_page()
    raw["page"]["widgets"][0]["render_as"] = shape
    manifest = parse_manifest(raw)
    assert manifest.page.widgets[0].render_as == shape


def test_page_widget_render_as_rejects_unknown_shape():
    raw = _with_page()
    raw["page"]["widgets"][0]["render_as"] = "pie_chart"
    with pytest.raises(ManifestValidationError):
        parse_manifest(raw)


def test_page_rejects_unknown_nav_icon():
    with pytest.raises(ManifestValidationError):
        parse_manifest(_with_page(nav_icon="rocket"))


def test_page_rejects_empty_widgets_list():
    """A page with no content isn't a real page — omit `page` entirely
    instead of declaring one with nothing in it."""
    raw = _with_page()
    raw["page"]["widgets"] = []
    with pytest.raises(ManifestValidationError):
        parse_manifest(raw)


def test_page_widget_capability_must_reference_declared_capability():
    raw = _with_page()
    raw["page"]["widgets"][0]["capability"] = "nonexistent_capability"
    with pytest.raises(ManifestValidationError):
        parse_manifest(raw)


def test_page_widgets_render_in_declared_order():
    raw = _base_manifest()
    raw["capabilities"].append(
        {
            "local_name": "queue_history",
            "summary": "Recent queue events.",
            "entrypoint": "handlers:queue_history",
            "result": {},
            "required_permission": "queue.read",
        }
    )
    raw["page"] = {
        "nav_label": "Queue Tools",
        "nav_icon": "list",
        "widgets": [
            {"label": "History", "capability": "queue_history", "render_as": "table"},
            {"label": "Depth", "capability": "queue_status", "render_as": "stat_pair"},
        ],
    }
    manifest = parse_manifest(raw)
    assert [w.label for w in manifest.page.widgets] == ["History", "Depth"]


# --- Phase 10, Tier 2 (Decision 2 Option A): config_fields ----------------


def test_manifest_with_no_config_fields_is_valid():
    """Strictly opt-in, same as `page` — most plugins have no config."""
    manifest = parse_manifest(_base_manifest())
    assert manifest.config_fields == []


def test_config_field_boolean_accepted():
    raw = _base_manifest()
    raw["config_fields"] = [
        {"key": "auto_purge", "type": "boolean", "label": "Auto-purge stale entries", "default_value": False},
    ]
    manifest = parse_manifest(raw)
    assert manifest.config_fields[0].key == "auto_purge"
    assert manifest.config_fields[0].default_value is False


def test_config_field_unsupported_type_rejected():
    """Tier 2's starting scope is boolean-only — text/number are a
    deliberate non-goal until real plugin demand exists."""
    raw = _base_manifest()
    raw["config_fields"] = [
        {"key": "max_items", "type": "integer", "label": "Max items", "default_value": True},
    ]
    with pytest.raises(ManifestValidationError):
        parse_manifest(raw)


def test_config_field_bad_key_shape_rejected():
    raw = _base_manifest()
    raw["config_fields"] = [
        {"key": "Not-A-Valid-Key!", "type": "boolean", "label": "x", "default_value": False},
    ]
    with pytest.raises(ManifestValidationError):
        parse_manifest(raw)


def test_config_field_duplicate_keys_rejected():
    raw = _base_manifest()
    raw["config_fields"] = [
        {"key": "auto_purge", "type": "boolean", "label": "A", "default_value": False},
        {"key": "auto_purge", "type": "boolean", "label": "B", "default_value": True},
    ]
    with pytest.raises(ManifestValidationError):
        parse_manifest(raw)


def test_config_field_key_does_not_need_to_reference_a_capability():
    """Unlike dashboard_ui_slots/page.widgets, config_fields.key names a kv
    storage slot, not a capability — no cross-reference check should apply
    (this would previously have needed a matching capabilities[].local_name
    if it were treated the same as the other declaration lists)."""
    raw = _base_manifest()
    raw["config_fields"] = [
        {"key": "totally_unrelated_to_any_capability", "type": "boolean", "label": "x", "default_value": False},
    ]
    manifest = parse_manifest(raw)
    assert manifest.config_fields[0].key == "totally_unrelated_to_any_capability"
