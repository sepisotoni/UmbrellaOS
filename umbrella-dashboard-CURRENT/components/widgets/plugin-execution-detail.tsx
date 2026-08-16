// components/widgets/plugin-execution-detail.tsx — Phase 8 completion,
// Task B: the plugin debugger's detail view. Renders a single
// PluginExecutionDetail (plugin.sandbox.execution_detail) — the one place
// in the dashboard error_detail is ever shown, matching the backend's own
// deliberate list/detail split (see capabilities/plugin_sandbox.py).
import type { PluginExecutionDetail } from "@/lib/types";

function formatMs(value: number): string {
  return value < 1000 ? `${value.toFixed(2)}ms` : `${(value / 1000).toFixed(3)}s`;
}

function formatBytes(value: number | null): string {
  if (value === null) return "not available";
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(2)} MB`;
}

const OUTCOME_LABELS: Record<string, string> = {
  success: "Succeeded",
  error: "Errored",
  timeout: "Timed out",
  resource_limit_kill: "Killed (resource limit)",
};

export function PluginExecutionDetailView({ execution }: { execution: PluginExecutionDetail }) {
  const telemetryUnavailable = execution.cpu_time_ms === null && execution.peak_memory_bytes === null;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-[var(--border)] p-4">
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wide opacity-60">Execution</h3>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
          <div>
            <dt className="text-xs opacity-50">Plugin</dt>
            <dd className="text-sm font-medium">{execution.plugin_id}</dd>
          </div>
          <div>
            <dt className="text-xs opacity-50">Entrypoint</dt>
            <dd className="text-sm font-medium">{execution.entrypoint}</dd>
          </div>
          <div>
            <dt className="text-xs opacity-50">Actor</dt>
            <dd className="text-sm font-medium">{execution.actor_id}</dd>
          </div>
          <div>
            <dt className="text-xs opacity-50">Outcome</dt>
            <dd className="text-sm font-medium">{OUTCOME_LABELS[execution.outcome] ?? execution.outcome}</dd>
          </div>
          <div>
            <dt className="text-xs opacity-50">Wall time</dt>
            <dd className="text-sm font-medium">{formatMs(execution.wall_time_ms)}</dd>
          </div>
          <div>
            <dt className="text-xs opacity-50">When</dt>
            <dd className="text-sm font-medium" title={execution.created_at ?? undefined}>
              {execution.created_at ? new Date(execution.created_at).toLocaleString() : "unknown"}
            </dd>
          </div>
        </dl>
      </div>

      <div className="rounded-lg border border-[var(--border)] p-4">
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wide opacity-60">Resource usage</h3>
        {telemetryUnavailable && (
          <p className="mb-3 text-xs opacity-50">
            Not available — the sandboxed process was terminated by signal before it could report its
            own resource usage (this happens for resource-limit kills; see the outcome above).
          </p>
        )}
        <dl className="flex flex-wrap gap-6">
          <div>
            <dt className="text-xs opacity-50">CPU time</dt>
            <dd className="text-lg font-semibold">
              {execution.cpu_time_ms !== null ? formatMs(execution.cpu_time_ms) : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-xs opacity-50">Peak memory</dt>
            <dd className="text-lg font-semibold">{formatBytes(execution.peak_memory_bytes)}</dd>
          </div>
        </dl>
      </div>

      {execution.error_detail && (
        <div className="rounded-lg border border-red-400/30 bg-red-400/5 p-4">
          <h3 className="mb-3 text-xs font-medium uppercase tracking-wide text-red-400/80">
            Error detail
          </h3>
          <pre className="overflow-x-auto whitespace-pre-wrap break-words text-xs text-red-300">
            {execution.error_detail}
          </pre>
        </div>
      )}
    </div>
  );
}
