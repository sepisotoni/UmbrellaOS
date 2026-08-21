import { redirect } from "next/navigation";
import { getSession, hasPermission } from "@/lib/session";
import { backend } from "@/lib/api";
import { StaffMember, RoleSchema } from "@/lib/types";
import { StaffTable } from "./staff-table";

export default async function StaffPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const canManage = hasPermission(session.user, "roles.manage");

  let members: StaffMember[] = [];
  let roles: RoleSchema[] = [];
  let error: string | null = null;

  if (canManage) {
    try {
      [members, roles] = await Promise.all([
        backend.get<StaffMember[]>("/api/v1/staff/discord-members", session.token),
        backend.get<RoleSchema[]>("/api/v1/roles", session.token),
      ]);
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load staff";
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card/80 px-5 py-5">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary">
          UmbrellaOS / Staff
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">
          Staff Management
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Manage Discord server members and their staff roles.
        </p>
      </div>
      {!canManage ? (
        <p className="text-sm opacity-60">
          You don&apos;t have permission to manage staff roles.
        </p>
      ) : error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : (
        <StaffTable members={members} roles={roles} token={session.token} />
      )}
    </div>
  );
}
