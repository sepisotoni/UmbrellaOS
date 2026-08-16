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
      <h1 className="text-lg font-semibold">Topology</h1>
      <TopologyCanvas infra={infra} dependency={dependency} />
    </div>
  );
}
