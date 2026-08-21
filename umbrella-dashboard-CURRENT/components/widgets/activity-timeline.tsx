// components/widgets/activity-timeline.tsx — first-party trusted
// component (Phase 10 closeout, Task 1). Follows the same conventions as
// components/widgets/{stat-pair,status-badge,simple-list}.tsx (plain data
// in, React's normal text-content escaping, no raw HTML) without routing
// through the plugin-widget/render_as dispatch pipeline — this renders a
// real `AuditSearchResult` from `platform.audit.search` directly, it
// isn't plugin-supplied data with a declared shape.
//
// No 'use client' anywhere here: pagination is plain <Link href>
// navigation (a server component re-render on the next request), not
// client-side state — matching the dispatch's "most of this doesn't need
// to be interactive at all."
import Link from "next/link";
import type { AuditSearchResult } from "@/lib/types";

function relativeTime(iso: string | null): string {
  if (!iso) return "unknown time";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "unknown time";

  const diffSeconds = Math.round((Date.now() - then) / 1000);
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 31_536_000],
    ["month", 2_592_000],
    ["week", 604_800],
    ["day", 86_400],
    ["hour", 3_600],
    ["minute", 60],
  ];

  for (const [unit, secondsInUnit] of units) {
    const value = Math.trunc(diffSeconds / secondsInUnit);
    if (Math.abs(value) >= 1) {
      return new Intl.RelativeTimeFormat("en", { numeric: "auto" }).format(-value, unit);
    }
  }
  return "just now";
}

export function ActivityTimeline({
  result,
  pageSize,
}: {
  result: AuditSearchResult;
  pageSize: number;
}) {
  const { entries, total, offset } = result;

  if (entries.length === 0) {
    return (
      <p className="text-sm opacity-60">
        {offset > 0 ? "No more activity to show." : "No audit activity recorded yet."}
      </p>
    );
  }

  const hasPrev = offset > 0;
  const hasNext = offset + entries.length < total;
  const prevOffset = Math.max(0, offset - pageSize);
  const nextOffset = offset + pageSize;

  return (
    <div className="space-y-3">
      <ul className="divide-y divide-[var(--border)] rounded-lg border border-[var(--border)]">
        {entries.map((entry) => (
          <li key={entry.id} className="flex items-start justify-between gap-4 p-3">
            <div className="min-w-0">
              <p className="text-sm">
                <span className="font-medium">{entry.actor}</span>{" "}
                <span className="opacity-70">{entry.action}</span>
                {entry.target && <span className="opacity-70"> → {entry.target}</span>}
              </p>
              <p className="mt-0.5 text-xs opacity-40">{entry.actor_type}</p>
            </div>
            <span className="shrink-0 text-xs opacity-50" title={entry.created_at ?? undefined}>
              {relativeTime(entry.created_at)}
            </span>
          </li>
        ))}
      </ul>
      <div className="flex items-center justify-between text-xs opacity-70">
        <span>
          Showing {offset + 1}–{offset + entries.length} of {total}
        </span>
        <div className="flex gap-2">
          {hasPrev ? (
            <Link
              href={`/activity?offset=${prevOffset}`}
              className="rounded border border-[var(--border)] px-2 py-1 hover:bg-white/5"
            >
              Newer
            </Link>
          ) : (
            <span className="rounded border border-[var(--border)] px-2 py-1 opacity-30">Newer</span>
          )}
          {hasNext ? (
            <Link
              href={`/activity?offset=${nextOffset}`}
              className="rounded border border-[var(--border)] px-2 py-1 hover:bg-white/5"
            >
              Older
            </Link>
          ) : (
            <span className="rounded border border-[var(--border)] px-2 py-1 opacity-30">Older</span>
          )}
        </div>
      </div>
    </div>
  );
}
