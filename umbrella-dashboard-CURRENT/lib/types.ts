// lib/types.ts — types mirroring umbrella-core's real response shapes.
//
// `User` / `Session` mirror api/routers/auth.py::UserSchema.
// `DashboardSlot` mirrors capabilities/marketplace.py::DashboardSlotResult
// as LIVE-VERIFIED in step 0 (handback/STEP0-MARKETPLACE-SHAPE-VERIFICATION.md),
// not as DASHBOARD-PLUGIN-UI-SCOPING.md assumed — notably `capability_name`,
// not `capability`, and `plugin_id` is present.

export type User = {
  id: string;
  discord_id: string;
  username: string;
  email: string | null;
  role_id: string | null;
  role: string | null;
  permissions: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type Session = {
  token: string;
  user: User;
  expires_in: number;
};

// Tier 1 widget-shape vocabulary (Phase 10 Decision 1 / Decision 7).
// "table" is reserved for Tier 3 (step 7) but included now since it's
// already part of the locked vocabulary in the core schema.
export type RenderAs = "stat_pair" | "status_badge" | "simple_list" | "table" | null;

export type DashboardSlotName = "sidebar.tools" | "sidebar.moderation" | "dashboard.widgets";

export type DashboardSlot = {
  plugin_id: string;
  slot: DashboardSlotName;
  label: string;
  capability_name: string;
  render_as: RenderAs;
};

export type PluginInstall = {
  plugin_id: string;
  installed_version: string;
  registered_capability_names: string[];
};

// Phase 10 step 6 — mirrors capabilities/dashboard_layout.py's
// LayoutWidgetEntry / DashboardLayoutResult exactly. `widget_key` is the
// same "{plugin_id}:{capability_name}" composite already used as the React
// key in components/widgets/widget-grid.tsx (step 3) — no new identity
// concept invented for matching a saved entry back to a live DashboardSlot.
export type CustomizablePageId = "dashboard";

export type LayoutWidgetEntry = {
  widget_key: string;
  visible: boolean;
};

export type DashboardLayoutResult = {
  page_id: string;
  // null = no saved layout — caller falls back to the page's default
  // arrangement (registration order, all visible). Distinct from an empty
  // array, which is a saved layout with everything explicitly hidden.
  widgets: LayoutWidgetEntry[] | null;
};

// Phase 10, Tier 3 — mirrors capabilities/marketplace.py's PageWidgetResult
// / PageNavResult / PageLayoutResult exactly. A page widget is
// structurally the same idea as DashboardSlot (label + render_as) minus
// slot/plugin_id, which is why components/widgets/plugin-widget.tsx's
// dispatcher accepts either via a shared minimal shape rather than two
// parallel renderers.
export type PageWidget = {
  label: string;
  capability_name: string;
  render_as: RenderAs;
};

export type PageNav = {
  plugin_id: string;
  nav_label: string;
  nav_icon: string;
};

export type PageLayout = {
  plugin_id: string;
  nav_label: string;
  nav_icon: string;
  widgets: PageWidget[];
};

// Phase 10, Tier 2 (Decision 2, Option A) — mirrors
// capabilities/marketplace.py's ConfigurablePluginResult and
// services/plugins/registration.py's ConfigFieldValue/ConfigGetResult
// exactly. Tier 2's starting scope is boolean-only (see registration.py's
// _make_config_set_handler), so `value`/`type` are narrowed to boolean
// here rather than the broader `unknown` PageWidget-style shapes use —
// widen this if a future phase adds non-boolean config field types.
export type ConfigurablePlugin = {
  plugin_id: string;
  plugin_name: string;
  field_count: number;
};

export type ConfigFieldValue = {
  key: string;
  label: string;
  type: "boolean";
  value: boolean;
};

export type ConfigGetResult = {
  values: ConfigFieldValue[];
};

// Phase 10 completion, Task A — mirrors capabilities/marketplace.py's
// PluginListingResult / PluginVersionResult / PluginInstallResult exactly
// (read the full result-model definitions there, not just field names,
// before changing this). `PluginInstall` above already covers the
// install-list shape (registered_capability_names included) — reused
// here rather than duplicated.
export type PluginListing = {
  plugin_id: string;
  name: string;
  author: string;
  description: string;
  latest_version: string;
};

export type PluginVersion = {
  plugin_id: string;
  version: string;
  sha256_hash: string;
  published_at: string;
};
