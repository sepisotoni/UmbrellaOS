// lib/search.ts — server-only federated search: one entry per source, each
// gated by the real permission it needs, run in parallel per keystroke
// against the real backend (roadmap Decision 3: "federated into one search
// UI via live fan-out per keystroke, not a pre-built index" — locked,
// simpler to build, latency bound by the slowest source, accepted
// tradeoff given this project's actual scale).
//
// Nothing here is cached or indexed. This file's only job is: given a
// query and the caller's already-resolved User, run every source the
// caller holds permission for, in parallel, and merge the results —
// never call a source the caller can't use (saves a doomed round trip,
// and avoids the palette silently showing empty sections that just 403'd).
import "server-only";
import { backend, invokeCapability } from "./api";
import type { User } from "./types";
import type { SearchResultItem } from "./search-types";
import { visibleNavItems } from "./nav-config";

type Source = {
  id: string;
  label: string;
  /** null = no permission needed (matches something already visible,
   * like the static nav list). */
  requiredPermission: string | null;
  run: (query: string, token: string) => Promise<SearchResultItem[]>;
};

const SOURCES: Source[] = [
  {
    id: "players",
    label: "Players",
    requiredPermission: "players.view",
    run: async (query, token) => {
      type PlayerSchema = { uuid: string; username: string };
      const players = await backend.get<PlayerSchema[]>(
        `/api/v1/players?username=${encodeURIComponent(query)}&limit=8`,
        token
      );
      return players.map((p) => ({
        sourceId: "players",
        sourceLabel: "Players",
        title: p.username,
        subtitle: p.uuid,
        href: `/players/${p.uuid}`,
      }));
    },
  },
  {
    id: "knowledge",
    label: "Knowledge base",
    requiredPermission: "knowledge.entry.search",
    run: async (query, token) => {
      type SearchResult = { entries: { id: string; channel_name: string; content: string }[] };
      const res = await invokeCapability<SearchResult>(
        "knowledge.entry.search",
        { query, limit: 5 },
        token
      );
      return res.entries.map((e) => ({
        sourceId: "knowledge",
        sourceLabel: "Knowledge base",
        title: e.content.slice(0, 80),
        subtitle: `#${e.channel_name}`,
        href: `/knowledge/${e.id}`,
      }));
    },
  },
  {
    id: "logs",
    label: "Logs",
    requiredPermission: "observability.logs.view",
    run: async (query, token) => {
      type LogSearchResult = {
        entries: { id: string; level: string; logger_name: string; message: string }[];
      };
      const res = await invokeCapability<LogSearchResult>(
        "platform.observability.search_logs",
        { query, limit: 5 },
        token
      );
      return res.entries.map((e) => ({
        sourceId: "logs",
        sourceLabel: "Logs",
        title: e.message.slice(0, 80),
        subtitle: `${e.level} · ${e.logger_name}`,
        href: `/observability/logs?trace=${e.id}`,
      }));
    },
  },
  {
    id: "marketplace",
    label: "Marketplace",
    requiredPermission: "marketplace.listing.view",
    run: async (query, token) => {
      type Listing = { plugin_id: string; name: string; description: string };
      // marketplace.listing.list has no server-side query param — it's a
      // small catalog by this project's own scale (single operator, one
      // community), so filtering the fanned-out response client-of-this-
      // route-handler-side is still "live fan-out per keystroke" (a real
      // request every time), just without backend-side filtering to ask
      // for. Worth revisiting only if the catalog ever grows enough for
      // that to matter — same "don't build it speculatively" posture the
      // roadmap doc takes elsewhere.
      const listings = await invokeCapability<Listing[]>("marketplace.listing.list", {}, token);
      const q = query.toLowerCase();
      return listings
        .filter(
          (l) =>
            l.name.toLowerCase().includes(q) ||
            l.plugin_id.toLowerCase().includes(q) ||
            l.description.toLowerCase().includes(q)
        )
        .slice(0, 5)
        .map((l) => ({
          sourceId: "marketplace",
          sourceLabel: "Marketplace",
          title: l.name,
          subtitle: l.description,
          href: `/marketplace/${l.plugin_id}`,
        }));
    },
  },
  // Deliberately NOT included: archive.search. Its capability declaration
  // (capabilities/archive_search.py) sets audited=True specifically
  // because it "reveals unfiltered chat content" — firing it on every
  // keystroke would write an audit-log entry per keystroke for a search
  // that hasn't finished being typed yet. Every other source here is
  // audited=False. Archive search belongs behind an explicit
  // "search archive" submit action, not live fan-out — not built in this
  // step, flagged in the handback doc as an intentional exclusion rather
  // than an oversight.
];

export async function runFederatedSearch(
  query: string,
  user: User,
  token: string
): Promise<SearchResultItem[]> {
  const trimmed = query.trim();
  if (trimmed.length < 2) return [];

  const navMatches: SearchResultItem[] = visibleNavItems(user.permissions)
    .filter((item) => item.label.toLowerCase().includes(trimmed.toLowerCase()))
    .map((item) => ({
      sourceId: "nav",
      sourceLabel: "Navigate",
      title: item.label,
      href: item.href,
    }));

  const runnable = SOURCES.filter(
    (s) => s.requiredPermission === null || user.permissions.includes(s.requiredPermission)
  );

  const results = await Promise.all(
    runnable.map(async (source) => {
      try {
        return await source.run(trimmed, token);
      } catch {
        // One source failing (backend hiccup, unexpected shape) drops that
        // section, never the whole palette — same independent-failure
        // posture as lib/widgets.ts.
        return [] as SearchResultItem[];
      }
    })
  );

  return [navMatches, ...results].flat();
}
