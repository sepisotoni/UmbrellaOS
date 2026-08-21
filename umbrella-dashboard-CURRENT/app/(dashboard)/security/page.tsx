import { redirect } from "next/navigation";
import { getSession, hasPermission } from "@/lib/session";
import { backend } from "@/lib/api";
import { SecurityEvent } from "@/lib/types";
import { SecurityEventsTable } from "./security-events-table";

export default async function SecurityPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const canView = hasPermission(session.user, "security.events.view");

  let events: SecurityEvent[] = [];
  let error: string | null = null;

  if (canView) {
    try {
      const data = await backend.get<{ events?: SecurityEvent[] } | SecurityEvent[]>(
        "/api/v1/security/events",
        session.token
      );
      events = Array.isArray(data) ? data : (data.events ?? []);
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load security events";
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card/80 px-5 py-5">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary">
          UmbrellaOS / Staff
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">
          Security Events
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Monitor security incidents and suspicious activity across your network.
        </p>
      </div>
      {!canView ? (
        <p className="text-sm opacity-60">
          You don&apos;t have permission to view security events.
        </p>
      ) : error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : (
        <SecurityEventsTable events={events} />
      )}
    </div>
  );
}
