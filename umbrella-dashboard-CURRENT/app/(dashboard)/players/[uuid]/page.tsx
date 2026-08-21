import { redirect, notFound } from "next/navigation";
import { getSession, hasPermission } from "@/lib/session";
import { backend } from "@/lib/api";
import { PlayerDetailSchema, PunishmentSchema, ModerationResponseSchema } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { PlayerActions } from "./player-actions";

function formatDate(d: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleString();
}

export default async function PlayerDetailPage({
  params,
}: {
  params: Promise<{ uuid: string }>;
}) {
  const session = await getSession();
  if (!session) redirect("/login");

  const canView = hasPermission(session.user, "players.view");
  if (!canView) {
    return (
      <p className="text-sm opacity-60">
        You don&apos;t have permission to view players.
      </p>
    );
  }

  const { uuid } = await params;

  let player: PlayerDetailSchema | null = null;
  let activePunishments: ModerationResponseSchema[] = [];
  let error: string | null = null;

  try {
    player = await backend.get<PlayerDetailSchema>(
      `/api/v1/players/${uuid}`,
      session.token
    );
  } catch (e: unknown) {
    if (e instanceof Error && "status" in e && (e as { status: number }).status === 404) {
      notFound();
    }
    error = e instanceof Error ? e.message : "Failed to load player";
  }

  if (player) {
    try {
      const mods = await backend.get<ModerationResponseSchema[]>(
        `/api/v1/moderation/active/${uuid}`,
        session.token
      );
      activePunishments = mods ?? [];
    } catch {
      // non-fatal
    }
  }

  if (error) {
    return (
      <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
        {error}
      </div>
    );
  }

  if (!player) return null;

  const canModerate =
    hasPermission(session.user, "moderation.kick") ||
    hasPermission(session.user, "moderation.warn") ||
    hasPermission(session.user, "moderation.ban");

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card/80 px-5 py-5">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary">
          UmbrellaOS / Players
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">
          {player.username}
        </h1>
        <p className="mt-1 font-mono text-xs opacity-50">{player.uuid}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-border bg-card/60 p-5 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wide opacity-50">
            Profile
          </p>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="opacity-60">Discord linked</span>
              <span>{player.discord_id ? "Yes" : "No"}</span>
            </div>
            <div className="flex justify-between">
              <span className="opacity-60">First joined</span>
              <span>{formatDate(player.first_joined)}</span>
            </div>
            <div className="flex justify-between">
              <span className="opacity-60">Last seen</span>
              <span>{formatDate(player.last_seen)}</span>
            </div>
            <div className="flex justify-between">
              <span className="opacity-60">Total punishments</span>
              <span>{player.punishment_count}</span>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card/60 p-5 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wide opacity-50">
            Active punishments
          </p>
          {activePunishments.length === 0 ? (
            <p className="text-sm opacity-50">None active.</p>
          ) : (
            <ul className="space-y-2">
              {activePunishments.map((p, i) => (
                <li key={i} className="text-sm flex items-center gap-2">
                  <Badge variant="destructive">{p.action}</Badge>
                  <span className="opacity-70">{p.reason}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {canModerate && (
        <PlayerActions
          playerUuid={uuid}
          token={session.token}
        />
      )}
    </div>
  );
}
