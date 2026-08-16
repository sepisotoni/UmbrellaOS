"use client";

// components/widgets/plugin-config-toggle.tsx — Phase 10 step 8's one
// 'use client' leaf for Tier 2 config toggles, same "scope client
// components to genuinely interactive leaves" rule step 6's
// dashboard-customizer.tsx follows. Optimistic-update on click, reverted
// on a failed save — a toggle should feel instant, but not lie about
// state it never actually persisted.
//
// canWrite (added: sub-chat bugfix dispatch, task B) distinguishes "you
// lack plugin.<id>.config.write for this field" from "the backend is
// unreachable." The backend already enforces this correctly (a real 403
// — see services/plugins/registration.py's tests); this was purely a UX
// gap where a read-only user could click, watch an optimistic flip, then
// see a generic "Save failed — reverted" with no explanation why.
import { useState } from "react";

export function PluginConfigToggle({
  pluginId,
  fieldKey,
  label,
  initialValue,
  canWrite,
}: {
  pluginId: string;
  fieldKey: string;
  label: string;
  initialValue: boolean;
  canWrite: boolean;
}) {
  const [value, setValue] = useState(initialValue);
  const [saving, setSaving] = useState(false);
  const [errorKind, setErrorKind] = useState<"forbidden" | "network" | null>(null);

  async function toggle() {
    // canWrite is a UX signal computed from the permission list at page
    // load, not a security boundary — the fetch below is what actually
    // matters, and the backend re-checks the real permission on every
    // request regardless of what this component thinks it knows. This
    // early return just avoids an optimistic flip the server was always
    // going to reject.
    if (!canWrite) return;

    const next = !value;
    setValue(next);
    setSaving(true);
    setErrorKind(null);
    try {
      const res = await fetch("/api/plugin-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plugin_id: pluginId, key: fieldKey, value: next }),
      });
      if (!res.ok) {
        // A permission that was granted at page load can still have been
        // revoked by the time this request lands — the route (see
        // app/api/plugin-config/route.ts) returns a real 403 for that
        // case specifically, distinct from a network/backend failure.
        setValue(!next); // revert — the toggle never actually persisted
        setErrorKind(res.status === 403 ? "forbidden" : "network");
        return;
      }
    } catch {
      setValue(!next);
      setErrorKind("network");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex items-center justify-between gap-2 rounded px-2 py-1.5 hover:bg-white/5">
      <label className={`flex items-center gap-2 text-sm ${!canWrite ? "opacity-60" : ""}`}>
        <input
          type="checkbox"
          checked={value}
          disabled={saving || !canWrite}
          onChange={toggle}
        />
        <span>{label}</span>
      </label>
      {!canWrite && (
        <span className="text-xs opacity-50">Read-only — you lack permission to change this</span>
      )}
      {errorKind === "forbidden" && (
        <span className="text-xs text-red-400">Permission denied — reverted</span>
      )}
      {errorKind === "network" && (
        <span className="text-xs text-red-400">Save failed — reverted</span>
      )}
    </div>
  );
}
