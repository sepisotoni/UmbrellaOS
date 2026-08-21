import { redirect } from "next/navigation";
import { getSession, hasPermission } from "@/lib/session";
import { backend } from "@/lib/api";
import { FeatureFlagResponse } from "@/lib/types";
import { FeatureFlagsManager } from "./feature-flags-manager";

export default async function FeatureFlagsPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const canView = hasPermission(session.user, "feature_flags.view");

  let flags: FeatureFlagResponse[] = [];
  let error: string | null = null;

  if (canView) {
    try {
      flags = await backend.get<FeatureFlagResponse[]>(
        "/api/v1/feature-flags",
        session.token
      );
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load feature flags";
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card/80 px-5 py-5">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary">
          UmbrellaOS / System
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">
          Feature Flags
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Toggle and manage feature flags across your network.
        </p>
      </div>
      {!canView ? (
        <p className="text-sm opacity-60">
          You don&apos;t have permission to view feature flags.
        </p>
      ) : error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : (
        <FeatureFlagsManager
          flags={flags}
          token={session.token}
          canManage={hasPermission(session.user, "feature_flags.manage")}
        />
      )}
    </div>
  );
}
