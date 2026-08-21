"use client";
// components/widgets/plugin-sandbox-profile-chart.tsx — Phase 8
// completion, Task C: the plugin profiler. Renders
// PluginExecutionProfile[] (plugin.sandbox.profile) as a per-plugin bar
// chart — avg/p95 wall time and error rate, the two things an admin
// actually wants at a glance when deciding "which plugin is the problem."
// 'use client' + recharts, matching this app's stated dependency
// (package.json already has recharts; this is its first use) — every
// other first-party widget in this app is a server component because it
// doesn't need interactivity, but a chart genuinely does need to run in
// the browser.
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PluginExecutionProfile } from "@/lib/types";

function formatMs(value: number): string {
  return value < 1000 ? `${value.toFixed(1)}ms` : `${(value / 1000).toFixed(2)}s`;
}

// Error rate drives bar color, not a separate legend — keeps the chart
// readable at a glance rather than adding a second chart just for error
// rate. Same three-tier severity vocabulary as
// plugin-execution-history.tsx's outcome colors (emerald/amber/red).
function barColor(errorRate: number): string {
  if (errorRate >= 0.25) return "#f87171"; // red-400
  if (errorRate > 0) return "#fbbf24"; // amber-400
  return "#34d399"; // emerald-400
}

export function PluginSandboxProfileChart({ profile }: { profile: PluginExecutionProfile[] }) {
  if (profile.length === 0) {
    return <p className="text-sm opacity-60">No plugin executions in this window.</p>;
  }

  const windowHours = profile[0]?.window_hours ?? 24;
  const data = profile.map((entry) => ({
    plugin_id: entry.plugin_id,
    avg_wall_time_ms: entry.avg_wall_time_ms,
    p95_wall_time_ms: entry.p95_wall_time_ms,
    execution_count: entry.execution_count,
    error_rate: entry.error_rate,
  }));

  return (
    <div className="rounded-lg border border-[var(--border)] p-4">
      <h3 className="mb-1 text-xs font-medium uppercase tracking-wide opacity-60">
        Execution time by plugin
      </h3>
      <p className="mb-3 text-xs opacity-40">
        p95 wall time, trailing {windowHours}h. Bar color reflects error rate (green: none, amber:
        some, red: 25%+).
      </p>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="plugin_id" tick={{ fontSize: 11 }} stroke="var(--fg)" />
            <YAxis
              tick={{ fontSize: 11 }}
              stroke="var(--fg)"
              tickFormatter={(value: number) => formatMs(value)}
            />
            <Tooltip
              formatter={(value: number, name: string) =>
                name === "p95_wall_time_ms" ? [formatMs(value), "p95 wall time"] : [value, name]
              }
              labelFormatter={(label: string) => `Plugin: ${label}`}
              contentStyle={{ background: "var(--bg)", border: "1px solid var(--border)", fontSize: 12 }}
            />
            <Bar dataKey="p95_wall_time_ms" radius={[4, 4, 0, 0]}>
              {data.map((entry) => (
                <Cell key={entry.plugin_id} fill={barColor(entry.error_rate)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {profile.map((entry) => (
          <div key={entry.plugin_id} className="rounded border border-[var(--border)] p-2">
            <dt className="truncate text-xs opacity-50" title={entry.plugin_id}>
              {entry.plugin_id}
            </dt>
            <dd className="text-sm font-semibold">{entry.execution_count} calls</dd>
            <dd className="text-xs opacity-60">avg {formatMs(entry.avg_wall_time_ms)}</dd>
            <dd className="text-xs opacity-60">{(entry.error_rate * 100).toFixed(0)}% errors</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
