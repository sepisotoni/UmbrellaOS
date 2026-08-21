import { redirect } from "next/navigation";
import { getSession, hasPermission } from "@/lib/session";
import { backend } from "@/lib/api";
import { AppealSchema } from "@/lib/types";
import { AppealsTable } from "./appeals-table";

export default async function AppealsPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const canView = hasPermission(session.user, "appeals.view");

  let appeals: AppealSchema[] = [];
  let error: string | null = null;

  if (canView) {
    try {
      appeals = await backend.get<AppealSchema[]>(
        "/api/v1/appeals",
        session.token
      );
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load appeals";
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card/80 px-5 py-5">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary">
          UmbrellaOS / Moderation
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">
          Appeals
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Review and process punishment appeals from players.
        </p>
      </div>
      {!canView ? (
        <p className="text-sm opacity-60">
          You don&apos;t have permission to view appeals.
        </p>
      ) : error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : (
        <AppealsTable
          appeals={appeals}
          token={session.token}
          canManage={hasPermission(session.user, "appeals.manage")}
        />
      )}
    </div>
  );
}
