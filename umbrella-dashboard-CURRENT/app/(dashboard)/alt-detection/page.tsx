import { redirect } from "next/navigation";
import { getSession, hasPermission } from "@/lib/session";
import { backend } from "@/lib/api";
import { FlaggedPlayerSchema, AltGroupSchema } from "@/lib/types";
import { AltDetectionView } from "./alt-detection-view";

export default async function AltDetectionPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const canView = hasPermission(session.user, "players.view");

  let flagged: FlaggedPlayerSchema[] = [];
  let groups: AltGroupSchema[] = [];
  let error: string | null = null;

  if (canView) {
    try {
      [flagged, groups] = await Promise.all([
        backend.get<FlaggedPlayerSchema[]>("/api/v1/alts/flagged", session.token),
        backend.get<AltGroupSchema[]>("/api/v1/alts/groups", session.token),
      ]);
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load alt detection data";
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card/80 px-5 py-5">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary">
          UmbrellaOS / Players
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">
          Alt Detection
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Review flagged players and known alt account groups.
        </p>
      </div>
      {!canView ? (
        <p className="text-sm opacity-60">
          You don&apos;t have permission to view player data.
        </p>
      ) : error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : (
        <AltDetectionView
          flagged={flagged}
          groups={groups}
          token={session.token}
          canManage={hasPermission(session.user, "players.manage")}
        />
      )}
    </div>
  );
}
