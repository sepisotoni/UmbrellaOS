import { redirect } from "next/navigation";
import { getSession, hasPermission } from "@/lib/session";
import { backend } from "@/lib/api";
import { PlayerSchema } from "@/lib/types";
import { PlayersTable } from "./players-table";

export default async function PlayersPage({
  searchParams,
}: {
  searchParams: Promise<{ username?: string }>;
}) {
  const session = await getSession();
  if (!session) redirect("/login");

  const canView = hasPermission(session.user, "players.view");
  const { username } = await searchParams;

  let players: PlayerSchema[] = [];
  let error: string | null = null;

  if (canView) {
    try {
      const qs = new URLSearchParams({ limit: "50" });
      if (username) qs.set("username", username);
      players = await backend.get<PlayerSchema[]>(
        `/api/v1/players?${qs}`,
        session.token
      );
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load players";
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card/80 px-5 py-5">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary">
          UmbrellaOS / Players
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">
          Players
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Search and manage players on your network.
        </p>
      </div>
      {!canView ? (
        <p className="text-sm opacity-60">
          You don&apos;t have permission to view players.
        </p>
      ) : error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : (
        <PlayersTable players={players} initialUsername={username ?? ""} />
      )}
    </div>
  );
}
