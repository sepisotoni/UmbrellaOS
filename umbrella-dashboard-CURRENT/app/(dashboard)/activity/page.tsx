// app/(dashboard)/activity/page.tsx — Phase 10 closeout, Task 1: the
// activity timeline. `platform.audit.search` already exists, paginated
// and filterable (capabilities/system.py) — this is a UI-only dispatch,
// no new backend plumbing (SUBCHAT-HANDOFF-PHASE10-CLOSEOUT.md).
//
// Its own route rather than a dashboard-page addition: `WidgetGrid`
// (components/widgets/widget-grid.tsx) resolves `dashboard.widgets`
// exclusively through the plugin-slot pipeline
// (`resolveSlotWidgets`/`marketplace.install.dashboard_slots`) — that
// pipeline exists specifically to render *untrusted, plugin-supplied*
// data through the render_as dispatcher. This widget is first-party and
// reads a platform capability directly; folding it into that grid would
// either require teaching the plugin pipeline about non-plugin sources or
// misrepresenting first-party content as a plugin slot. A dedicated route
// matches how every other first-party page in this app already works
// (`/marketplace`, `/settings`, `/topology` are each their own route, not
// grid entries) and gets a real nav entry instead of being buried inside
// another page.
//
// Permission-gate pattern follows settings/page.tsx and
// marketplace/page.tsx: neither of those pages does a hard redirect on a
// missing *view* permission (only on no session at all) — they check
// session, then compute a boolean from `hasPermission` and use it to
// decide what to render. No page in this app currently redirects to a
// dedicated "access denied" route, so this doesn't invent one either;
// missing `audit.view` renders an inline message in place of the
// timeline, same shape as every other empty/degraded state in this app.
import { redirect } from "next/navigation";
import { getSession, hasPermission } from "@/lib/session";
import { fetchAuditLog } from "@/lib/activity";
import { ActivityTimeline } from "@/components/widgets/activity-timeline";

const PAGE_SIZE = 25;

function parseOffset(raw: string | undefined): number {
  const parsed = Number.parseInt(raw ?? "0", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

export default async function ActivityPage({
  searchParams,
}: {
  searchParams: Promise<{ offset?: string }>;
}) {
  const session = await getSession();
  if (!session) redirect("/login");

  const canView = hasPermission(session.user, "audit.view");
  const { offset: offsetParam } = await searchParams;
  const offset = parseOffset(offsetParam);

  const result = canView
    ? await fetchAuditLog(session.token, { limit: PAGE_SIZE, offset })
    : null;

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card/80 px-5 py-5"><p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary">UmbrellaOS / Audit trail</p><h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">Activity</h1><p className="mt-2 text-sm leading-6 text-muted-foreground">A chronological view of changes and events across your network.</p></div>
      {!canView || !result ? (
        <p className="text-sm opacity-60">You don&apos;t have permission to view the audit log.</p>
      ) : (
        <ActivityTimeline result={result} pageSize={PAGE_SIZE} />
      )}
    </div>
  );
}
