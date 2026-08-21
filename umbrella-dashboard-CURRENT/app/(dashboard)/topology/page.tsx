import { getSession } from "@/lib/session";
import { redirect } from "next/navigation";
import { buildAvailableLayers } from "@/lib/topology";
import { TopologyCanvas } from "@/components/topology/topology-canvas";

export default async function TopologyPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const { infra, dependency } = await buildAvailableLayers(session.user.permissions, session.token);

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card/80 px-5 py-5"><p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary">UmbrellaOS / Systems map</p><h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">Topology</h1><p className="mt-2 text-sm leading-6 text-muted-foreground">See how your infrastructure and dependencies connect in real time.</p></div>
      <TopologyCanvas infra={infra} dependency={dependency} />
    </div>
  );
}
