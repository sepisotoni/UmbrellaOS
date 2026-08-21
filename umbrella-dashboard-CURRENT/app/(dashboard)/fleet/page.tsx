// app/(dashboard)/fleet/page.tsx — Phase 10 closeout, Task 2: the fleet
// overview. `hosting.node.list` / `hosting.server.list` /
// `hosting.server.stats` already exist (capabilities/hosting.py) — this
// is a UI-only dispatch, no new backend plumbing
// (SUBCHAT-HANDOFF-PHASE10-CLOSEOUT.md).
//
// Its own route, same reasoning as app/(dashboard)/activity/page.tsx:
// first-party data read directly from platform capabilities, not a
// plugin-supplied dashboard slot, so it doesn't belong inside
// `WidgetGrid`'s plugin-slot pipeline. Not folded into `/topology` either
// even though that page's infra layer also reads `hosting.node.list` /
// `hosting.server.list` — topology is a relationship graph (which server
// runs on which node, rendered as a canvas), this is a status/at-a-glance
// overview with live stats attached; different question, different page,
// and the dispatch scoped this as "an overview, not the full hosting
// console," which topology already partially is.
//
// Permission-gate pattern follows settings/page.tsx and
// marketplace/page.tsx (see activity/page.tsx's longer comment on this
// same choice) — session-redirect only, `hosting.server.view` gates an
// inline message in place of the overview rather than a redirect.
import { redirect } from "next/navigation";
import { getSession, hasPermission } from "@/lib/session";
import { buildFleetOverview } from "@/lib/fleet";
import { FleetOverview } from "@/components/widgets/fleet-overview";

export default async function FleetPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const canView = hasPermission(session.user, "hosting.server.view");
  const nodes = canView ? await buildFleetOverview(session.token) : [];

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card/80 px-5 py-5"><p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary">UmbrellaOS / Infrastructure</p><h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">Fleet overview</h1><p className="mt-2 text-sm leading-6 text-muted-foreground">Monitor nodes, capacity, and server health from one operational surface.</p></div>
      {!canView ? (
        <p className="text-sm opacity-60">
          You don&apos;t have permission to view hosted server state.
        </p>
      ) : (
        <FleetOverview nodes={nodes} />
      )}
    </div>
  );
}
