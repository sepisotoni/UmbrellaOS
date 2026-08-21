// components/widgets/plugin-execution-history.tsx — first-party trusted
// component (Phase 8 completion, Task A UI / feeds Task B's debugger).
// Same conventions as activity-timeline.tsx: renders a real
// PluginExecutionHistoryResult from plugin.sandbox.execution_history
// directly, plain <Link href> pagination (server re-render), no
// 'use client'. Each row links to /plugin-sandbox/[id], the debugger
// detail view (Task B) — the list view itself never shows error_detail
// (matching the backend's own list/detail split), only outcome + timing.
import Link from "next/link";
import type { PluginExecutionEntry } from "@/lib/types";

const OUTCOME_STYLES: Record<string, string> = {
  success: "text-emerald-400 bg-emerald-400/10",
  error: "text-red-400 bg-red-400/10",
  timeout: "text-amber-400 bg-amber-400/10",
  resource_limit_kill: "text-amber-400 bg-amber-400/10",
};

function outcomeClass(outcome: string): string {
  return OUTCOME_STYLES[outcome] ?? "text-[var(--fg)] bg-white/5";
}

function formatMs(value: number): string {
  return value < 1000 ? `${value.toFixed(1)}ms` : `${(value / 1000).toFixed(2)}s`;
}

function formatBytes(value: number | null): string {
  if (value === null) return "—";
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(0)}KB`;
  return `${(value / (1024 * 1024)).toFixed(1)}MB`;
}

export function PluginExecutionHistory({
  entries,
  total,
  limit,
  offset,
  basePath = "/plugin-sandbox",
}: {
  entries: PluginExecutionEntry[];
  total: number;
  limit: number;
  offset: number;
  basePath?: string;
}) {
  if (entries.length === 0) {
    return (
      <p className="text-sm opacity-60">
        {offset > 0 ? "No more executions to show." : "No plugin executions recorded yet."}
      </p>
    );
  }

  const hasPrev = offset > 0;
  const hasNext = offset + entries.length < total;
  const prevOffset = Math.max(0, offset - limit);
  const nextOffset = offset + limit;

  return (
    <div className="space-y-3">
      <ul className="divide-y divide-[var(--border)] rounded-lg border border-[var(--border)]">
        {entries.map((entry) => (
          <li key={entry.id}>
            <Link
              href={`${basePath}/${entry.id}`}
              className="flex items-start justify-between gap-4 p-3 hover:bg-white/5"
            >
              <div className="min-w-0">
                <p className="text-sm">
                  <span className="font-medium">{entry.plugin_id}</span>{" "}
                  <span className="opacity-70">{entry.entrypoint}</span>
                </p>
                <p className="mt-0.5 text-xs opacity-40">
                  by {entry.actor_id} · {formatMs(entry.wall_time_ms)} wall
                  {entry.cpu_time_ms !== null && <> · {formatMs(entry.cpu_time_ms)} cpu</>}
                  {entry.peak_memory_bytes !== null && <> · {formatBytes(entry.peak_memory_bytes)} peak</>}
                </p>
              </div>
              <span
                className={`shrink-0 rounded px-2 py-0.5 text-xs font-medium ${outcomeClass(entry.outcome)}`}
              >
                {entry.outcome}
              </span>
            </Link>
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
              href={`${basePath}?offset=${prevOffset}`}
              className="rounded border border-[var(--border)] px-2 py-1 hover:bg-white/5"
            >
              Newer
            </Link>
          ) : (
            <span className="rounded border border-[var(--border)] px-2 py-1 opacity-30">Newer</span>
          )}
          {hasNext ? (
            <Link
              href={`${basePath}?offset=${nextOffset}`}
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
