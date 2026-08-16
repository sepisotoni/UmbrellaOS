// app/(dashboard)/plugin-sandbox/[id]/page.tsx — Phase 8 completion, Task
// B: the plugin debugger. One execution's full detail, including
// error_detail — the field the list view at /plugin-sandbox deliberately
// omits (see components/widgets/plugin-execution-history.tsx and
// capabilities/plugin_sandbox.py's own list/detail split). Same dynamic-
// route/async-params shape as app/(dashboard)/marketplace/[pluginId].
import Link from "next/link";
import { getSession, hasPermission } from "@/lib/session";
import { fetchExecutionDetail } from "@/lib/plugin-sandbox";
import { PluginExecutionDetailView } from "@/components/widgets/plugin-execution-detail";

export default async function PluginExecutionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const session = await getSession();
  if (!session) {
    return <p className="text-sm opacity-60">Sign in to view this execution.</p>;
  }

  const canView = hasPermission(session.user, "plugin.sandbox.view");
  const execution = canView ? await fetchExecutionDetail(id, session.token) : null;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link href="/plugin-sandbox" className="text-sm opacity-60 hover:opacity-100">
          ← Plugin Sandbox
        </Link>
      </div>
      <h1 className="text-lg font-semibold">Execution detail</h1>
      {!canView ? (
        <p className="text-sm opacity-60">
          You don&apos;t have permission to view plugin sandbox execution data.
        </p>
      ) : !execution ? (
        <p className="text-sm opacity-60">
          No execution found with id &quot;{id}&quot; — it may not exist, or you may not have
          permission to view it.
        </p>
      ) : (
        <PluginExecutionDetailView execution={execution} />
      )}
    </div>
  );
}
