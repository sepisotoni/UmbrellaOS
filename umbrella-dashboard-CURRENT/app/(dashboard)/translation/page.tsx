import { redirect } from "next/navigation";
import { getSession, hasPermission } from "@/lib/session";
import { backend } from "@/lib/api";
import { PlayerLanguageResponse } from "@/lib/types";
import { TranslationView } from "./translation-view";

export default async function TranslationPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const canView = hasPermission(session.user, "players.view");

  let languages: PlayerLanguageResponse[] = [];
  let error: string | null = null;

  if (canView) {
    try {
      languages = await backend.get<PlayerLanguageResponse[]>(
        "/api/v1/translation/language/all",
        session.token
      );
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load language data";
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card/80 px-5 py-5">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary">
          UmbrellaOS / System
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">
          Translation
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          View player language preferences and translate text manually.
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
        <TranslationView languages={languages} token={session.token} />
      )}
    </div>
  );
}
