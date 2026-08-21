"use client";

// components/widgets/marketplace-install-button.tsx — Task A's one
// 'use client' leaf, same "scope client components to genuinely
// interactive leaves" rule plugin-config-toggle.tsx and
// dashboard-customizer.tsx already follow.
//
// canManage is a UX signal computed from the permission list at page
// load (marketplace.install.manage — see the Settings page's canWrite
// for the identical pattern), not a security boundary: the backend
// re-checks the real permission on every request regardless of what this
// component thinks it knows.
//
// Install is a real, meaningful action (manifest validation + sandbox
// setup server-side, not instant) — this shows a "Installing…"/
// "Uninstalling…" pending state rather than assuming the request
// resolves the way a config toggle's optimistic flip does, and does NOT
// optimistically flip installed/not-installed state before the request
// actually resolves.
import { useState } from "react";
import { useRouter } from "next/navigation";

export function MarketplaceInstallButton({
  pluginId,
  latestVersion,
  installedVersion,
  canManage,
}: {
  pluginId: string;
  latestVersion: string;
  /** null when this plugin isn't currently installed. */
  installedVersion: string | null;
  canManage: boolean;
}) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [errorKind, setErrorKind] = useState<"forbidden" | "conflict" | "not_found" | "network" | null>(
    null
  );

  const isInstalled = installedVersion !== null;
  const updateAvailable = isInstalled && installedVersion !== latestVersion;

  async function handleInstall() {
    if (!canManage || pending) return;
    setPending(true);
    setErrorKind(null);
    try {
      const res = await fetch("/api/marketplace-install", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plugin_id: pluginId, version: latestVersion }),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { error?: string };
        setErrorKind(
          res.status === 403
            ? "forbidden"
            : res.status === 404
              ? "not_found"
              : res.status === 409
                ? "conflict"
                : "network"
        );
        void body;
        return;
      }
      router.refresh();
    } catch {
      setErrorKind("network");
    } finally {
      setPending(false);
    }
  }

  async function handleUninstall() {
    if (!canManage || pending) return;
    if (!window.confirm(`Uninstall ${pluginId}? Its registered capabilities will be removed.`)) {
      return;
    }
    setPending(true);
    setErrorKind(null);
    try {
      const res = await fetch(`/api/marketplace-install?plugin_id=${encodeURIComponent(pluginId)}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        setErrorKind(res.status === 403 ? "forbidden" : res.status === 404 ? "not_found" : "network");
        return;
      }
      router.refresh();
    } catch {
      setErrorKind("network");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-2">
        {isInstalled && updateAvailable && (
          <button
            type="button"
            onClick={handleInstall}
            disabled={!canManage || pending}
            className="rounded border border-[var(--border)] px-2 py-1 text-xs disabled:opacity-50"
          >
            {pending ? "Updating…" : `Update to ${latestVersion}`}
          </button>
        )}
        {isInstalled ? (
          <button
            type="button"
            onClick={handleUninstall}
            disabled={!canManage || pending}
            className="rounded border border-red-400/40 px-2 py-1 text-xs text-red-400 disabled:opacity-50"
          >
            {pending ? "Uninstalling…" : "Uninstall"}
          </button>
        ) : (
          <button
            type="button"
            onClick={handleInstall}
            disabled={!canManage || pending}
            className="rounded bg-[var(--accent)] px-2 py-1 text-xs disabled:opacity-50"
          >
            {pending ? "Installing…" : "Install"}
          </button>
        )}
      </div>
      {!canManage && (
        <span className="text-xs opacity-50">Read-only — you lack permission to manage plugins</span>
      )}
      {errorKind === "forbidden" && (
        <span className="text-xs text-red-400">Permission denied</span>
      )}
      {errorKind === "conflict" && (
        <span className="text-xs text-red-400">That version is already installed</span>
      )}
      {errorKind === "not_found" && (
        <span className="text-xs text-red-400">Plugin or version not found</span>
      )}
      {errorKind === "network" && (
        <span className="text-xs text-red-400">Action failed — try again</span>
      )}
    </div>
  );
}
