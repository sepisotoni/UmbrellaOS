// app/(dashboard)/plugin-sandbox/page.tsx — Phase 8 completion: the
// sandbox visualizer (Task D) combined with the profiler (Task C) and the
// execution history list (Task A) on one page, plus a link into the
// per-execution debugger (Task B, app/(dashboard)/plugin-sandbox/[id]).
// One route rather than three separate nav entries — all four read the
// same underlying PluginExecutionRecord data at different granularities
// (configured limits -> aggregate profile -> individual executions ->
// one execution's full detail), so this is one continuous drill-down,
// the same reasoning fleet/page.tsx and activity/page.tsx already used
// for "first-party platform data gets its own route, not a dashboard
// grid slot."
//
// Permission gate: `plugin.sandbox.view` (services/roles_service.py),
// same inline-message-in-place-of-content pattern as every other
// first-party page in this app (see activity/page.tsx's longer comment
// on why this app never redirects to a dedicated "access denied" route).
import { redirect } from "next/navigation";
import { getSession, hasPermission } from "@/lib/session";
import { fetchExecutionHistory, fetchProfile, fetchSandboxLimits } from "@/lib/plugin-sandbox";
import { PluginExecutionHistory } from "@/components/widgets/plugin-execution-history";
import { PluginSandboxProfileChart } from "@/components/widgets/plugin-sandbox-profile-chart";
import { PluginSandboxLimitsPanel } from "@/components/widgets/plugin-sandbox-limits";

const PAGE_SIZE = 25;

function parseOffset(raw: string | undefined): number {
  const parsed = Number.parseInt(raw ?? "0", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

export default async function PluginSandboxPage({
  searchParams,
}: {
  searchParams: Promise<{ offset?: string; plugin_id?: string; outcome?: string }>;
}) {
  const session = await getSession();
  if (!session) redirect("/login");

  const canView = hasPermission(session.user, "plugin.sandbox.view");
  const { offset: offsetParam, plugin_id: pluginId, outcome } = await searchParams;
  const offset = parseOffset(offsetParam);

  const [limits, profile, history] = canView
    ? await Promise.all([
        fetchSandboxLimits(session.token),
        fetchProfile(session.token, { pluginId }),
        fetchExecutionHistory(session.token, { limit: PAGE_SIZE, offset, pluginId, outcome }),
      ])
    : [null, [], { entries: [], total: 0, limit: PAGE_SIZE, offset: 0 }];

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card/80 px-5 py-5"><p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary">UmbrellaOS / Runtime</p><h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">Plugin sandbox</h1><p className="mt-2 text-sm leading-6 text-muted-foreground">Inspect plugin executions, limits, and runtime health.</p></div>
      {!canView ? (
        <p className="text-sm opacity-60">
          You don&apos;t have permission to view plugin sandbox execution data.
        </p>
      ) : (
        <div className="space-y-6">
          {limits && <PluginSandboxLimitsPanel limits={limits} />}
          <PluginSandboxProfileChart profile={profile} />
          <div>
            <h2 className="mb-3 text-xs font-medium uppercase tracking-wide opacity-60">
              Recent executions
            </h2>
            <PluginExecutionHistory
              entries={history.entries}
              total={history.total}
              limit={history.limit}
              offset={history.offset}
              basePath="/plugin-sandbox"
            />
          </div>
        </div>
      )}
    </div>
  );
}
