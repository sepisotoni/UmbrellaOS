import Link from "next/link";
import { visibleNavItems } from "@/lib/nav-config";
import { SidebarWidgets } from "@/components/widgets/sidebar-widgets";
import { fetchPluginNavEntries } from "@/lib/marketplace-pages";
import { navIconFor } from "@/lib/nav-icons";

// Server component — no 'use client'. Filtering nav items by permission is
// plain data filtering, not interactivity. Slot widgets (sidebar.tools /
// sidebar.moderation) are fetched here too, same trusted rendering path
// as the dashboard grid (components/widgets/plugin-widget.tsx) — a plugin
// gets a card in the sidebar, never arbitrary markup.
export async function Sidebar({
  permissions,
  token,
}: {
  permissions: string[];
  token: string;
}) {
  const items = visibleNavItems(permissions);
  // Phase 10, Tier 3: strictly opt-in per plugin (no page declared = no
  // entry, not a placeholder) and gated behind the same permission the
  // static "Marketplace" nav item already requires — a user who can't see
  // the marketplace section shouldn't see individual plugin pages either.
  // Skipping the fetch entirely when the permission is absent avoids a
  // guaranteed-403 round trip on every navigation for those users.
  const pluginPages = permissions.includes("marketplace.install.view")
    ? await fetchPluginNavEntries(token)
    : [];

  return (
    <nav className="flex w-56 shrink-0 flex-col border-r border-[var(--border)]">
      <div className="flex flex-col gap-1 p-4">
        {items.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="rounded-md px-3 py-2 text-sm opacity-80 hover:bg-white/5 hover:opacity-100"
          >
            {item.label}
          </Link>
        ))}
        {pluginPages.length > 0 && (
          <>
            <p className="mt-3 px-3 text-xs font-medium uppercase tracking-wide opacity-40">
              Plugins
            </p>
            {pluginPages.map((page) => {
              const Icon = navIconFor(page.nav_icon);
              return (
                <Link
                  key={page.plugin_id}
                  href={`/marketplace/${page.plugin_id}`}
                  className="flex items-center gap-2 rounded-md px-3 py-2 text-sm opacity-80 hover:bg-white/5 hover:opacity-100"
                >
                  <Icon size={14} className="shrink-0 opacity-70" />
                  <span>{page.nav_label}</span>
                </Link>
              );
            })}
          </>
        )}
      </div>
      <SidebarWidgets slot="sidebar.tools" token={token} />
      <SidebarWidgets slot="sidebar.moderation" token={token} />
    </nav>
  );
}

