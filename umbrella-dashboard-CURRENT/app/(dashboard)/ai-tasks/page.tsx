import { redirect } from "next/navigation";
import { getSession, hasPermission } from "@/lib/session";
import { backend } from "@/lib/api";
import { AITask, AIConfigResponse } from "@/lib/types";
import { AITasksList } from "./ai-tasks-list";

export default async function AITasksPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const canView = hasPermission(session.user, "punishments.view");
  const canManageConfig = hasPermission(session.user, "settings.manage");

  let tasks: AITask[] = [];
  let configPending: AIConfigResponse[] = [];
  let error: string | null = null;

  if (canView) {
    try {
      tasks = await backend.get<AITask[]>("/api/v1/ai/tasks", session.token);
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load AI tasks";
    }
  }

  if (canManageConfig) {
    try {
      configPending = await backend.get<AIConfigResponse[]>(
        "/api/v1/ai/config/pending",
        session.token
      );
    } catch {
      // non-fatal
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card/80 px-5 py-5">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary">
          UmbrellaOS / Moderation
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">
          AI Tasks
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Review AI recommendations and approve pending configuration changes.
        </p>
      </div>
      {!canView ? (
        <p className="text-sm opacity-60">
          You don&apos;t have permission to view AI tasks.
        </p>
      ) : error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : (
        <AITasksList
          tasks={tasks}
          configPending={configPending}
          token={session.token}
          canAction={hasPermission(session.user, "punishments.create")}
          canManageConfig={canManageConfig}
        />
      )}
    </div>
  );
}
