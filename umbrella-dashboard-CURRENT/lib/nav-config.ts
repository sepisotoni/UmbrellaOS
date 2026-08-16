// lib/nav-config.ts — declarative nav item list, gated by real permission
// keys from services/roles_service.py::DEFAULT_PERMISSIONS. No page
// content is built yet (that's steps 3-7) — this just establishes which
// routes exist and what permission unlocks each, so the shell layout has
// something real to filter against.
//
// "marketplace" is here (not "plugins") per Decision 4 — this is the new
// sandboxed-plugin marketplace, unrelated to the existing Bukkit/Paper
// `Plugin` concept.

export type NavItem = {
  href: string;
  label: string;
  /** Any one of these permissions unlocks the item; empty = always visible
   * to any authenticated staff user. */
  permissions: string[];
};

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", permissions: [] },
  { href: "/marketplace", label: "Marketplace", permissions: ["marketplace.install.view"] },
  {
    href: "/topology",
    label: "Topology",
    permissions: ["hosting.node.view", "marketplace.install.view"],
  },
  {
    // Same gating permission as the read side of the config.get/.set pair
    // (services/plugins/registration.py) — anyone who can see a plugin is
    // installed can see this nav entry; the per-field write permission is
    // enforced backend-side per plugin, not here.
    href: "/settings",
    label: "Settings",
    permissions: ["marketplace.install.view"],
  },
  {
    // Phase 10 closeout — matches the page's own gate (`audit.view`, the
    // capability's own `required_permission` in capabilities/system.py).
    href: "/activity",
    label: "Activity",
    permissions: ["audit.view"],
  },
  {
    // Phase 10 closeout — matches the page's own gate
    // (`hosting.server.view`). Deliberately not the same permission list
    // as Topology's ["hosting.node.view", "marketplace.install.view"]
    // (any-of) — Fleet always needs server visibility specifically, it
    // isn't satisfiable via the dependency-layer's plugin permission the
    // way Topology's infra layer is.
    href: "/fleet",
    label: "Fleet",
    permissions: ["hosting.server.view"],
  },
];

export function visibleNavItems(userPermissions: string[]): NavItem[] {
  return NAV_ITEMS.filter(
    (item) =>
      item.permissions.length === 0 ||
      item.permissions.some((p) => userPermissions.includes(p))
  );
}
