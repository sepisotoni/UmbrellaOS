import { redirect } from "next/navigation";
import { getSession, hasPermission } from "@/lib/session";
import { backend } from "@/lib/api";
import { PunishmentSchema } from "@/lib/types";
import { ModerationTabs } from "./moderation-tabs";

export default async function ModerationPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const canView = hasPermission(session.user, "punishments.view");

  let punishments: PunishmentSchema[] = [];
  let error: string | null = null;

  if (canView) {
    try {
      punishments = await backend.get<PunishmentSchema[]>(
        "/api/v1/punishments",
        session.token
      );
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load punishments";
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card/80 px-5 py-5">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary">
          UmbrellaOS / Moderation
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">
          Moderation
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Manage punishments and active bans across your network.
        </p>
      </div>
      {!canView ? (
        <p className="text-sm opacity-60">
          You don&apos;t have permission to view punishments.
        </p>
      ) : error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : (
        <ModerationTabs
          punishments={punishments}
          token={session.token}
          canCreate={hasPermission(session.user, "punishments.create")}
          canRevoke={hasPermission(session.user, "punishments.revoke")}
        />
      )}
    </div>
  );
}
