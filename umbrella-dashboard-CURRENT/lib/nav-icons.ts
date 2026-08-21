// lib/nav-icons.ts — fixed lookup from a manifest-declared nav_icon string
// to a real lucide-react component. Deliberately a lookup table, not a
// dynamic import by name: a plugin's `page.nav_icon` string is untrusted
// input, and resolving it through `import()`/bracket-indexing an arbitrary
// module would let a plugin reach for anything in the package rather than
// the small curated set the backend actually validates against
// (services/plugins/manifest.py::_ALLOWED_NAV_ICONS) — same no-plugin-
// controlled-asset stance the rest of Tier 3 holds.
//
// Keep this set in lockstep with _ALLOWED_NAV_ICONS. A name that isn't a
// key here (shouldn't happen — the backend already rejected anything
// outside that set at manifest-validation time) falls back to Box rather
// than crashing the sidebar.
import { Activity, BarChart3, Box, Database, LayoutGrid, List, Puzzle, Server, Settings, type LucideIcon } from "lucide-react";

const NAV_ICONS: Record<string, LucideIcon> = {
  box: Box,
  "layout-grid": LayoutGrid,
  activity: Activity,
  database: Database,
  list: List,
  "bar-chart": BarChart3,
  puzzle: Puzzle,
  settings: Settings,
  server: Server,
};

export function navIconFor(name: string): LucideIcon {
  return NAV_ICONS[name] ?? Box;
}
